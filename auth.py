import os, requests
import ipaddress
import re
from flask import Blueprint, request, session, jsonify, url_for, current_app, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from datetime import datetime, timezone

# safe defaults: if .env lacks these, behave like production
ENV = os.getenv("ENV", "prod").strip().lower()
RECAPTCHA_BYPASS = os.getenv("RECAPTCHA_BYPASS", "0").strip().lower() in ("1","true","yes")

ALLOWED_HOSTS_PROD = {"adaptdelivery.org", "www.adaptdelivery.org"}
ALLOWED_HOSTS_DEV = {"127.0.0.1", "localhost", "0.0.0.0"}

auth = Blueprint('auth', __name__)
db = SQLAlchemy()
mail = Mail()

# SQLAlchemy User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    organization = db.Column(db.String(200))
    affiliation = db.Column(db.String(100))
    is_confirmed = db.Column(db.Boolean, default=False)
    confirmation_token = db.Column(db.String(256), nullable=True)
    last_confirmation_sent = db.Column(db.DateTime, nullable=True)
    backup_confirm_email_sent = db.Column(db.Boolean, default=False, nullable=False)
    backup_reset_email_pending = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'organization': self.organization,
            'affiliation': self.affiliation
        }


class PredictionHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    polymer_name = db.Column(db.String(100), nullable=False)
    monomer_number = db.Column(db.Integer, nullable=False)
    property_name = db.Column(db.String(20), nullable=False)
    predicted_value = db.Column(db.Float, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'polymer_name': self.polymer_name,
            'monomer_number': self.monomer_number,
            'property_name': self.property_name,
            'predicted_value': self.predicted_value,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class GuestUser(db.Model):
    __tablename__ = 'guest_users'

    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    region = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    timezone = db.Column(db.String(100), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    device_type = db.Column(db.String(30), nullable=True)
    referrer = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


def safe_delta_seconds(a, b):
    if a is None or b is None:
        return None
    if a.tzinfo is None:
        a = a.replace(tzinfo=timezone.utc)
    if b.tzinfo is None:
        b = b.replace(tzinfo=timezone.utc)
    return (a - b).total_seconds()


def verify_recaptcha_token(token, min_score=0.0):
    """
    Verify the reCAPTCHA token (v2/v3) using siteverify.
    Return (True, info_dict) or (False, info_dict).
    """
    if not token:
        return False, {"reason": "missing-token"}

    # 1) BYPASS (explicit)
    if RECAPTCHA_BYPASS:
        return True, {"bypass": True}

    # 2) secret
    secret = current_app.config.get("RECAPTCHA_SECRET_KEY") or os.getenv("RECAPTCHA_SECRET_KEY")
    if not secret:
        return False, {"reason": "missing-secret"}

    # 3) call Google
    url = "https://www.google.com/recaptcha/api/siteverify"
    payload = {"secret": secret, "response": token}
    try:
        r = requests.post(url, data=payload, timeout=5)
        data = r.json()
    except Exception as e:
        return False, {"reason": "exception", "error": str(e)}

    if not data.get("success"):
        return False, {"reason": "verify-failed", "details": data.get("error-codes")}

    # 4) hostname check based on ENV
    hostname = data.get("hostname", "")
    if ENV == "prod":
        if hostname not in ALLOWED_HOSTS_PROD:
            return False, {"reason": "bad-hostname", "hostname": hostname}
    else:  # dev
        if hostname not in (ALLOWED_HOSTS_DEV | ALLOWED_HOSTS_PROD):
            return False, {"reason": "bad-hostname", "hostname": hostname}

    # 5) optional: v3 score/action checks left intact (caller supplies min_score)
    return True, data


@auth.route('/status')
def status():
    # Logged-in user
    if 'user' in session:
        user = User.query.get(session['user'])
        if not user or not user.is_confirmed:
            # Force logout if invalid/unconfirmed
            session.pop('user', None)
            session.pop('guest', None)
            return jsonify({'loggedIn': False, 'guest': False})

        return jsonify({
            'loggedIn': True,
            'guest': False,
            'name': user.name
        })

    # Guest session
    if session.get('guest'):
        return jsonify({
            'loggedIn': False,
            'guest': True,
            'name': 'Guest'
        })

    # Not authenticated
    return jsonify({'loggedIn': False, 'guest': False})


@auth.route('/signup', methods=['POST'])
def signup():
    data = request.get_json(silent=True) or {}
    
    # --- reCAPTCHA server-side verification ---
    recaptcha_token = data.get('recaptchaToken') or data.get('g-recaptcha-response')
    ok, info = verify_recaptcha_token(recaptcha_token, min_score=0.5)
    if not ok:
        # Log for debugging, visible in stdout / journalctl
        current_app.logger.warning(f"recaptcha signup failed: {info}")
        return jsonify({'success': False, 'code': 'RECAPTCHA_FAILED', 'message': 'reCAPTCHA verification failed.'}), 400

    # Required fields validation
    required_fields = ['name', 'email', 'password', 'organization', 'affiliation']
    for field in required_fields:
        if not data.get(field) or data[field].strip() == '':
            return jsonify({'success': False, 'code': 'MISSING_FIELDS', 'message': f'Missing or empty field: {field}'}), 400

    # Password strength validation
    password = data['password']
    if len(password) < 8:
        return jsonify({'success': False, 'code': 'WEAK_PASSWORD', 'message': 'Password must be at least 8 characters long.'}), 400
    if not re.search(r'[A-Z]', password):
        return jsonify({'success': False, 'code': 'WEAK_PASSWORD', 'message': 'Password must contain at least one uppercase letter.'}), 400
    if not re.search(r'[a-z]', password):
        return jsonify({'success': False, 'code': 'WEAK_PASSWORD', 'message': 'Password must contain at least one lowercase letter.'}), 400
    if not re.search(r'\d', password):
        return jsonify({'success': False, 'code': 'WEAK_PASSWORD', 'message': 'Password must contain at least one number.'}), 400
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return jsonify({'success': False, 'code': 'WEAK_PASSWORD', 'message': 'Password must contain at least one special character.'}), 400

    # Normalize email
    email = data['email'].strip().lower()

    # Email format
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({'success': False, 'code': 'INVALID_EMAIL_FORMAT', 'message': 'Invalid email format.'}), 400

    # Check if email already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        now = datetime.now(timezone.utc)
        delta = safe_delta_seconds(now, existing_user.last_confirmation_sent)

        if delta is not None:
            if delta < -10:
                current_app.logger.warning("System clock appears out of sync. Skipping rate-limit check.")
            elif delta < 300:
                return jsonify({'success': False, 'message': 'Please wait before requesting another confirmation email.'}), 429

        return jsonify({'success': False, 'code': 'EMAIL_EXISTS'}), 200

    # Hash the password
    hashed_pw = generate_password_hash(password)

    # Create user
    user = User(
        name=data['name'],
        email=email,
        password=hashed_pw,
        organization=data.get('organization'),
        affiliation=data.get('affiliation')
    )

    db.session.add(user)
    db.session.commit()

    # Generate token
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    token = serializer.dumps(user.email, salt='email-confirm')
    user.confirmation_token = token
    user.last_confirmation_sent = datetime.now(timezone.utc)
    db.session.commit()

    # Build confirmation link
    confirmation_url = url_for('auth.confirm_email', token=token, _external=True)

    msg = Message(
        subject='Confirm Your Email - AdaptDelivery',
        sender=('AdaptDelivery', current_app.config['MAIL_USERNAME']),
        recipients=[user.email]
    )
    msg.body = f"""Hello {user.name},

Thank you for creating an account with AdaptDelivery.

To activate your account, open the link below and then click the "Confirm Email" button on the confirmation page:
{confirmation_url}

This extra confirmation step helps protect your account from automated email scanners.

If you did not create this account, you can safely ignore this email.
"""

    mail.send(msg)

    return jsonify({'success': True, 'redirect': '/confirm_status'})



@auth.route('/confirm/<token>', methods=['GET', 'POST'])
def confirm_email(token):
    if request.method != 'POST':
        return redirect(f'/?email_status=confirm_pending&confirm_token={token}')

    serializer = URLSafeTimedSerializer(current_app.secret_key)
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=86400)
    except SignatureExpired:
        return jsonify({'success': False, 'status': 'expired'}), 400
    except BadSignature as e:
        current_app.logger.warning(f"Invalid email confirmation token: {e}")
        return jsonify({'success': False, 'status': 'invalid'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        current_app.logger.warning(f"No user found for email confirmation: {email}")
        return jsonify({'success': False, 'status': 'invalid'}), 400

    if user.is_confirmed:
        current_app.logger.info(f"User already confirmed: {email}")
        return jsonify({'success': True, 'status': 'already'})

    user.is_confirmed = True
    db.session.commit()
    session.pop('user', None)
    current_app.logger.info(f"Email confirmed successfully: {email}")

    return jsonify({'success': True, 'status': 'success'})



@auth.route('/forgot_password', methods=['POST'])
def forgot_password():
    data = request.get_json(silent=True) or {}

    # --- reCAPTCHA server-side verification for Forgot Password ---
    recaptcha_token = data.get('recaptchaToken') or data.get('g-recaptcha-response')
    ok, info = verify_recaptcha_token(recaptcha_token, min_score=0.3)
    if not ok:
        current_app.logger.warning(f"recaptcha forgot_password failed: {info}")
        return jsonify({
            'success': False,
            'code': 'RECAPTCHA_FAILED',
            'message': 'reCAPTCHA verification failed.'
        }), 400

    email = data.get('email', '').strip().lower()
    
    # 1. Check if empty
    if not email:
        return jsonify({'success': False, 'code': 'MISSING_EMAIL', 'message': 'Email is required.'}), 400

    # 2. Validate email format
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({'success': False, 'code': 'INVALID_EMAIL_FORMAT', 'message': 'Invalid email format.'}), 400

    # 3. Look up user, with a generic response for security
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'success': True, 'message': 'If that email is registered, a reset link has been sent.'}), 200

    # 4. Rate-limit protection with robust validation
    now = datetime.now(timezone.utc)
    delta = safe_delta_seconds(now, user.last_confirmation_sent)

    if delta is not None:
        if delta < -10:
            current_app.logger.warning("System clock appears out of sync. Skipping rate-limit check.")
        elif delta < 300:
            return jsonify({'success': False, 'message': 'Please wait before requesting another reset email.'}), 429

    # 5. Create token and send email
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    token = serializer.dumps(user.email, salt='password-reset-salt')
    reset_url = url_for('auth.reset_password', token=token, _external=True)

    msg = Message(
        subject='Reset Your Password - AdaptDelivery',
        sender=('AdaptDelivery', current_app.config['MAIL_USERNAME']),
        recipients=[user.email]
    )
    msg.body = f"""Hello {user.name},

We received a request to reset your AdaptDelivery account password.

To choose a new password, open the link below:
{reset_url}

If you did not request this, you can safely ignore this email.
"""
    
    mail.send(msg)

    # 6. Save the new send timestamp
    user.last_confirmation_sent = now
    user.backup_reset_email_pending = True
    db.session.commit()

    return jsonify({'success': True, 'message': 'If that email is registered, a reset link has been sent.'})



@auth.route('/reset_password/<token>', methods=['GET'])
def reset_password(token):
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=86400)
    except (SignatureExpired, BadSignature):
        return redirect('/?email_status=reset_expired')

    user = User.query.filter_by(email=email).first()
    if not user:
        return redirect('/?email_status=reset_invalid')

    # ✅ Store user ID in session
    session['reset_user'] = user.id

    # ✅ Redirect back to main page where JS will show reset modal
    return redirect('/?email_status=reset_ready')



