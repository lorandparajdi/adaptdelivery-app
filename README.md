# AdaptDelivery Web App

AdaptDelivery is a Flask-based web application for polymer property prediction and interactive polymer structure generation.

This public repository contains a limited demo version of the platform. It preserves the main application structure while including only selected demo assets for:

- GUAI, a natural polymer unit
- PEI, a synthetic polymer

The full production model collection, dataset collection and generator library are not included in this public version.

## Features

- Polymer property prediction
- Radius of gyration prediction
- Solvent-accessible surface area prediction
- PDB structure generation for included demo polymers
- User signup and login
- Email confirmation
- Password reset
- Optional backup email delivery
- Optional Google reCAPTCHA protection
- Prediction history for registered users

## Repository Contents

```text
models/
  Natural/poly_GUAI/
  Synthetic/poly_PEI/

data/
  Natural/poly_GUAI/
  Synthetic/poly_PEI/

pdb_generators/
  linear/linearGUAIgenerator.py
  linear/linearPEIgenerator.py
```

The application code keeps the same general structure as the production platform, but predictions are expected to work only for the polymers whose model, data and generator files are included in this repository.
This public version includes complete working assets for GUAI and PEI only. Additional polymer folders can be added following the same `data/`, `models/` and `pdb_generators/` structure.

## ANN Input and Representative Models

The input variable used by each property-specific artificial neural network (ANN) is the polymer monomer number, denoted by `x`, within the supported range of 1–1000 monomers. 
For each supported polymer, separate property-specific ANN models are used to predict the radius of gyration (Rg) and solvent-accessible surface area (SASA).

The public repository includes representative input data and trained `.pth` models for GUAI and PEI. 
The datasets consist of `(monomer number, polymer property)` pairs generated from power-law fits to structural descriptor values obtained from molecular dynamics simulations. 
The same input structure and model-integration workflow are used for the other supported polymers.

## Setup

Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create your local environment file:

```bash
cp .env.example .env
```

Then edit `.env` with your own database, email and reCAPTCHA settings.

## Environment Variables

Configuration is loaded from `.env`.

The public repository includes only `.env.example`. Do not commit real credentials.

Important variables include:

```env
SECRET_KEY=
DATABASE_URL=

ENV=dev
APP_HOST=0.0.0.0
APP_PORT=5000
APP_DEBUG=true

MAIL_SERVER=
MAIL_PORT=
MAIL_USERNAME=
MAIL_PASSWORD=

RECAPTCHA_BYPASS=1
RECAPTCHA_SITE_KEY=
RECAPTCHA_SECRET_KEY=
```

Optional backup email delivery can be configured with:

```env
MAIL_BACKUP_ENABLED=false
MAIL_BACKUP_DELAY_SECONDS=240
BACKUP_MAIL_SERVER=
BACKUP_MAIL_PORT=
BACKUP_MAIL_USERNAME=
BACKUP_MAIL_PASSWORD=
```

## Database

AdaptDelivery uses PostgreSQL through SQLAlchemy.

Main tables:

- `user`
- `guest_users`
- `prediction_history`

## Run

```bash
python app.py
```

The app will start using `APP_HOST` and `APP_PORT` from `.env`.

## Security

Do not commit:

- `.env`
- passwords
- API keys
- SMTP credentials
- database credentials
- reCAPTCHA secrets
- virtual environments
- cache files

## License

This repository is made available under a restricted academic review license. See `LICENSE` for details.

## Contact

For inquiries or collaborations:

```text
contact@adaptdelivery.org
```