"""
IGN2932M75 - Bond Pull Data Control Charts
Flask Application
"""

from flask import Flask, render_template, redirect, url_for, session, request, jsonify
import pandas as pd
import plotly.graph_objects as go
import plotly.utils
import json
import re
import os

app = Flask(__name__)
app.secret_key = 'integra-bond-secret-2024'  # Change in production

# ── Auth credentials (change in production) ───────────────────────────────────
USERS = {
    'admin': 'integra2024',
    'royce': 'bonddata'
}

# ── CSV config ────────────────────────────────────────────────────────────────
CSV_PATH = os.path.join(os.path.dirname(__file__), 'RoyceData.csv')
CSV_SKIPROWS = 3800
PRODUCT_FILTER = 'IGN2932M75'
LOWER_LIMIT = 8  # Red dashed line value on charts

COL_NAMES = [
    'Test ID', 'Test Number', 'Test Number In Sample', 'Date/Time (Local)',
    'User Field 1', 'User Field 2', 'User Field 3', 'User Field 4',
    'User Field 5', 'User Field 6', 'User Field 7', 'User Field 8',
    'User Field 9', 'User Field 10', 'User Field 11', 'User Field 12',
    'Grade Code', 'Peak Force (g/kg)', 'Raw Peak Force (g/kg)',
    'Displacement At Peak Force', 'Displacement At Spec Force', 'Module Serial'
]

MACHINES = ['B21', 'B24', 'B25', 'B27']
BOND_TYPES = ['TYPE 1', 'TYPE 2', 'TYPE 3 SHORT', 'TYPE 3 LONG']


# ── Normalization ─────────────────────────────────────────────────────────────

def normalize_machine(m):
    m = re.sub(r'[\s\-]', '', str(m).strip().upper())
    mapping = {'B21': 'B21', 'B24': 'B24', 'B25': 'B25', 'B27': 'B27'}
    return mapping.get(m)


def normalize_bond_type(b):
    b = str(b).strip().upper()
    b_clean = re.sub(r'[\s\-#_]', '', b)
    # TYPE 3 SHORT variants
    if re.search(r'3.*(SHORT|SCHORT|CHORT|SCHOT|SHOT)', b) or b_clean in ['T3SHORT', 'TYPE3SHORT', 'TYYPE3SHORT']:
        return 'TYPE 3 SHORT'
    # TYPE 3 LONG variants
    if re.search(r'3.*(LONG)', b) or b_clean in ['T3LONG', 'TYPE3LONG']:
        return 'TYPE 3 LONG'
    # TYPE 3 generic (without SHORT/LONG qualifier — skip)
    if re.search(r'TYPE[-\s#]?3$', b) or b_clean in ['TYPE3']:
        return None
    # TYPE 1 variants
    if re.search(r'TYPE[-\s#]?1$', b) or b_clean in ['TYPE1', 'TYPEI']:
        return 'TYPE 1'
    # TYPE 2 variants
    if re.search(r'TYPE[-\s#]?2$', b) or b_clean in ['TYPE2']:
        return 'TYPE 2'
    return None


# ── Data loading ──────────────────────────────────────────────────────────────

def load_data():
    df = pd.read_csv(
        CSV_PATH, sep=',', skiprows=CSV_SKIPROWS, header=None,
        names=COL_NAMES, quotechar='"', on_bad_lines='skip'
    )
    # Keep only numeric Test IDs
    df = df[pd.to_numeric(df['Test ID'], errors='coerce').notna()]

    # Parse date — date only
    df['Date'] = pd.to_datetime(df['Date/Time (Local)'], errors='coerce').dt.strftime('%m.%d.%y')
    df['DateSort'] = pd.to_datetime(df['Date/Time (Local)'], errors='coerce').dt.date

    # Numeric grade code
    df['Grade Code'] = pd.to_numeric(df['Grade Code'], errors='coerce')

    # Normalize machine and bond type
    df['Machine'] = df['User Field 1'].apply(normalize_machine)
    df['Bond Type'] = df['User Field 4'].apply(normalize_bond_type)
    df['Product'] = df['User Field 2'].str.strip().str.upper()

    # Filter: product, valid machine, valid bond type
    df = df[
        (df['Product'] == PRODUCT_FILTER) &
        (df['Machine'].notna()) &
        (df['Bond Type'].notna()) &
        (df['Grade Code'].notna())
    ]

    # Group by Machine, Bond Type, Date → mean Grade Code
    grouped = (
        df.groupby(['Machine', 'Bond Type', 'Date', 'DateSort'])['Grade Code']
        .mean()
        .round(2)
        .reset_index()
    )
    grouped = grouped.sort_values('DateSort')
    return grouped


def build_charts(machine, data):
    """Build 4 Plotly charts for a given machine. Returns list of JSON strings."""
    charts = []
    for bond_type in BOND_TYPES:
        subset = data[(data['Machine'] == machine) & (data['Bond Type'] == bond_type)]

        fig = go.Figure()

        if not subset.empty:
            fig.add_trace(go.Scatter(
                x=subset['Date'],
                y=subset['Grade Code'],
                mode='lines+markers+text',
                text=subset['Grade Code'].astype(str),
                textposition='top center',
                textfont=dict(size=11, color='#1a73e8'),
                line=dict(color='#1a73e8', width=2),
                marker=dict(size=7, color='#1a73e8'),
                name='Grade Code',
                hovertemplate='<b>%{x}</b><br>Grade Code: %{y}<extra></extra>'
            ))

            # Red dashed lower limit line
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
            title=dict(
                text=f'BOND DATA CHART :: {bond_type}',
                font=dict(size=13, color='#333'),
                x=0.5,
                xanchor='center'
            ),
            xaxis=dict(
                title='',
                tickangle=-30,
                tickfont=dict(size=10),
                showgrid=True,
                gridcolor='#eee'
            ),
            yaxis=dict(
                title='Grade Code',
                tickfont=dict(size=10),
                showgrid=True,
                gridcolor='#eee',
                rangemode='tozero'
            ),
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=50, r=30, t=50, b=60),
            height=320,
            showlegend=False,
            font=dict(family='IBM Plex Sans, sans-serif')
        )

        charts.append(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))
    return charts


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if USERS.get(username) == password:
            session['user'] = username
            return redirect(url_for('machine', machine_id='B21'))
        error = 'Invalid username or password.'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ── Main routes ───────────────────────────────────────────────────────────────

@app.route('/')
@login_required
def index():
    return redirect(url_for('machine', machine_id='B21'))


@app.route('/machine/<machine_id>')
@login_required
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
        user=session.get('user')
    )


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
