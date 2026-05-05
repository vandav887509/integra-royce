# IGN2932M75 — Bond Pull QC Dashboard

Static front-end for the Integra bond-pull control chart dashboard.

## File structure

```
dashboard/
├── css/
│   └── styles.css          ← all shared styles (one file)
├── js/
│   ├── machine-data.js     ← static machine datasets (replace with CSV next sprint)
│   ├── charts.js           ← Chart.js wrapper / IntegraCharts.buildAll()
│   ├── sidebar.js          ← sidebar toggle
│   └── dashboard.js        ← page controller (URL routing, machine switching, tabs)
├── data/                   ← Excel files go here (not committed to git)
├── index.html              ← ONE file handles ALL machines
└── README.md
```

## URL routing

A single `index.html` serves all machine pages via a URL query parameter:

| URL | Machine shown |
|-----|---------------|
| `index.html` or `index.html?machine=21` | B21 (default) |
| `index.html?machine=24` | B24 |
| `index.html?machine=25` | B25 |
| `index.html?machine=27` | B27 |

- Switching machines updates the URL with `history.pushState` — **no page reload**.
- Browser back/forward buttons work correctly.
- Adding a new machine only requires adding one entry to `machine-data.js` and one sidebar link in `index.html`.

## How it works

1. `index.html` loads — one static HTML shell, no machine-specific markup.
2. `dashboard.js` reads `?machine=XX` from the URL.
3. It calls `renderMachine(key)` which:
   - Updates the page title, breadcrumb, header
   - Sets the active state on sidebar links and machine tabs
   - Calls `IntegraCharts.buildAll(data)` to draw all 4 charts
   - Populates metric cards and the data table
4. Clicking a machine tab or sidebar link calls `history.pushState` and re-renders — no reload.

## Colour scheme

| Area | Colour |
|------|--------|
| Top nav / sidebar / footer | `#161b27` dark navy |
| Main content background | `#f5f6f8` light grey |
| Card surfaces | `#ffffff` white |
| Accent / active | `#00c8a0` teal |
| Chart line | `#1a6eb5` steel blue |
| Spec limit line | `#cc3333` red dashed |

## Adding a new machine

1. Add its entry to `js/machine-data.js`:
   ```js
   '28': {
     label: 'B28 Machine', title: 'B28',
     date: '2024-10-14',
     excel: 'data/BOND PULL DATA IGN2932M75 B28 bonder.xlsx',
     dates: [...], t1: [...], t2: [...], t3s: [...], t3l: [...]
   }
   ```
2. Add a sidebar link in `index.html`:
   ```html
   <a class="sidebar-link" data-machine="28" href="index.html?machine=28">
     B28 Machine Chart <span class="machine-badge">B28</span>
   </a>
   ```
3. Add a machine tab button:
   ```html
   <button class="machine-tab" data-machine="28">B28</button>
   ```

No new HTML files needed — ever.

## Next steps

1. Parse `RoyceData.csv` (Python / Node build step) → generate per-machine JSON.
2. Replace static arrays in `machine-data.js` with the generated data.
3. Add Excel files to the `data/` folder.
