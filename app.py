"""
IGN2932M75 - Bond Pull Data Control Charts
Flask Application
"""

from flask import Flask, render_template, redirect, url_for, request
from werkzeug.middleware.proxy_fix import ProxyFix
import pandas as pd
import plotly.graph_objects as go
import plotly.utils
import json
import re
import os
import datetime

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# ── CSV config ──────────────────────────────────────────────────────────────
CSV_PATH      = os.path.join(os.path.dirname(__file__), 'RoyceData.csv')
CSV_SKIPROWS  = 3760
PRODUCT_FILTER = 'IGN2932M75'
LOWER_LIMIT   = 8

COL_TEST_ID   = 0
COL_DATE      = 3
COL_MACHINE   = 4
COL_PRODUCT   = 5
COL_BOND_TYPE = 7
COL_GRADE     = 17

MACHINES   = ['B21', 'B24', 'B25', 'B27']
BOND_TYPES = ['TYPE 1', 'TYPE 2', 'TYPE 3 SHORT', 'TYPE 3 LONG']


# ── Normalization ─────────────────────────────────────────────────────────────

def normalize_machine(m):
    m = re.sub(r'[\s\-]', '', str(m).strip().upper())
    return {'B21':'B21','B24':'B24','B25':'B25','B27':'B27'}.get(m)


def normalize_bond_type(b):
    b = str(b).strip().upper()
    b_clean = re.sub(r'[\s\-#_]', '', b)
    if re.search(r'3.*(SHORT|SCHORT|CHORT|SCHOT|SHOT)', b) or b_clean in ['T3SHORT','TYPE3SHORT','TYYPE3SHORT','T3CHORT']:
        return 'TYPE 3 SHORT'
    if re.search(r'3.*(LONG)', b) or b_clean in ['T3LONG','TYPE3LONG']:
        return 'TYPE 3 LONG'
    if re.search(r'TYPE[-\s#]?3$', b) or b_clean in ['TYPE3']:
        return None
    if re.search(r'TYPE[-\s#]?1$', b) or b_clean in ['TYPE1','TYPEI']:
        return 'TYPE 1'
    if re.search(r'TYPE[-\s#]?2$', b) or b_clean in ['TYPE2']:
        return 'TYPE 2'
    return None


# ── Data loading ──────────────────────────────────────────────────────────────

def load_data():
    df = pd.read_csv(
        CSV_PATH, sep=',', skiprows=CSV_SKIPROWS, header=None,
        quotechar='"', on_bad_lines='skip', engine='python'
    )
    df = df[pd.to_numeric(df[COL_TEST_ID], errors='coerce').notna()].copy()
    df['Date']     = pd.to_datetime(df[COL_DATE], errors='coerce').dt.strftime('%m.%d.%y')
    df['DateSort'] = pd.to_datetime(df[COL_DATE], errors='coerce').dt.date
    df['Grade']    = pd.to_numeric(df[COL_GRADE], errors='coerce')
    df['Machine']  = df[COL_MACHINE].apply(normalize_machine)
    df['BondType'] = df[COL_BOND_TYPE].apply(normalize_bond_type)
    df['Product']  = df[COL_PRODUCT].astype(str).str.strip().str.upper()
    df = df[
        (df['Product']  == PRODUCT_FILTER) &
        (df['Machine'].notna()) &
        (df['BondType'].notna()) &
        (df['Grade'].notna())
    ]
    grouped = (
        df.groupby(['Machine','BondType','Date','DateSort'])['Grade']
        .mean().round(2).reset_index()
    )
    return grouped.sort_values('DateSort')


def build_charts(machine, data):
    charts = []
    for bond_type in BOND_TYPES:
        subset = data[(data['Machine'] == machine) & (data['BondType'] == bond_type)]
        fig = go.Figure()
        if not subset.empty:
            fig.add_trace(go.Scatter(
                x=subset['Date'], y=subset['Grade'],
                mode='lines+markers+text',
                text=subset['Grade'].astype(str),
                textposition='top center',
                textfont=dict(size=10, color='#60a5fa'),
                line=dict(color='#3b82f6', width=2),
                marker=dict(size=6, color='#3b82f6'),
                name='Grade Code',
                hovertemplate='<b>%{x}</b><br>Grade: %{y}<extra></extra>'
            ))
            fig.add_hline(
                y=LOWER_LIMIT, line_dash='dash', line_color='#ef4444', line_width=1.5,
                annotation_text=f'  LCL={LOWER_LIMIT}',
                annotation_position='left', annotation_font_color='#ef4444'
            )
        fig.update_layout(
            title=dict(text=f'BOND DATA CHART :: {bond_type}',
                       font=dict(size=12, color='#e2e8f0'), x=0.5, xanchor='center'),
            xaxis=dict(title='', tickangle=-30, tickfont=dict(size=9),
                       showgrid=True, gridcolor='#2a2f3e'),
            yaxis=dict(title='Grade Code', tickfont=dict(size=9),
                       showgrid=True, gridcolor='#2a2f3e', rangemode='tozero'),
            plot_bgcolor='#13171f', paper_bgcolor='transparent',
            margin=dict(l=45, r=30, t=45, b=55),
            height=280, showlegend=False,
            font=dict(family='IBM Plex Sans, sans-serif', color='#94a3b8')
        )
        charts.append(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))
    return charts


def build_kpi(machine, data):
    kpi = {}
    for bt in BOND_TYPES:
        subset = data[(data['Machine'] == machine) & (data['BondType'] == bt)].sort_values('DateSort')
        if len(subset) >= 2:
            latest = subset.iloc[-1]['Grade']
            prev   = subset.iloc[-2]['Grade']
            pct    = round((latest - prev) / prev * 100, 1) if prev else None
        elif len(subset) == 1:
            latest = subset.iloc[-1]['Grade']
            prev   = '—'
            pct    = None
        else:
            latest = '—'
            prev   = '—'
            pct    = None
        kpi[bt] = {'latest': latest, 'prev': prev, 'pct': pct}
    return kpi


def build_table(machine, data):
    subset = data[data['Machine'] == machine]
    dates  = sorted(subset['DateSort'].unique())
    rows   = []
    for d in dates:
        day = subset[subset['DateSort'] == d]
        row = {'date': day.iloc[0]['Date']}
        for bt in BOND_TYPES:
            match = day[day['BondType'] == bt]
            row[bt] = round(float(match.iloc[0]['Grade']), 2) if not match.empty else None
        rows.append(row)
    return rows


# ── Routes ────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('machine', machine_id='B21'))


@app.route('/machine/<machine_id>')
def machine(machine_id):
    machine_id = machine_id.upper()
    if machine_id not in MACHINES:
        return redirect(url_for('machine', machine_id='B21'))
    try:
        data         = load_data()
        charts       = build_charts(machine_id, data)
        kpi          = build_kpi(machine_id, data)
        table_data   = build_table(machine_id, data)
        last_updated = datetime.date.today().strftime('%Y-%m-%d')
    except Exception as e:
        print(f'Error loading data: {e}')
        charts, kpi, table_data = [], {bt: {'latest':'—','prev':'—','pct':None} for bt in BOND_TYPES}, []
        last_updated = '—'
    return render_template(
        'machine.html',
        machine_id=machine_id,
        machines=MACHINES,
        bond_types=BOND_TYPES,
        charts=charts,
        kpi=kpi,
        table_data=table_data,
        last_updated=last_updated,
        product=PRODUCT_FILTER,
        user=None
    )


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
