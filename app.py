import os
import re
import tempfile
import sys
import importlib.util
import smtplib
import ssl
from email.mime.text import MIMEText
from email.utils import formataddr
from flask import Flask, request, render_template, jsonify, session, current_app
from flask_mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, timezone
from itsdangerous import URLSafeTimedSerializer

from dotenv import load_dotenv
load_dotenv()

from auth import auth, db, User, PredictionHistory

RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY")
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY")

# safe defaults: if .env lacks these, behave like production
ENV = os.getenv("ENV", "prod").strip().lower()            # default -> 'prod'
RECAPTCHA_BYPASS = os.getenv("RECAPTCHA_BYPASS", "0").strip().lower() in ("1","true","yes")

ALLOWED_HOSTS_PROD = {"adaptdelivery.org", "www.adaptdelivery.org"}
ALLOWED_HOSTS_DEV = {"127.0.0.1", "localhost", "0.0.0.0"}

import requests
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.modules.loss import L1Loss
from sklearn.preprocessing import StandardScaler


# —— Scaler helpers ——
class FrozenStandardScaler:
    """
    Apply (x - mean) / std using training parameters.
    Keep .transform(X) available to avoid refactoring the routes.
    """
    def __init__(self, mean: float, std: float):
        self.mean_ = float(mean)
        self.scale_ = float(std if std > 0 else 1.0)

    def transform(self, X):
        X = np.asarray(X, dtype=float)
        return (X - self.mean_) / self.scale_
        
    def inverse_transform(self, X):
        X = np.asarray(X, dtype=float)
        return X * self.scale_ + self.mean_
        
# === Scaler "prediction.py style": fit on TRAIN data, column 0 = Distance ===
def fit_scaler_from_train(data_dir: str, poly_name: str, scaler_feat: str = "gradius"):
    """
    Fit StandardScaler on train_data_{scaler_feat}.txt, column 0 = Distance,
    matching prediction.py. No .json files, no fit_*.txt files, no *_scaled.txt files.
    """
    train_file = os.path.join(data_dir, f"train_data_{scaler_feat}.txt")
    if not os.path.exists(train_file):
        raise FileNotFoundError(f"[SCALER] {poly_name}: missing {train_file}")

    X_train = np.loadtxt(train_file, usecols=(0,), dtype=float).reshape(-1, 1)
    scaler = StandardScaler().fit(X_train)
    mean = float(scaler.mean_[0])
    std  = float(np.sqrt(scaler.var_[0]))
  # print(f"[SCALER] {poly_name}: fitted on {os.path.basename(train_file)} (mean={mean:.6f}, std={std:.6f})")
    return scaler
    

#def load_scaler_params_or_fit(data_dir: str, feat: str, poly_name: str):
#    """
#    prediction.py style (.txt files only):
#      - ignore fit_{feat}_mean_std_value.txt and any *_scaled.txt files
#      - compute mean/std exclusively from train_data_{feat}.txt, column 0 = Distance
#      - return (mean, std)
#    """
#    import os
#    import numpy as np
#
#    train_file = os.path.join(data_dir, f"train_data_{feat}.txt")
#    if not os.path.exists(train_file):
#        raise FileNotFoundError(f"[SCALER] {poly_name}/{feat}: missing {train_file}")
#
#    X = np.loadtxt(train_file, usecols=(0,), dtype=float).reshape(-1, 1)
#    mean = float(np.mean(X))
#    std  = float(np.std(X, ddof=0))
#    if std <= 0:
#        std = 1.0  # numeric protection
#  # print(f"[SCALER] {poly_name}/{feat}: mean/std from TRAIN ({os.path.basename(train_file)}) -> {mean:.6f} {std:.6f}")
#    return mean, std
# —— End Scaler helpers ——


# —––––– Setup Flask + extensions –––––—
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# reCAPTCHA config, available to all blueprints
app.config['RECAPTCHA_SECRET_KEY'] = RECAPTCHA_SECRET_KEY
app.config['RECAPTCHA_SITE_KEY']   = RECAPTCHA_SITE_KEY

