# Scripts

## process_csv.py

Converts `RoyceData.csv` into `dashboard/data/machine-data.json` which the dashboard reads via `fetch()`.

### Install dependency

```bash
pip install pandas --break-system-packages
```

### Run manually

```bash
python3 /var/www/integra-royce/scripts/process_csv.py \
    --csv /home/integra/RoyceData.csv \
    --out /var/www/integra-royce/dashboard/data/machine-data.json
```

### Output

Produces one JSON object per machine:

```json
{
  "21": {
    "label": "B21 Machine",
    "title": "B21",
    "date": "2024-10-04",
    "specLimit": 8,
    "excel": "data/BOND PULL DATA IGN2932M75 B21 bonder.xlsx",
    "dates": ["2020-01-10", "2020-01-13", ...],
    "t1":  [35.5, 31.3, ...],
    "t2":  [24.3, 28.3, ...],
    "t3s": [31.5, 26.6, ...],
    "t3l": [26.1, 24.5, ...]
  },
  "24": { ... },
  "25": { ... },
  "27": { ... }
}
```

### Auto-update with cron

Run every day at 06:00:

```bash
crontab -e
```

Add:

```
0 6 * * * python3 /var/www/integra-royce/scripts/process_csv.py --csv /home/integra/RoyceData.csv --out /var/www/integra-royce/dashboard/data/machine-data.json
```
