"""
scripts/build_dashboard.py
==========================
Builds a self-contained HTML dashboard from all analytics query results.
No server needed — just open the HTML file in a browser.
"""

import os
import sys
import json
import pandas as pd

ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANA_DIR = os.path.join(ROOT, "output", "analytics")
WH_DIR  = os.path.join(ROOT, "output", "warehouse")
OUT_DIR = os.path.join(ROOT, "output")

sys.path.insert(0, ROOT)


def load_csv(name):
    path = os.path.join(ANA_DIR, name)
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()


def df_to_json(df, max_rows=200):
    df2 = df.head(max_rows).copy()
    for col in df2.select_dtypes(include="float").columns:
        df2[col] = df2[col].round(2)
    return df2.to_json(orient="records")


def load_warehouse_stats():
    stats = {}
    for fname, label in [
        ("dim_customer.csv",    "Total Customers"),
        ("dim_policy.csv",      "Total Policies"),
        ("dim_address.csv",     "Addresses"),
        ("fact_transactions.csv","Transactions"),
    ]:
        path = os.path.join(WH_DIR, fname)
        if os.path.exists(path):
            stats[label] = len(pd.read_csv(path))
        else:
            stats[label] = 0
    return stats


def load_region_breakdown():
    path = os.path.join(WH_DIR, "dim_customer.csv")
    if not os.path.exists(path):
        return {}
    df = pd.read_csv(path)
    counts = df["Region"].value_counts().to_dict()
    return counts


def load_policy_type_breakdown():
    path = os.path.join(WH_DIR, "dim_policy.csv")
    if not os.path.exists(path):
        return {}
    df = pd.read_csv(path)
    counts = df["Policy_Type"].value_counts().to_dict()
    return counts


def load_term_breakdown():
    path = os.path.join(WH_DIR, "dim_policy.csv")
    if not os.path.exists(path):
        return {}
    df = pd.read_csv(path)
    counts = df["Policy_Term"].value_counts().to_dict()
    return counts