# Prod / dev switch
IS_PROD = ENV in {"prod", "production"}

app.config.update(
    # session
    SESSION_PERMANENT=True,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),

    # session cookie
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=IS_PROD,
)


@app.before_request
def refresh_session_timeout():
    session.modified = True

# Mail config
# Local/Gmail defaults are kept here as fallback.
# Production should override these values from .env.
def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

app.config.update(
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
    MAIL_USE_TLS=env_bool("MAIL_USE_TLS", True),
    MAIL_USE_SSL=env_bool("MAIL_USE_SSL", False),
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_DEFAULT_SENDER=('AdaptDelivery', os.getenv('MAIL_USERNAME'))
)

# Database setup
app.config.update(
    SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)

mail = Mail(app)
db.init_app(app)
app.register_blueprint(auth)
with app.app_context():
    #db.session.query(User).delete()
    #db.session.commit()
    #db.drop_all()
    #db.create_all()
    pass


def verify_recaptcha(response_token: str) -> bool:
    """
    Verify reCAPTCHA v2 token with Google's API.
    Behavior:
      - If RECAPTCHA_BYPASS True -> allow (dev)
      - Otherwise -> call Google siteverify, check success and hostname.
      - Hostname rules: if ENV == 'prod' accept only ALLOWED_HOSTS_PROD;
        if ENV == 'dev' accept ALLOWED_HOSTS_DEV OR ALLOWED_HOSTS_PROD.
    """
    if not response_token:
        return False

    # 1) bypass if explicitly enabled (dev)
    if RECAPTCHA_BYPASS:
        return True

    # 2) get secret
    secret = current_app.config.get("RECAPTCHA_SECRET_KEY") or RECAPTCHA_SECRET_KEY
    if not secret:
        return False

    # 3) call Google
    url = "https://www.google.com/recaptcha/api/siteverify"
    payload = {"secret": secret, "response": response_token}
    try:
        r = requests.post(url, data=payload, timeout=5)
        data = r.json()
    except Exception:
        return False

    if not data.get("success"):
        return False

    # 4) hostname check based on ENV
    hostname = data.get("hostname", "")
    if ENV == "prod":
        if hostname not in ALLOWED_HOSTS_PROD:
            return False
    else:  # dev
        if hostname not in (ALLOWED_HOSTS_DEV | ALLOWED_HOSTS_PROD):
            return False

    return True
        

# —––––– Model classes –––––—
torch.serialization.add_safe_globals([L1Loss])