@auth.route('/reset_password', methods=['POST'])
def reset_password_from_modal():   # Name must match the route
    user_id = session.get('reset_user')
    if not user_id:
        return jsonify({'success': False, 'message': 'Session expired. Please restart password recovery.'})

    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'})

    data = request.get_json(silent=True) or {}
    new_password = data.get('password', '')
    
    # 1. Check if the password is empty
    if not new_password.strip():
        return jsonify({'success': False, 'code': 'EMPTY_PASSWORD', 'message': 'Password is required.'}), 400

    # 2. More detailed validation with error codes
    if len(new_password) < 8:
        return jsonify({'success': False, 'code': 'WEAK_PASSWORD_LENGTH', 'message': 'Password must be at least 8 characters long.'}), 400
    if not re.search(r'[A-Z]', new_password):
        return jsonify({'success': False, 'code': 'WEAK_PASSWORD_UPPER', 'message': 'Password must contain at least one uppercase letter.'}), 400
    if not re.search(r'[a-z]', new_password):
        return jsonify({'success': False, 'code': 'WEAK_PASSWORD_LOWER', 'message': 'Password must contain at least one lowercase letter.'}), 400
    if not re.search(r'\d', new_password):
        return jsonify({'success': False, 'code': 'WEAK_PASSWORD_DIGIT', 'message': 'Password must contain at least one number.'}), 400
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
        return jsonify({'success': False, 'code': 'WEAK_PASSWORD_SPECIAL', 'message': 'Password must contain at least one special character.'}), 400

    user.password = generate_password_hash(new_password)
    user.backup_reset_email_pending = False
    db.session.commit()
    session.pop('reset_user', None)

    return jsonify({'success': True})



