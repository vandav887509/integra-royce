# IGN2932M75 — Bond Pull QC Dashboard

## Version 0.1 — Stable Release

A static HTML dashboard served via Nginx displaying bond pull control charts for the IGN2932M75 product across 4 bonder machines (B21, B24, B25, B27).

## Stack
- **Frontend:** Static HTML + Chart.js 2.9.x
- **Data pipeline:** Python (`scripts/process_csv.py`) reads `RoyceData.csv` → generates `dashboard/data/machine-data.json`
- **Server:** Ubuntu 22.04 + Nginx (serves `dashboard/` folder)
- **SSL:** Let's Encrypt via Certbot
- **URL:** https://chart.integratech.com

## Features
- 4 machines: B21, B24, B25, B27
- 4 bond types per machine: Type 1, Type 2, Type 3 Short, Type 3 Long
- KPI cards showing latest value + previous + % change
- Control charts with LCL=8 spec limit line
- Data table view
- Excel file downloads per machine
- Dark sidebar + light main content area

## Updating data
```bash
cd /opt/bondapp
source venv/bin/activate
python3 scripts/process_csv.py \
    --csv /opt/bondapp/RoyceData.csv \
    --out /opt/bondapp/dashboard/data/machine-data.json
python3 -c "
import json
data = json.load(open('/opt/bondapp/dashboard/data/machine-data.json'))
js = 'window.MACHINE_DATA = ' + json.dumps(data, indent=2) + ';'
open('/opt/bondapp/dashboard/js/machine-data.js', 'w').write(js)
print('Done')
"
```

## Restoring to v0.1
```bash
cd /opt/bondapp
git fetch origin
git reset --hard v0.1
```