class polymerGradius(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(1, 16)
        self.fc2 = nn.Linear(16, 8)
        self.fc3 = nn.Linear(8, 1)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        return self.fc3(x)

class polymerSasa(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(1, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 16)
        self.fc4 = nn.Linear(16, 8)
        self.fc5 = nn.Linear(8, 1)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        x = F.relu(self.fc4(x))
        return self.fc5(x)

# —––––– File paths and preload —––––—
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_ROOT = os.path.join(BASE_DIR, 'data')
MODELS_ROOT = os.path.join(BASE_DIR, 'models')

poly_folders_dict = {
    'PE': 'poly_PE',
    'PEI': 'poly_PEI',
    'PEO': 'poly_PEO',
    'PAAMR': 'poly_PAAMR',
    'PAM': 'poly_PAM',
    'PNIPAAMR': 'poly_PNIPAAMR',
    'PVMKR': 'poly_PVMKR',
    'GUAI': 'poly_GUAI',
    'PHP': 'poly_PHP',
    'SYR': 'poly_SYR'
}
# Polymers considered natural, with separate subfolders in models/ and data/
NATURAL_POLYMERS = {"GUAI", "PHP", "SYR"}

poly_feature_names = ['gradius', 'sasa']
scaled = True

mymodel_dict = {}
test_stats_dict = {}
scaler_dict = {}

# —––––– Preload models and data at startup —––––—
def preload_models_and_data():
    lossfn = nn.L1Loss()
    for poly_key, poly_folder in poly_folders_dict.items():
        for feat in poly_feature_names:
            subdir = "Natural" if poly_key in NATURAL_POLYMERS else "Synthetic"
            model_path = os.path.join(MODELS_ROOT, subdir, poly_folder, feat, f"model_{feat}_scaled.pth")
            if not os.path.exists(model_path):
                print(f" Skipping missing model: {model_path}")
                continue

            model = polymerGradius() if feat == 'gradius' else polymerSasa()
            ckpt = torch.load(model_path, map_location='cpu', weights_only=False)
            model.load_state_dict(ckpt['model_state_dict'])
            model.eval()
            mymodel_dict[f"{poly_key}_{feat}"] = model

            fname = f"test_data_{feat}" + ('' if not scaled else '_scaled') + '.txt'
            data_dir = os.path.join(DATA_ROOT, subdir, poly_folder, feat)
            data_path = os.path.join(data_dir, fname)
            if not os.path.exists(data_path):
                print(f" Skipping missing data: {data_path}")
                continue

            data_x, data_y = np.loadtxt(data_path, usecols=(0, 1), unpack=True)
            
            # 1-to-1 with prediction.py: fit on DISTANCE, column 0, from train_data_{feat}.txt
            sc = fit_scaler_from_train(data_dir, poly_key, scaler_feat=feat)  # already defined in app.py
            mean = float(sc.mean_[0])
            std  = float(np.sqrt(sc.var_[0]))
            scaler = FrozenStandardScaler(mean, std)
            scaler_dict[f"{poly_key}_{feat}"] = scaler

            # If scaled=True, the *_scaled.txt file already contains X in model space
            if scaled:
                data_x_model = data_x  # already stored in scaled space on disk
            else:
                data_x_model = scaler.transform(data_x.reshape(-1, 1)).flatten()

            xs, ys, errs = [], [], []
            for i in range(len(data_x)):
                xt = torch.tensor([[data_x_model[i]]]).float()
                yt = torch.tensor([[data_y[i]]]).float()
                with torch.no_grad():
                    y_hat = model(xt)
                    
                # For the UI/plot, use the real distance in natural units, not the z-scaled value.
                if scaled:
                    x_display = float(scaler.inverse_transform([[data_x_model[i]]])[0][0])
                else:
                    x_display = float(data_x[i])
                    
                xs.append(x_display)
                ys.append(y_hat.item())
                errs.append(lossfn(y_hat, yt).item())

            y_true_list = data_y.tolist()
            y_pred_list = ys

            test_stats_dict[f"{poly_key}_{feat}"] = {
                'test_x': xs,
                'test_y': y_pred_list,
                'test_y_pred': y_pred_list,
                'test_y_true': y_true_list,
                'avg_error': float(np.mean(errs)),
                'avg_pred': float(np.mean(y_pred_list))
            }

preload_models_and_data()


@app.route("/")
def index():
    return render_template("index.html", recaptcha_site_key=RECAPTCHA_SITE_KEY, recaptcha_bypass=RECAPTCHA_BYPASS)
    

def has_prediction_access():
    return bool(session.get('user') or session.get('guest'))
    
   
def save_prediction_history(polymer_name, monomer_number, property_name, predicted_value):
    """
    Save prediction history only for logged-in users.
    Guest users are allowed to use the platform, but their predictions are not stored.
    """
    user_id = session.get('user')

    # Guest users do not have user_id, so nothing is saved
    if not user_id:
        return

    try:
        history_row = PredictionHistory(
            user_id=user_id,
            polymer_name=str(polymer_name),
            monomer_number=int(monomer_number),
            property_name=str(property_name),
            predicted_value=round(float(predicted_value), 3)
        )

        db.session.add(history_row)
        db.session.commit()

    except Exception as e:
        current_app.logger.error(f"Failed to save prediction history: {e}")
        db.session.rollback()
      
        
@app.route('/history_data')
def history_data():
    """
    Return prediction history only for logged-in users.
    Guest users do not have prediction history.
    """
    user_id = session.get('user')

    if not user_id:
        return jsonify({
            'success': False,
            'message': 'Please log in to view prediction history.'
        }), 401

    rows = (
        PredictionHistory.query
        .filter_by(user_id=user_id)
        .order_by(PredictionHistory.created_at.desc())
        .limit(100)
        .all()
    )

    return jsonify({
        'success': True,
        'items': [row.to_dict() for row in rows]
    })
  

@app.route('/delete_history', methods=['POST'])
def delete_history():
    """
    Delete prediction history only for the currently logged-in user.
    Guest users do not have prediction history and cannot delete history.
    """
    user_id = session.get('user')

    if not user_id:
        return jsonify({
            'success': False,
            'message': 'Please log in to delete prediction history.'
        }), 401

    try:
        PredictionHistory.query.filter_by(user_id=user_id).delete()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Prediction history deleted successfully.'
        })

    except Exception as e:
        current_app.logger.error(f"Failed to delete prediction history: {e}")
        db.session.rollback()

        return jsonify({
            'success': False,
            'message': 'Could not delete prediction history.'
        }), 500