@auth.route('/confirm_status')
def confirm_status():
    return jsonify({"status": "pending"})



@auth.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    
    # reCAPTCHA server-side verification for login
    recaptcha_token = data.get('recaptchaToken') or data.get('g-recaptcha-response')
    ok, info = verify_recaptcha_token(recaptcha_token, min_score=0.3)
    if not ok:
        current_app.logger.warning(f"recaptcha login failed: {info}")
        return jsonify({'success': False, 'code': 'RECAPTCHA_FAILED', 'message': 'reCAPTCHA verification failed.'}), 400

    # 1. Validate missing fields
    if not data.get('email') or not data.get('password'):
        return jsonify({'success': False, 'code': 'MISSING_CREDENTIALS', 'message': 'Email and password are required.'}), 400

    # 2. Validate email format
    email = data.get('email', '').strip().lower()
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({'success': False, 'code': 'INVALID_EMAIL_FORMAT', 'message': 'Invalid email format.'}), 400

    password = data.get('password', '')

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({'success': False, 'code': 'INVALID_CREDENTIALS'}), 200

    if not user.is_confirmed:
        return jsonify({'success': False, 'code': 'EMAIL_UNCONFIRMED_RESENT'}), 200

    if not check_password_hash(user.password, password):
        return jsonify({'success': False, 'code': 'INVALID_CREDENTIALS'}), 200

    session['user'] = user.id   # Create session after successful login
    session.pop('guest', None)  # Remove guest mode when real login succeeds
    session.permanent = True

    return jsonify({'success': True}), 200


