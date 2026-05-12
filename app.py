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

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# ── CSV config ────────────────────────────────────────────────────────────────
CSV_PATH = os.path.join(os.path.dirname(__file__), 'RoyceData.csv')
CSV_SKIPROWS = 3760      # always start from row 3760
PRODUCT_FILTER = 'IGN2932M75'
LOWER_LIMIT = 8

# Column indices (0-based) after skiprows
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
    mapping = {'B21': 'B21', 'B24': 'B24', 'B25': 'B25', 'B27': 'B27'}
    return mapping.get(m)


def normalize_bond_type(b):
    b = str(b).strip().upper()
    b_clean = re.sub(r'[\s\-#_]', '', b)
    if re.search(r'3.*(SHORT|SCHORT|CHORT|SCHOT|SHOT)', b) or b_clean in ['T3SHORT', 'TYPE3SHORT', 'TYYPE3SHORT', 'T3CHORT']:
        return 'TYPE 3 SHORT'
    if re.search(r'3.*(LONG)', b) or b_clean in ['T3LONG', 'TYPE3LONG']:
        return 'TYPE 3 LONG'
    if re.search(r'TYPE[-\s#]?3$', b) or b_clean in ['TYPE3']:
        return None
    if re.search(r'TYPE[-\s#]?1$', b) or b_clean in ['TYPE1', 'TYPEI', 'TYPEI']:
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

    # Keep only rows where col 0 is numeric (actual data rows)
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
        df.groupby(['Machine', 'BondType', 'Date', 'DateSort'])['Grade']
        .mean()
        .round(2)
        .reset_index()
    )
    grouped = grouped.sort_values('DateSort')
    return grouped


def build_charts(machine, data):
    charts = []
    for bond_type in BOND_TYPES:
        subset = data[(data['Machine'] == machine) & (data['BondType'] == bond_type)]
        fig = go.Figure()

        if not subset.empty:
            fig.add_trace(go.Scatter(
                x=subset['Date'],
                y=subset['Grade'],
                mode='lines+markers+text',
                text=subset['Grade'].astype(str),
                textposition='top center',
                textfont=dict(size=11, color='#1a73e8'),
                line=dict(color='#1a73e8', width=2),
                marker=dict(size=7, color='#1a73e8'),
                name='Grade Code',
                hovertemplate='<b>%{x}</b><br>Grade Code: %{y}<extra></extra>'
            ))
            fig.add_hline(
                y=LOWER_LIMIT,
                line_dash='dash',
                line_color='red',
                line_width=2,
                annotation_text=f'  LCL={LOWER_LIMIT}',
                annotation_position='left',
                annotation_font_color='red'
            )

        fig.update_layout(
            title=dict(text=f'BOND DATA CHART :: {bond_type}',
                       font=dict(size=13, color='#333'), x=0.5, xanchor='center'),
            xaxis=dict(title='', tickangle=-30, tickfont=dict(size=10),
                       showgrid=True, gridcolor='#eee'),
            yaxis=dict(title='Grade Code', tickfont=dict(size=10),
                       showgrid=True, gridcolor='#eee', rangemode='tozero'),
            plot_bgcolor='white', paper_bgcolor='white',
            margin=dict(l=50, r=30, t=50, b=60),
            height=320, showlegend=False,
            font=dict(family='IBM Plex Sans, sans-serif')
        )
        charts.append(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))
    return charts


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('machine', machine_id='B21'))


@app.route('/machine/<machine_id>')
def machine(machine_id):
    machine_id = machine_id.upper()
    if machine_id not in MACHINES:
        return redirect(url_for('machine', machine_id='B21'))
    try:
        data = load_data()
        charts = build_charts(machine_id, data)
    except Exception as e:
        charts = []
        print(f'Error loading data: {e}')
    return render_template(
        'machine.html',
        machine_id=machine_id,
        machines=MACHINES,
        bond_types=BOND_TYPES,
        charts=charts,
        product=PRODUCT_FILTER,
        user=None
    )


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