@app.route('/generate_gradius', methods=['POST'])
def generate_gradius():
    if not has_prediction_access():
        return jsonify({
            'success': False,
            'message': 'Please log in or access as Guest to use this feature.'
        }), 401
    
    payload = request.json or {}
    poly_name = payload.get('polymer_type', '')

    if poly_name not in poly_folders_dict:
        return jsonify({'success': False, 'message': f'Invalid polymer type: {poly_name}'}), 400

    try:
        raw_lengths = payload.get('lengths', [])
        if not isinstance(raw_lengths, list) or len(raw_lengths) != 1:
            raise ValueError("Please submit a single integer value.")
        length_value = int(raw_lengths[0])
        if length_value <= 0 or length_value > 1000:
            raise ValueError("Length must be a positive integer ≤ 1000.")
        lengths = [length_value]
    except (ValueError, TypeError) as e:
        return jsonify({'success': False, 'message': f'Invalid lengths input: {str(e)}'}), 400

    X_raw = np.array(lengths, dtype=float).reshape(-1, 1)

    key = f"{poly_name}_gradius"
    scaler = scaler_dict.get(key)
    model = mymodel_dict.get(key)
    stats = test_stats_dict.get(key)
    if scaler is None or model is None or stats is None:
        return jsonify({'success': False, 'message': f'Missing model or scaler for {key}'}), 400

    X_scaled = scaler.transform(X_raw)
    xt = torch.from_numpy(X_scaled).float()
    
    with torch.no_grad():
        y_pred = model(xt).detach().cpu().numpy().flatten()

    # Save prediction history only for logged-in users, not for Guest users
    save_prediction_history(
        polymer_name=poly_name,
        monomer_number=length_value,
        property_name='Rg',
        predicted_value=y_pred[0]
    )

    return jsonify({
        'polymer': poly_name,
        'Distance': X_raw.flatten().tolist(),
        'pred_gradius': y_pred.tolist(),
        'gradius_test_x': stats['test_x'],
        'gradius_test_y': stats['test_y'],          
        'gradius_test_y_pred': stats['test_y_pred'],
        'gradius_test_y_true': stats['test_y_true'],
        'gradius_avg_error_gradius': stats['avg_error'],
        'gradius_avg_pred_gradius': stats['avg_pred'],
        'success': True
    })
    