def get_client_ip():
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()

    return request.headers.get('X-Real-IP') or request.remote_addr


def is_public_ip(ip_address):
    try:
        ip = ipaddress.ip_address(ip_address)
        return not (
            ip.is_private
            or ip.is_loopback
            or ip.is_reserved
            or ip.is_multicast
        )
    except Exception:
        return False


def get_guest_location(ip_address):
    if not ip_address or not is_public_ip(ip_address):
        return {}

    try:
        response = requests.get(
            f"http://ip-api.com/json/{ip_address}",
            params={"fields": "status,country,regionName,city,timezone"},
            timeout=3
        )
        data = response.json()

        if data.get("status") != "success":
            return {}

        return {
            "country": data.get("country"),
            "region": data.get("regionName"),
            "city": data.get("city"),
            "timezone": data.get("timezone")
        }

    except Exception as e:
        current_app.logger.warning(f"Guest location lookup failed: {e}")
        return {}


def detect_device_type(user_agent):
    ua = (user_agent or '').lower()

    if 'ipad' in ua or 'tablet' in ua or ('android' in ua and 'mobile' not in ua):
        return 'tablet'

    if 'mobile' in ua or 'iphone' in ua or 'android' in ua:
        return 'mobile'

    return 'desktop'


def save_guest_user():
    try:
        ip_address = get_client_ip()
        user_agent = request.headers.get('User-Agent', '')
        location = get_guest_location(ip_address)

        guest_user = GuestUser(
            ip_address=ip_address,
            country=location.get("country"),
            region=location.get("region"),
            city=location.get("city"),
            timezone=location.get("timezone"),
            user_agent=user_agent,
            device_type=detect_device_type(user_agent),
            referrer=request.headers.get('Referer')
        )

        db.session.add(guest_user)
        db.session.commit()

    except Exception as e:
        current_app.logger.error(f"Failed to save guest user: {e}")
        db.session.rollback()


@auth.route('/guest', methods=['POST'])
def guest_login():
    data = request.get_json(silent=True) or {}

    # reCAPTCHA server-side verification for Guest access
    recaptcha_token = data.get('recaptchaToken') or data.get('g-recaptcha-response')
    ok, info = verify_recaptcha_token(recaptcha_token, min_score=0.3)

    if not ok:
        current_app.logger.warning(f"recaptcha guest failed: {info}")
        return jsonify({
            'success': False,
            'code': 'RECAPTCHA_FAILED',
            'message': 'reCAPTCHA verification failed.'
        }), 400

    # Start a guest session without creating a user account
    session.pop('user', None)
    session['guest'] = True
    session.permanent = True
    
    save_guest_user()

    return jsonify({'success': True, 'guest': True}), 200



@auth.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    session.pop('guest', None)
    session.pop('reset_user', None)
    return jsonify({'success': True})