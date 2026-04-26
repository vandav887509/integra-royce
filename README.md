# integra-royce

**IGN2932M75 — Bond Pull Data Control Charts**

Flask web portal displaying interactive Plotly control charts for bond pull data,
filtered per machine (B21, B24, B25, B27) and bond type (Type 1, 2, 3 Short, 3 Long).

## Stack
- **Python / Flask** — web framework
- **Pandas** — CSV data processing
- **Plotly** — interactive charts
- **Gunicorn + Nginx** — production deployment

## Quick start
```bash
pip install -r requirements.txt
cp RoyceData.csv .
python app.py
```

See [DEPLOY.md](DEPLOY.md) for full server setup.