@app.route('/generate_sasa', methods=['POST'])
def generate_sasa():
    if not has_prediction_access():
        return jsonify({
            'success': False,
            'message': 'Please log in or access as Guest to use this feature.'
        }), 401
    
    payload = request.json or {}
    poly_name = payload.get('polymer_type', '')

    if poly_name not in poly_folders_dict:
        return jsonify({'success': False, 'message': f'Invalid polymer type: {poly_name}'}), 400

    try:
        raw_lengths = payload.get('lengths', [])
        if not isinstance(raw_lengths, list) or len(raw_lengths) != 1:
            raise ValueError("Please submit a single integer value.")
        length_value = int(raw_lengths[0])
        if length_value <= 0 or length_value > 1000:
            raise ValueError("Length must be a positive integer ≤ 1000.")
        lengths = [length_value]
    except (ValueError, TypeError) as e:
        return jsonify({'success': False, 'message': f'Invalid lengths input: {str(e)}'}), 400

    X_raw = np.array(lengths, dtype=float).reshape(-1, 1)

    key = f"{poly_name}_sasa"
    scaler = scaler_dict.get(key)
    model = mymodel_dict.get(key)
    stats = test_stats_dict.get(key)
    if scaler is None or model is None or stats is None:
        return jsonify({'success': False, 'message': f'Missing model or scaler for {key}'}), 400

    X_scaled = scaler.transform(X_raw)
    xt = torch.from_numpy(X_scaled).float()
    
    with torch.no_grad():
        y_pred = model(xt).detach().cpu().numpy().flatten()

    # Save prediction history only for logged-in users, not for Guest users
    save_prediction_history(
        polymer_name=poly_name,
        monomer_number=length_value,
        property_name='SASA',
        predicted_value=y_pred[0]
    )

    return jsonify({
        'polymer': poly_name,
        'Distance': X_raw.flatten().tolist(),
        'pred_sasa': y_pred.tolist(),
        'sasa_test_x': stats['test_x'],
        'sasa_test_y': stats['test_y'],
        'sasa_test_y_pred': stats['test_y_pred'],
        'sasa_test_y_true': stats['test_y_true'],
        'sasa_avg_error_sasa': stats['avg_error'],
        'sasa_avg_pred_sasa': stats['avg_pred'],
        'success': True
    })


@app.route('/generate_diffusion', methods=['POST'])
def generate_diffusion():
    if not has_prediction_access():
        return jsonify({
            'success': False,
            'message': 'Please log in or access as Guest to use this feature.'
        }), 401
        
    return jsonify({'success': False, 'message': 'Diffusion prediction not yet implemented.'}), 501


### PDB generators (linear/curved) for the 3D viewer (3Dmol.js) ###

# ============================================================
# PDB GENERATOR LOADER (NO __init__.py)
# Scans: pdb_generators/linear/*.py and pdb_generators/curved/*.py
# ============================================================

_PDB_GENERATOR_REGISTRY = None