# Load all data
qb = load_csv("query_b_policy_changes.csv")
qc = load_csv("query_c_total_policy_all.csv")
qd = load_csv("query_d_auto_policy_amount.csv")
qe = load_csv("query_e_east_west_quarterly_2012.csv")
qf = load_csv("query_f_marital_changes.csv")
qg = load_csv("query_g_all_regions_full.csv")
stats      = load_warehouse_stats()
regions    = load_region_breakdown()
pol_types  = load_policy_type_breakdown()
pol_terms  = load_term_breakdown()

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ABC Insurance — Data Warehouse Dashboard</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}}
  header{{background:linear-gradient(135deg,#1e3a5f,#0f2744);padding:28px 40px;border-bottom:1px solid #1e40af33}}
  header h1{{font-size:1.7rem;font-weight:700;color:#fff;letter-spacing:.3px}}
  header p{{color:#94a3b8;font-size:.9rem;margin-top:4px}}
  .badge{{display:inline-block;background:#1e40af22;border:1px solid #3b82f644;color:#60a5fa;
          font-size:.72rem;padding:2px 8px;border-radius:20px;margin-left:10px;vertical-align:middle}}
  nav{{background:#0f172a;border-bottom:1px solid #1e293b;display:flex;gap:0;overflow-x:auto;padding:0 32px}}
  nav button{{background:none;border:none;color:#94a3b8;padding:14px 20px;cursor:pointer;
              font-size:.87rem;border-bottom:2px solid transparent;white-space:nowrap;transition:all .2s}}
  nav button:hover{{color:#e2e8f0}}
  nav button.active{{color:#60a5fa;border-bottom-color:#3b82f6}}
  .section{{display:none;padding:32px 40px}}
  .section.active{{display:block}}
  .kpi-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:32px}}
  .kpi{{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:20px 24px}}
  .kpi .val{{font-size:2rem;font-weight:700;color:#60a5fa;line-height:1}}
  .kpi .lbl{{font-size:.82rem;color:#64748b;margin-top:6px}}
  .charts-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px;margin-bottom:32px}}
  .card{{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:24px}}
  .card h3{{font-size:.92rem;font-weight:600;color:#cbd5e1;margin-bottom:16px}}
  .bar-chart{{display:flex;flex-direction:column;gap:8px}}
  .bar-row{{display:flex;align-items:center;gap:10px;font-size:.82rem}}
  .bar-label{{width:80px;color:#94a3b8;text-align:right;flex-shrink:0}}
  .bar-track{{flex:1;background:#0f172a;border-radius:4px;height:22px;overflow:hidden}}
  .bar-fill{{height:100%;border-radius:4px;display:flex;align-items:center;
             padding-left:8px;font-size:.78rem;font-weight:600;color:#fff;transition:width .6s ease}}
  .bar-count{{width:50px;color:#64748b;font-size:.78rem}}
  .query-header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:10px}}
  .query-header h2{{font-size:1.05rem;font-weight:600;color:#e2e8f0}}
  .query-desc{{font-size:.84rem;color:#64748b;margin-bottom:20px;line-height:1.5}}
  .search-box{{background:#0f172a;border:1px solid #334155;border-radius:8px;
               padding:8px 14px;color:#e2e8f0;font-size:.84rem;width:240px;outline:none}}
  .search-box:focus{{border-color:#3b82f6}}
  .table-wrap{{overflow-x:auto;border-radius:10px;border:1px solid #1e293b}}
  table{{border-collapse:collapse;width:100%;font-size:.82rem}}
  th{{background:#0f172a;color:#64748b;font-weight:500;padding:10px 14px;text-align:left;
      white-space:nowrap;border-bottom:1px solid #1e293b;font-size:.78rem;text-transform:uppercase;letter-spacing:.5px}}
  td{{padding:9px 14px;border-bottom:1px solid #1e293b;color:#cbd5e1;white-space:nowrap}}
  tr:hover td{{background:#1e293b99}}
  .tag{{display:inline-block;padding:2px 8px;border-radius:20px;font-size:.72rem;font-weight:600}}
  .tag-auto{{background:#1e40af22;color:#60a5fa;border:1px solid #3b82f644}}
  .tag-home{{background:#14532d22;color:#4ade80;border:1px solid #22c55e44}}
  .tag-health{{background:#78350f22;color:#fbbf24;border:1px solid #f59e0b44}}
  .tag-term{{background:#4c1d9522;color:#a78bfa;border:1px solid #7c3aed44}}
  .tag-whole{{background:#881337AA;color:#fb7185;border:1px solid #f4365844}}
  .tag-east{{background:#1e3a5f44;color:#93c5fd}}
  .tag-west{{background:#14532d44;color:#86efac}}
  .tag-north{{background:#78350f44;color:#fcd34d}}
  .tag-south{{background:#4c1d9544;color:#c4b5fd}}
  .pagination{{display:flex;gap:6px;margin-top:16px;justify-content:flex-end;flex-wrap:wrap}}
  .pagination button{{background:#1e293b;border:1px solid #334155;color:#94a3b8;
                      padding:5px 12px;border-radius:6px;cursor:pointer;font-size:.8rem}}
  .pagination button.active{{background:#1e40af;border-color:#3b82f6;color:#fff}}
  .pagination button:hover:not(.active){{background:#334155}}
  .summary-pill{{display:inline-flex;align-items:center;gap:6px;background:#1e293b;
                border:1px solid #334155;border-radius:20px;padding:5px 14px;font-size:.8rem;color:#94a3b8}}
  .summary-pill span{{color:#60a5fa;font-weight:600}}
  footer{{text-align:center;padding:24px;color:#334155;font-size:.78rem;border-top:1px solid #1e293b}}
</style>
</head>
<body>
<header>
  <h1>ABC Insurance <span class="badge">Data Warehouse</span></h1>
  <p>End-to-end Data Engineering Pipeline — day0 → day1 → day2 &nbsp;|&nbsp; 4 Regions &nbsp;|&nbsp; 6 Analytics Queries</p>
</header>

<nav>
  <button class="active" onclick="show('overview',this)">Overview</button>
  <button onclick="show('qb',this)">b) Policy Changes</button>
  <button onclick="show('qc',this)">c) Total Policy Amt</button>
  <button onclick="show('qd',this)">d) Auto Policies</button>
  <button onclick="show('qe',this)">e) East+West 2012</button>
  <button onclick="show('qf',this)">f) Marital SCD</button>
  <button onclick="show('qg',this)">g) Full Region View</button>
</nav>

<!-- OVERVIEW -->
<div id="overview" class="section active">
  <div class="kpi-row">
    {"".join(f'<div class="kpi"><div class="val">{v:,}</div><div class="lbl">{k}</div></div>' for k,v in stats.items())}
  </div>

  <div class="charts-row">
    <div class="card">
      <h3>Customers by Region</h3>
      <div class="bar-chart" id="region-chart"></div>
    </div>
    <div class="card">
      <h3>Policies by Type</h3>
      <div class="bar-chart" id="type-chart"></div>
    </div>
    <div class="card">
      <h3>Policies by Term</h3>
      <div class="bar-chart" id="term-chart"></div>
    </div>
  </div>

  <div class="card">
    <h3>Pipeline Summary</h3>
    <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:8px">
      <div class="summary-pill">Source Files <span>12</span></div>
      <div class="summary-pill">Days Processed <span>3</span></div>
      <div class="summary-pill">Regions <span>4</span></div>
      <div class="summary-pill">Late Fees Detected <span>40</span></div>
      <div class="summary-pill">SCD Customers <span>1</span></div>
      <div class="summary-pill">Policy Changes <span>{len(qb)}</span></div>
      <div class="summary-pill">Marital Changes <span>{len(qf)}</span></div>
    </div>
  </div>
</div>

<!-- QUERY B -->
<div id="qb" class="section">
  <div class="query-header">
    <h2>b) Customers who changed their Policy Type</h2>
    <input class="search-box" placeholder="Search..." oninput="filterTable('tb','qb-count',this.value)">
  </div>
  <p class="query-desc">Shows customers whose policy type changed between day0 and day1, along with current and previous policy type details.</p>
  <p class="summary-pill" style="margin-bottom:16px">Total records <span id="qb-count">{len(qb)}</span></p>
  <div class="table-wrap"><table id="tb"><thead><tr>
    <th>Customer ID</th><th>Customer Name</th><th>Policy ID</th>
    <th>Current Type</th><th>Current Policy</th><th>Previous Type</th><th>Previous Policy</th>
  </tr></thead><tbody id="tb-body"></tbody></table></div>
  <div class="pagination" id="tb-pages"></div>
</div>

<!-- QUERY C -->
<div id="qc" class="section">
  <div class="query-header">
    <h2>c) Total Policy Amount — All Customers, All Regions</h2>
    <input class="search-box" placeholder="Search..." oninput="filterTable('tc','qc-count',this.value)">
  </div>
  <p class="query-desc">Aggregate total policy amount per customer across all regions combined.</p>
  <p class="summary-pill" style="margin-bottom:16px">Total customers <span id="qc-count">{len(qc)}</span></p>
  <div class="table-wrap"><table id="tc"><thead><tr>
    <th>Customer ID</th><th>Customer Name</th><th>Region</th><th>Total Policy Amount</th>
  </tr></thead><tbody id="tc-body"></tbody></table></div>
  <div class="pagination" id="tc-pages"></div>
</div>

<!-- QUERY D -->
<div id="qd" class="section">
  <div class="query-header">
    <h2>d) Total Policy Amount — Auto Policy Customers</h2>
    <input class="search-box" placeholder="Search..." oninput="filterTable('td','qd-count',this.value)">
  </div>
  <p class="query-desc">Total policy amount aggregated for customers who hold Auto insurance policies.</p>
  <p class="summary-pill" style="margin-bottom:16px">Auto policy customers <span id="qd-count">{len(qd)}</span></p>
  <div class="table-wrap"><table id="td"><thead><tr>
    <th>Customer ID</th><th>Customer Name</th><th>Region</th><th>Policy Type</th><th>Total Policy Amount</th>
  </tr></thead><tbody id="td-body"></tbody></table></div>
  <div class="pagination" id="td-pages"></div>
</div>

<!-- QUERY E -->
<div id="qe" class="section">
  <div class="query-header">
    <h2>e) East + West Customers — Quarterly Term, Year 2012</h2>
    <input class="search-box" placeholder="Search..." oninput="filterTable('te','qe-count',this.value)">
  </div>
  <p class="query-desc">Total policy amount for East and West region customers with Quarterly payment term and policy start date in 2012.</p>
  <p class="summary-pill" style="margin-bottom:16px">Matching records <span id="qe-count">{len(qe)}</span></p>
  <div class="table-wrap"><table id="te"><thead><tr>
    <th>Customer ID</th><th>Customer Name</th><th>Region</th><th>Policy Term</th><th>Policy Start</th><th>Total Policy Amount</th>
  </tr></thead><tbody id="te-body"></tbody></table></div>
  <div class="pagination" id="te-pages"></div>
</div>

<!-- QUERY F -->
<div id="qf" class="section">
  <div class="query-header">
    <h2>f) Customers whose Marital Status Changed (SCD Type 2)</h2>
  </div>
  <p class="query-desc">Tracks customers where Marital_Status changed over time. The Effective_Start_Dt and Effective_End_Dt columns show the validity period of each status record (Slowly Changing Dimension Type 2).</p>
  <div class="table-wrap"><table id="tf"><thead><tr>
    <th>Customer ID</th><th>Title</th><th>First Name</th><th>Last Name</th>
    <th>Segment</th><th>Marital Status</th><th>Start Date</th><th>End Date</th>
  </tr></thead><tbody id="tf-body"></tbody></table></div>
</div>

<!-- QUERY G -->
<div id="qg" class="section">
  <div class="query-header">
    <h2>g) All Regions — Customer + Policy + Address Full View</h2>
    <input class="search-box" placeholder="Search by name, region..." oninput="filterTable('tg','qg-count',this.value)">
  </div>
  <p class="query-desc">Comprehensive view joining all regions' customer data with their policy details, policy type information, address data, and transaction amounts.</p>
  <p class="summary-pill" style="margin-bottom:16px">Total rows <span id="qg-count">{len(qg)}</span></p>
  <div class="table-wrap"><table id="tg"><thead><tr>
    <th>Customer ID</th><th>Customer Name</th><th>Segment</th><th>Marital</th>
    <th>Region</th><th>Policy Type</th><th>Policy Term</th>
    <th>Policy Start</th><th>Premium Amt</th><th>Total Amt</th>
    <th>City</th><th>State</th>
  </tr></thead><tbody id="tg-body"></tbody></table></div>
  <div class="pagination" id="tg-pages"></div>
</div>

<footer>ABC Insurance · Data Engineering Pipeline · day0 → day1 → day2 · 4 Regions · MySQL DWH</footer>

<script>
const DATA = {{
  qb: {df_to_json(qb)},
  qc: {df_to_json(qc)},
  qd: {df_to_json(qd)},
  qe: {df_to_json(qe)},
  qf: {df_to_json(qf)},
  qg: {df_to_json(qg, 500)}
}};

const REGIONS   = {json.dumps(regions)};
const POL_TYPES = {json.dumps(pol_types)};
const POL_TERMS = {json.dumps(pol_terms)};

const PAGE_SIZE = 20;
const tableState = {{}};

function fmt(v) {{
  if (v === null || v === undefined || v === '') return '—';
  if (typeof v === 'number') return v.toLocaleString();
  return v;
}}

function regionTag(r) {{
  if (!r) return '';
  const cl = {{'EAST':'east','WEST':'west','NORTH':'north','SOUTH':'south'}}[r] || '';
  return `<span class="tag tag-${{cl}}">${{r}}</span>`;
}}

function typeTag(t) {{
  if (!t) return '';
  const cl = {{'Auto':'auto','WholeLife':'whole','Health':'health','Term':'term','Home':'home'}}[t] || '';
  return `<span class="tag tag-${{cl}}">${{t}}</span>`;
}}

function renderRows(tableId, rows, renderers) {{
  const tbody = document.getElementById(tableId + '-body');
  tbody.innerHTML = rows.map(r => '<tr>' + renderers.map(fn => '<td>' + fn(r) + '</td>').join('') + '</tr>').join('');
}}

function paginate(tableId, data, renderers, countId) {{
  const state = tableState[tableId] = tableState[tableId] || {{page:0, filtered: data}};
  const pages  = Math.ceil(state.filtered.length / PAGE_SIZE);
  const slice  = state.filtered.slice(state.page * PAGE_SIZE, (state.page + 1) * PAGE_SIZE);
  renderRows(tableId, slice, renderers);
  if (countId) document.getElementById(countId).textContent = state.filtered.length;

  const container = document.getElementById(tableId + '-pages');
  if (!container) return;
  container.innerHTML = '';
  for (let i = 0; i < pages; i++) {{
    const b = document.createElement('button');
    b.textContent = i + 1;
    if (i === state.page) b.className = 'active';
    b.onclick = () => {{ tableState[tableId].page = i; paginate(tableId, data, renderers, countId); }};
    container.appendChild(b);
  }}
}}

function filterTable(tableId, countId, q) {{
  const query = q.toLowerCase();
  const orig  = DATA[tableId.replace('t','q')];
  const filtered = orig.filter(r => Object.values(r).some(v => String(v).toLowerCase().includes(query)));
  tableState[tableId] = {{page: 0, filtered}};
  const spec = TABLE_SPECS[tableId];
  paginate(tableId, filtered, spec.renderers, countId);
}}

const TABLE_SPECS = {{
  tb: {{ renderers: [
    r => fmt(r.Customer_ID), r => fmt(r.Customer_Name),
    r => fmt(r.Policy_Id),
    r => typeTag(r.Current_Policy_Type),
    r => fmt(r.Current_Policy_Name || r.Current_Policy_Type_Id),
    r => typeTag(r.Previous_Policy_Type),
    r => fmt(r.Previous_Policy_Type_Id)
  ]}},
  tc: {{ renderers: [
    r => fmt(r.Customer_ID), r => fmt(r.Customer_Name),
    r => regionTag(r.Region), r => '$' + fmt(r.Total_Policy_Amt)
  ]}},
  td: {{ renderers: [
    r => fmt(r.Customer_ID), r => fmt(r.Customer_Name),
    r => regionTag(r.Region), r => typeTag(r.Policy_Type),
    r => '$' + fmt(r.Total_Policy_Amt)
  ]}},
  te: {{ renderers: [
    r => fmt(r.Customer_ID), r => fmt(r.Customer_Name),
    r => regionTag(r.Region), r => fmt(r.Policy_Term),
    r => fmt(r.Policy_Start_Dt), r => '$' + fmt(r.Total_Policy_Amt)
  ]}},
  tf: {{ renderers: [
    r => fmt(r.Customer_ID), r => fmt(r.Customer_Title),
    r => fmt(r.Customer_First_Name), r => fmt(r.Customer_Last_Name),
    r => fmt(r.Customer_Segment), r => fmt(r.Marital_Status),
    r => fmt(r.Start_Dt_Marital_Status), r => fmt(r.End_Dt_Marital_Status)
  ]}},
  tg: {{ renderers: [
    r => fmt(r.Customer_ID), r => fmt(r.Customer_Name),
    r => fmt(r.Customer_Segment), r => fmt(r.Marital_Status),
    r => regionTag(r.Region), r => typeTag(r.Policy_Type),
    r => fmt(r.Policy_Term), r => fmt(r.Policy_Start_Dt),
    r => '$' + fmt(r.Premium_Amt), r => '$' + fmt(r.Total_Policy_Amt),
    r => fmt(r.City), r => fmt(r.State)
  ]}}
}};

function initTable(tableId, dataKey, countId) {{
  tableState[tableId] = {{page: 0, filtered: DATA[dataKey]}};
  paginate(tableId, DATA[dataKey], TABLE_SPECS[tableId].renderers, countId);
}}

// Render SCD table (query f) directly — small table
function renderFStatic() {{
  const tbody = document.getElementById('tf-body');
  tbody.innerHTML = DATA.qf.map(r => `<tr>
    <td>${{fmt(r.Customer_ID)}}</td><td>${{fmt(r.Customer_Title)}}</td>
    <td>${{fmt(r.Customer_First_Name)}}</td><td>${{fmt(r.Customer_Last_Name)}}</td>
    <td>${{fmt(r.Customer_Segment)}}</td>
    <td><span class="tag" style="background:#1e293b;color:#94a3b8">${{fmt(r.Marital_Status)}}</span></td>
    <td>${{fmt(r.Start_Dt_Marital_Status)}}</td><td>${{fmt(r.End_Dt_Marital_Status)}}</td>
  </tr>`).join('');
}}

// Bar chart renderer
function renderBarChart(containerId, data, colors) {{
  const el    = document.getElementById(containerId);
  const max   = Math.max(...Object.values(data));
  const pairs = Object.entries(data).sort((a,b) => b[1]-a[1]);
  el.innerHTML = pairs.map(([k,v], i) => `
    <div class="bar-row">
      <div class="bar-label">${{k}}</div>
      <div class="bar-track">
        <div class="bar-fill" style="width:${{Math.round(v/max*100)}}%;background:${{colors[i % colors.length]}}">${{v}}</div>
      </div>
    </div>`).join('');
}}

function show(id, btn) {{
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
}}

// Init
renderBarChart('region-chart', REGIONS, ['#3b82f6','#22c55e','#f59e0b','#a78bfa']);
renderBarChart('type-chart',   POL_TYPES, ['#60a5fa','#4ade80','#fbbf24','#c084fc','#fb7185']);
renderBarChart('term-chart',   POL_TERMS, ['#38bdf8','#34d399','#fb923c']);
initTable('tb', 'qb', 'qb-count');
initTable('tc', 'qc', 'qc-count');
initTable('td', 'qd', 'qd-count');
initTable('te', 'qe', 'qe-count');
initTable('tg', 'qg', 'qg-count');
renderFStatic();
</script>
</body>
</html>"""

out_path = os.path.join(OUT_DIR, "insurance_dashboard.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(HTML)

print(f"✅ Dashboard saved: {out_path}")
print(f"   Size: {len(HTML):,} bytes")
