# IGN2932M75 — Bond Pull QC Dashboard

Static front-end for the Integra bond-pull control chart dashboard.

## File structure

```
dashboard/
├── css/
│   └── styles.css          ← all shared styles (one file, all pages)
├── js/
│   ├── machine-data.js     ← static machine datasets (replace with CSV in next sprint)
│   ├── charts.js           ← Chart.js wrapper / control chart builder
│   ├── sidebar.js          ← sidebar toggle + active-link detection
│   └── dashboard.js        ← page controller (machine switching, tabs, metrics)
├── data/                   ← Excel files go here (not committed)
├── index.html              ← B21 Machine page
├── index24.html            ← B24 Machine page
├── index25.html            ← B25 Machine page
├── index27.html            ← B27 Machine page
└── README.md
```

## How it works

- Each HTML page sets `<body data-machine="XX">` to declare which machine it represents.
- `dashboard.js` reads that attribute on load and calls `switchMachine(key)` automatically.
- All four pages share **one CSS file** and **four JS files** — no duplication.
- The machine-tab quick-selector on each page lets users jump between machines without a page reload.

## Colour scheme

| Area | Colour |
|------|--------|
| Top nav / sidebar / footer | `#161b27` dark navy |
| Main content background | `#f5f6f8` light grey |
| Card surfaces | `#ffffff` white |
| Accent / active | `#00c8a0` teal |
| Chart line | `#1a6eb5` steel blue |
| Spec limit line | `#cc3333` red dashed |

## Next steps

1. Parse `RoyceData.csv` in a build step (Python / Node) to generate per-machine JSON.
2. Replace the static arrays in `machine-data.js` with the generated JSON.
3. Add a `data/` folder with Excel files and wire up the download links.