def _pdb_load_module_from_path(py_path: str):
    module_name = "gen_" + re.sub(r"[^a-zA-Z0-9_]", "_", py_path)
    spec = importlib.util.spec_from_file_location(module_name, py_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from: {py_path}")
    mod = importlib.util.module_from_spec(spec)

    # IMPORTANT: register in sys.modules BEFORE exec_module
    sys.modules[module_name] = mod

    spec.loader.exec_module(mod)
    return mod

def _pdb_find_generate_func(mod):
    # Find the first generate_* function
    for name in dir(mod):
        if name.startswith("generate_"):
            fn = getattr(mod, name)
            if callable(fn):
                return name, fn
    return None, None

def _pdb_build_registry():
    registry = {}
    gen_base = os.path.join(BASE_DIR, "pdb_generators")

    for folder in ("linear", "curved"):
        folder_path = os.path.join(gen_base, folder)
        if not os.path.isdir(folder_path):
            continue

        for fname in os.listdir(folder_path):
            if not fname.endswith(".py"):
                continue
            py_path = os.path.join(folder_path, fname)

            mod = _pdb_load_module_from_path(py_path)
            gen_name, gen_fn = _pdb_find_generate_func(mod)
            if not gen_fn:
                continue

            # generate_pe -> "PE"
            key = gen_name.replace("generate_", "").upper().strip()
            registry[key] = gen_fn

    return registry

def pdb_generate_pdb_text(polymer_type: str, n: int) -> str:
    """
    Run the generator and return PDB text read from a temporary file.
    Supports different signatures without modifying the generators:
      - generate_pe(n, out_pdb, ...)
      - generate_xxx(n, out_path=...)
      - generate_xxx(n, out_pdb=...)
      - generate_xxx(n, output_path=...)
      - fallback: generate_xxx(n, path) positional
    """
    global _PDB_GENERATOR_REGISTRY
    if _PDB_GENERATOR_REGISTRY is None:
        _PDB_GENERATOR_REGISTRY = _pdb_build_registry()

    key = (polymer_type or "").strip().upper()
    if key not in _PDB_GENERATOR_REGISTRY:
        raise KeyError(f"No generator for type '{polymer_type}'. Available: {sorted(_PDB_GENERATOR_REGISTRY.keys())}")

    gen_fn = _PDB_GENERATOR_REGISTRY[key]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdb") as tf:
        out_path = tf.name

    try:
        try:
            gen_fn(int(n), out_path=out_path)
        except TypeError:
            try:
                gen_fn(int(n), out_pdb=out_path)
            except TypeError:
                try:
                    gen_fn(int(n), output_path=out_path)
                except TypeError:
                    gen_fn(int(n), out_path)  # positional (n, path)

        with open(out_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    finally:
        try:
            os.remove(out_path)
        except Exception:
            pass


@app.route("/pdb_polymer")
def pdb_polymer():
    if not has_prediction_access():
        return current_app.response_class(
            "3D viewer error: Please log in or access as Guest to use this feature.",
            status=401,
            mimetype="text/plain",
        )

    polymer = (request.args.get("type") or "").strip()
    
    if not polymer:
        return current_app.response_class(
            "3D viewer error: type is required.",
            status=400,
            mimetype="text/plain",
        )

    n_raw = (request.args.get("n") or "").strip()

    # validate n: int, 1..1000
    try:
        n = int(n_raw)
    except Exception:
        return current_app.response_class(
            "3D viewer error: n must be an integer.",
            status=400,
            mimetype="text/plain",
        )

    if n < 1 or n > 1000:
        return current_app.response_class(
            "3D viewer error: n must be in [1, 1000].",
            status=400,
            mimetype="text/plain",
        )

    try:
        pdb_text = pdb_generate_pdb_text(polymer, n)
        return current_app.response_class(pdb_text, mimetype="chemical/x-pdb")

    except KeyError:
        return current_app.response_class(
            "3D viewer error: Unknown polymer type (no generator found).",
            status=400,
            mimetype="text/plain",
        )

    except Exception as e:
        return current_app.response_class(
            f"3D viewer error: {e}",
            status=500,
            mimetype="text/plain",
        )
        
###  END PDB generators ###



# —––––– Cleanup scheduler –––––—
if __name__ == '__main__':
    def delete_old_unconfirmed_users():
        with app.app_context():
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            old = User.query.filter(
                User.is_confirmed == False,
                User.last_confirmation_sent < cutoff
            ).all()
            for u in old:
                db.session.delete(u)
            db.session.commit()
            
    def delete_old_prediction_history():
        with app.app_context():
            cutoff = datetime.utcnow() - timedelta(days=30)

            deleted_count = (
                PredictionHistory.query
                .filter(PredictionHistory.created_at < cutoff)
                .delete(synchronize_session=False)
            )

            db.session.commit()
            current_app.logger.info(
                f"Deleted {deleted_count} prediction history rows older than 30 days."
            )

    def send_backup_confirmation_emails():
        with app.app_context():
            if not env_bool("MAIL_BACKUP_ENABLED", False):
                return

            backup_username = os.getenv("BACKUP_MAIL_USERNAME")
            backup_password = os.getenv("BACKUP_MAIL_PASSWORD")
            if not backup_username or not backup_password:
                current_app.logger.warning("Backup mail skipped: missing Gmail backup credentials.")
                return

            delay_seconds = int(os.getenv("MAIL_BACKUP_DELAY_SECONDS", "240"))
            cutoff = datetime.now() - timedelta(seconds=delay_seconds)
            base_url = os.getenv("PUBLIC_BASE_URL", "https://adaptdelivery.org").rstrip("/")

            users = User.query.filter(
                User.is_confirmed == False,
                User.backup_confirm_email_sent == False,
                User.last_confirmation_sent.isnot(None),
                User.last_confirmation_sent < cutoff
            ).all()

            for user in users:
                if not user.confirmation_token:
                    continue

                confirmation_url = f"{base_url}/confirm/{user.confirmation_token}"
                body = f"""Hello {user.name},

Thank you for creating an account with AdaptDelivery.

To activate your account, open the link below and then click the "Confirm Email" button on the confirmation page:
{confirmation_url}

This extra confirmation step helps protect your account from automated email scanners.

If you did not create this account, you can safely ignore this email.
"""

                msg = MIMEText(body, "plain", "utf-8")
                msg["Subject"] = "Confirm Your Email - AdaptDelivery"
                msg["From"] = formataddr(("AdaptDelivery", backup_username))
                msg["To"] = user.email

                try:
                    context = ssl.create_default_context()
                    with smtplib.SMTP(os.getenv("BACKUP_MAIL_SERVER", "smtp.gmail.com"), int(os.getenv("BACKUP_MAIL_PORT", "587")), timeout=20) as smtp:
                        smtp.starttls(context=context)
                        smtp.login(backup_username, backup_password)
                        smtp.send_message(msg)

                    user.backup_confirm_email_sent = True
                    db.session.commit()
                    current_app.logger.info(f"Backup confirmation email sent to {user.email}")
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.warning(f"Backup confirmation email failed for {user.email}: {e}")
                    
    def send_backup_reset_emails():
        with app.app_context():
            if not env_bool("MAIL_BACKUP_ENABLED", False):
                return

            backup_username = os.getenv("BACKUP_MAIL_USERNAME")
            backup_password = os.getenv("BACKUP_MAIL_PASSWORD")
            if not backup_username or not backup_password:
                current_app.logger.warning("Backup reset mail skipped: missing Gmail backup credentials.")
                return

            delay_seconds = int(os.getenv("MAIL_BACKUP_DELAY_SECONDS", "240"))
            cutoff = datetime.now() - timedelta(seconds=delay_seconds)
            base_url = os.getenv("PUBLIC_BASE_URL", "https://adaptdelivery.org").rstrip("/")

            users = User.query.filter(
                User.is_confirmed == True,
                User.backup_reset_email_pending == True,
                User.last_confirmation_sent.isnot(None),
                User.last_confirmation_sent < cutoff
            ).all()

            serializer = URLSafeTimedSerializer(app.secret_key)

            for user in users:
                token = serializer.dumps(user.email, salt='password-reset-salt')
                reset_url = f"{base_url}/reset_password/{token}"

                body = f"""Hello {user.name},

We received a request to reset your AdaptDelivery account password.

To choose a new password, open the link below:
{reset_url}

If you did not request this, you can safely ignore this email.
"""

                msg = MIMEText(body, "plain", "utf-8")
                msg["Subject"] = "Reset Your Password - AdaptDelivery"
                msg["From"] = formataddr(("AdaptDelivery", backup_username))
                msg["To"] = user.email

                try:
                    context = ssl.create_default_context()
                    with smtplib.SMTP(os.getenv("BACKUP_MAIL_SERVER", "smtp.gmail.com"), int(os.getenv("BACKUP_MAIL_PORT", "587")), timeout=20) as smtp:
                        smtp.starttls(context=context)
                        smtp.login(backup_username, backup_password)
                        smtp.send_message(msg)

                    user.backup_reset_email_pending = False
                    db.session.commit()
                    current_app.logger.info(f"Backup reset email sent to {user.email}")
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.warning(f"Backup reset email failed for {user.email}: {e}")

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(delete_old_unconfirmed_users, 'interval', hours=24)
    scheduler.add_job(delete_old_prediction_history, 'interval', hours=24)
    scheduler.add_job(send_backup_confirmation_emails, 'interval', minutes=1)
    scheduler.add_job(send_backup_reset_emails, 'interval', minutes=1)
    scheduler.start()

    import atexit
    atexit.register(lambda: scheduler.shutdown())

    app.run(host=os.getenv("APP_HOST", "0.0.0.0"), port=int(os.getenv("APP_PORT", "5000")), debug=env_bool("APP_DEBUG", False), use_reloader=False)
    #app.run(debug=True, host='0.0.0.0')