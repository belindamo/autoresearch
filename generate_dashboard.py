#!/usr/bin/env python3
"""
Reads research_log.md + session logs and generates index.html dashboard.
Run after each experiment to keep the dashboard up to date.
"""

import re
import os
import json
from datetime import datetime

WORKSPACE = os.path.dirname(os.path.abspath(__file__))
RESEARCH_LOG = os.path.join(WORKSPACE, "research_log.md")
LOGS_DIR = os.path.join(WORKSPACE, "logs")
OUTPUT = os.path.join(WORKSPACE, "index.html")


def parse_session_log(filepath):
    """Parse a single session log and extract experiment data."""
    with open(filepath, "r") as f:
        content = f.read()

    session_num = None
    m = re.search(r"Session\s+(\d+)", content)
    if m:
        session_num = int(m.group(1))

    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(filepath))
    date = date_match.group(1) if date_match else "unknown"

    experiment_desc = ""
    desc_match = re.search(r"\*\*(.+?)\*\*", content)
    if desc_match:
        experiment_desc = desc_match.group(1)

    # Extract results table
    results = {}
    val_bpb_match = re.search(r"val_bpb\s*\|\s*\*?\*?(\d+\.\d+)\*?\*?", content)
    if val_bpb_match:
        results["val_bpb"] = float(val_bpb_match.group(1))

    vram_match = re.search(r"Peak VRAM\s*\|\s*(\d+\.?\d*)\s*GB", content)
    if vram_match:
        results["vram"] = float(vram_match.group(1))

    steps_match = re.search(r"Steps\s*\|\s*(\d+)", content)
    if steps_match:
        results["steps"] = int(steps_match.group(1))

    mfu_match = re.search(r"MFU\s*\|\s*(\d+\.?\d*)%", content)
    if mfu_match:
        results["mfu"] = float(mfu_match.group(1))

    tokens_match = re.search(r"Total tokens\s*\|\s*(\d+\.?\d*)M", content)
    if tokens_match:
        results["tokens_m"] = float(tokens_match.group(1))

    status_match = re.search(r"Status:\s*(KEEP|DISCARD)", content, re.IGNORECASE)
    if status_match:
        results["status"] = status_match.group(1).lower()

    return {
        "session": session_num,
        "date": date,
        "description": experiment_desc,
        "results": results,
    }


def parse_research_log(filepath):
    """Parse research_log.md for session summaries and overall info."""
    with open(filepath, "r") as f:
        content = f.read()

    # Extract intro line
    intro = content.split("\n")[0].strip()

    # Extract best bpb
    best_match = re.search(r"Current best:\s*\*?\*?(\d+\.\d+)\*?\*?", content)
    best_bpb = float(best_match.group(1)) if best_match else None

    # Extract individual experiment results from session 1 table
    experiments = []
    # Session 1 ran multiple experiments — parse from session log table if present
    return {
        "intro": intro,
        "best_bpb": best_bpb,
        "content": content,
    }


def parse_session1_experiments(filepath):
    """Session 1 has a multi-experiment table. Parse it separately."""
    with open(filepath, "r") as f:
        content = f.read()

    experiments = []
    # Find table rows like: | 0 | 1.1186 | 44.0 | keep | baseline ... |
    table_rows = re.findall(
        r"\|\s*(\d+)\s*\|\s*(\d+\.\d+)\s*\|\s*(\d+\.?\d*)\s*\|\s*(\w+)\s*\|\s*(.+?)\s*\|",
        content,
    )
    for row in table_rows:
        num, bpb, vram, status, desc = row
        exp = {
            "num": int(num),
            "session": 1,
            "val_bpb": float(bpb),
            "vram": float(vram),
            "status": status.lower(),
            "description": desc.strip(),
            "steps": None,
        }
        # Estimate steps from description
        if "baseline" in desc.lower():
            exp["steps"] = 350
        elif "depth" in desc.lower() or "10" in desc:
            exp["steps"] = 234
        elif "batch" in desc.lower():
            exp["steps"] = 686
        else:
            exp["steps"] = 350
        experiments.append(exp)
    return experiments


def build_all_experiments():
    """Combine session 1 table + later session logs into a single ordered list."""
    all_exps = []

    # Session 1 has multiple experiments in one log
    s1_path = None
    for f in sorted(os.listdir(LOGS_DIR)):
        if f.endswith(".md"):
            if "session_1" in f:
                s1_path = os.path.join(LOGS_DIR, f)
                break

    if s1_path:
        s1_exps = parse_session1_experiments(s1_path)
        for exp in s1_exps:
            all_exps.append(exp)

    # Sessions 2+ each have one experiment
    log_files = sorted(os.listdir(LOGS_DIR))
    next_num = len(all_exps)
    for f in log_files:
        if not f.endswith(".md"):
            continue
        session_match = re.search(r"session_(\d+)", f)
        if not session_match:
            continue
        session_num = int(session_match.group(1))
        if session_num <= 1:
            continue

        parsed = parse_session_log(os.path.join(LOGS_DIR, f))
        r = parsed["results"]
        if "val_bpb" not in r:
            continue

        all_exps.append({
            "num": next_num,
            "session": session_num,
            "val_bpb": r.get("val_bpb"),
            "vram": r.get("vram", 0),
            "steps": r.get("steps", 0),
            "status": r.get("status", "keep"),
            "description": parsed["description"],
        })
        next_num += 1

    return all_exps


def generate_html(experiments, research_info):
    """Generate the full HTML dashboard."""
    if not experiments:
        return "<html><body><h1>No experiments yet</h1></body></html>"

    baseline_bpb = experiments[0]["val_bpb"] if experiments else 1.1186
    best_bpb = min(e["val_bpb"] for e in experiments)
    best_exp = [e for e in experiments if e["val_bpb"] == best_bpb][0]
    improvement = baseline_bpb - best_bpb
    pct_improvement = (improvement / baseline_bpb) * 100
    num_experiments = len(experiments)
    num_sessions = max(e["session"] for e in experiments)
    today = datetime.now().strftime("%Y-%m-%d")

    # Build table rows
    table_rows = ""
    for e in experiments:
        status_class = "badge-best" if e["val_bpb"] == best_bpb else (
            "badge-discard" if e["status"] == "discard" else "badge-keep"
        )
        status_label = "★ best" if e["val_bpb"] == best_bpb else e["status"]
        if e["num"] == 0 and e["val_bpb"] != best_bpb:
            status_class = "badge-keep"
            status_label = "baseline"

        bpb_style = ' style="color: var(--green); font-weight: 700;"' if e["val_bpb"] == best_bpb else ""
        steps_display = f"~{e['steps']}" if e["num"] <= 1 and e["steps"] == 350 else str(e["steps"] or "—")
        vram_display = f"{e['vram']:.1f} GB" if e["vram"] else "—"

        table_rows += f"""          <tr>
            <td>{e['num']}</td><td>{e['session']}</td><td>{e['description']}</td>
            <td{bpb_style}>{e['val_bpb']:.4f}</td><td>{steps_display}</td><td>{vram_display}</td>
            <td><span class="badge {status_class}">{status_label}</span></td>
          </tr>\n"""

    # Build JS data arrays
    js_labels = json.dumps([f"#{e['num']} S{e['session']}" for e in experiments])
    js_bpb = json.dumps([e["val_bpb"] for e in experiments])
    js_steps = json.dumps([e["steps"] or 0 for e in experiments])
    js_vram = json.dumps([e["vram"] or 0 for e in experiments])
    js_descriptions = json.dumps([e["description"][:30] for e in experiments])

    # Extract current best config from the latest "keep" session log
    config_section = ""
    for f in sorted(os.listdir(LOGS_DIR), reverse=True):
        if f.endswith(".md"):
            path = os.path.join(LOGS_DIR, f)
            with open(path, "r") as fh:
                text = fh.read()
            if "Current best config" in text or "Status: KEEP" in text.upper():
                # Extract config items
                config_items = re.findall(r"[-*]\s+(\w+)\s*[=:]\s*(.+)", text)
                if config_items:
                    config_section = "\n".join(
                        f'        <div class="config-item"><span class="key">{k.strip()}</span><span class="val">{v.strip().rstrip("*")}</span></div>'
                        for k, v in config_items
                        if k not in ("Status",) and "best" not in v.lower()
                    )
                    break

    if not config_section:
        config_section = '<div class="config-item"><span class="key">val_bpb</span><span class="val">' + f"{best_bpb:.4f}" + '</span></div>'

    # Read research_log for next ideas from latest session
    next_ideas_html = ""
    for f in sorted(os.listdir(LOGS_DIR), reverse=True):
        if f.endswith(".md"):
            with open(os.path.join(LOGS_DIR, f), "r") as fh:
                text = fh.read()
            ideas_match = re.search(r"Next (?:ideas|steps)(.*?)(?=\n## |\Z)", text, re.DOTALL | re.IGNORECASE)
            if ideas_match:
                ideas = re.findall(r"[-*]\s+(.+)", ideas_match.group(1))
                if ideas:
                    next_ideas_html = "\n".join(f"          <li>{idea.strip()}</li>" for idea in ideas[:6])
                    break

    # Determine what worked / didn't
    kept = [e for e in experiments if e["status"] == "keep" and e["num"] > 0]
    discarded = [e for e in experiments if e["status"] == "discard"]

    worked_html = "\n".join(
        f'          <li>{e["description"]} → {e["val_bpb"]:.4f}</li>' for e in kept
    )
    failed_html = "\n".join(
        f'          <li>{e["description"]} → {e["val_bpb"]:.4f}</li>' for e in discarded
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Autoresearch Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
  <style>
    :root {{
      --bg: #0d1117;
      --surface: #161b22;
      --border: #30363d;
      --text: #e6edf3;
      --muted: #8b949e;
      --accent: #58a6ff;
      --green: #3fb950;
      --red: #f85149;
      --orange: #d29922;
      --purple: #bc8cff;
    }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; padding: 2rem 1.5rem; }}
    header {{
      border-bottom: 1px solid var(--border);
      padding-bottom: 2rem;
      margin-bottom: 2.5rem;
    }}
    header h1 {{
      font-size: 2rem;
      font-weight: 700;
      margin-bottom: 0.5rem;
      background: linear-gradient(135deg, var(--accent), var(--purple));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}
    header p {{ color: var(--muted); font-size: 1.05rem; max-width: 720px; }}
    .kpi-strip {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem;
      margin-bottom: 2.5rem;
    }}
    .kpi {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.25rem;
    }}
    .kpi-label {{ font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); margin-bottom: 0.25rem; }}
    .kpi-value {{ font-size: 1.8rem; font-weight: 700; }}
    .kpi-sub {{ font-size: 0.8rem; color: var(--muted); margin-top: 0.15rem; }}
    .kpi-value.green {{ color: var(--green); }}
    .charts-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
      margin-bottom: 2.5rem;
    }}
    @media (max-width: 768px) {{ .charts-grid {{ grid-template-columns: 1fr; }} }}
    .chart-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.5rem;
    }}
    .chart-card h3 {{ font-size: 1rem; margin-bottom: 1rem; font-weight: 600; }}
    .table-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.5rem;
      margin-bottom: 2.5rem;
      overflow-x: auto;
    }}
    .table-card h3 {{ font-size: 1rem; margin-bottom: 1rem; font-weight: 600; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
    thead th {{
      text-align: left;
      padding: 0.75rem 1rem;
      border-bottom: 1px solid var(--border);
      color: var(--muted);
      font-weight: 600;
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    tbody td {{ padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); }}
    tbody tr:last-child td {{ border-bottom: none; }}
    tbody tr:hover {{ background: rgba(88,166,255,0.04); }}
    .badge {{
      display: inline-block;
      padding: 0.15rem 0.6rem;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 600;
    }}
    .badge-keep {{ background: rgba(63,185,80,0.15); color: var(--green); }}
    .badge-discard {{ background: rgba(248,81,73,0.15); color: var(--red); }}
    .badge-best {{ background: rgba(188,140,255,0.15); color: var(--purple); }}
    .findings {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
      margin-bottom: 2.5rem;
    }}
    @media (max-width: 768px) {{ .findings {{ grid-template-columns: 1fr; }} }}
    .finding-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.5rem;
    }}
    .finding-card h3 {{ font-size: 1rem; font-weight: 600; margin-bottom: 0.75rem; }}
    .finding-card ul {{ list-style: none; padding: 0; }}
    .finding-card li {{
      padding: 0.4rem 0;
      padding-left: 1.2rem;
      position: relative;
      color: var(--muted);
      font-size: 0.9rem;
    }}
    .finding-card li::before {{
      content: '\\2192';
      position: absolute;
      left: 0;
      color: var(--accent);
    }}
    .config-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.5rem;
      margin-bottom: 2rem;
    }}
    .config-card h3 {{ font-size: 1rem; font-weight: 600; margin-bottom: 1rem; }}
    .config-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 0.75rem;
    }}
    .config-item {{
      display: flex;
      justify-content: space-between;
      padding: 0.5rem 0.75rem;
      background: var(--bg);
      border-radius: 8px;
      font-size: 0.85rem;
    }}
    .config-item .key {{ color: var(--muted); }}
    .config-item .val {{ color: var(--accent); font-weight: 600; font-family: 'SF Mono', 'Fira Code', monospace; }}
    footer {{
      border-top: 1px solid var(--border);
      padding-top: 1.5rem;
      text-align: center;
      color: var(--muted);
      font-size: 0.8rem;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Autoresearch Dashboard</h1>
      <p>Autonomous GPT pretraining research using Karpathy's autoresearch framework. 5-minute training experiments on Modal A100-80GB GPUs, optimizing val_bpb (validation bits per byte).</p>
    </header>

    <div class="kpi-strip">
      <div class="kpi">
        <div class="kpi-label">Best val_bpb</div>
        <div class="kpi-value green">{best_bpb:.4f}</div>
        <div class="kpi-sub">&darr; {pct_improvement:.1f}% from baseline</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Baseline val_bpb</div>
        <div class="kpi-value">{baseline_bpb:.4f}</div>
        <div class="kpi-sub">Unmodified train.py</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Experiments Run</div>
        <div class="kpi-value">{num_experiments}</div>
        <div class="kpi-sub">Across {num_sessions} session{"s" if num_sessions > 1 else ""}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Improvement</div>
        <div class="kpi-value green">&minus;{improvement:.4f}</div>
        <div class="kpi-sub">val_bpb reduction</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">GPU</div>
        <div class="kpi-value" style="font-size:1.4rem;">A100-80GB</div>
        <div class="kpi-sub">Modal cloud</div>
      </div>
    </div>

    <div class="charts-grid">
      <div class="chart-card">
        <h3>val_bpb Over Experiments</h3>
        <canvas id="bpbChart"></canvas>
      </div>
      <div class="chart-card">
        <h3>Optimizer Steps per Experiment</h3>
        <canvas id="stepsChart"></canvas>
      </div>
      <div class="chart-card">
        <h3>Peak VRAM Usage (GB)</h3>
        <canvas id="vramChart"></canvas>
      </div>
      <div class="chart-card">
        <h3>val_bpb vs Steps (Efficiency)</h3>
        <canvas id="scatterChart"></canvas>
      </div>
    </div>

    <div class="table-card">
      <h3>All Experiments</h3>
      <table>
        <thead>
          <tr><th>#</th><th>Session</th><th>Description</th><th>val_bpb</th><th>Steps</th><th>VRAM</th><th>Status</th></tr>
        </thead>
        <tbody>
{table_rows}
        </tbody>
      </table>
    </div>

    <div class="findings">
      <div class="finding-card">
        <h3>What Worked</h3>
        <ul>
{worked_html}
        </ul>
      </div>
      <div class="finding-card">
        <h3>What Didn't Work</h3>
        <ul>
{failed_html if failed_html else '          <li>Nothing discarded yet</li>'}
        </ul>
      </div>
      <div class="finding-card" style="grid-column: span 2;">
        <h3>Next Experiments</h3>
        <ul>
{next_ideas_html if next_ideas_html else '          <li>No ideas logged yet</li>'}
        </ul>
      </div>
    </div>

    <div class="config-card">
      <h3>Current Best Configuration</h3>
      <div class="config-grid">
{config_section}
      </div>
    </div>

    <footer>
      <p>Autoresearch Dashboard &middot; Auto-generated {today} &middot; Built on Sundial</p>
    </footer>
  </div>

  <script>
    Chart.defaults.color = '#8b949e';
    Chart.defaults.borderColor = '#30363d';
    Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif";

    const labels = {js_labels};
    const bpbData = {js_bpb};
    const stepsData = {js_steps};
    const vramData = {js_vram};
    const descriptions = {js_descriptions};
    const bestBpb = Math.min(...bpbData);

    function bpbColors(data) {{
      return data.map(v => v === bestBpb ? '#3fb950' : (v > bpbData[0] ? '#f85149' : '#58a6ff'));
    }}

    // val_bpb line
    new Chart(document.getElementById('bpbChart'), {{
      type: 'line',
      data: {{
        labels,
        datasets: [{{
          label: 'val_bpb',
          data: bpbData,
          borderColor: '#58a6ff',
          backgroundColor: 'rgba(88,166,255,0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 6,
          pointBackgroundColor: bpbColors(bpbData),
          pointBorderColor: bpbColors(bpbData),
          borderWidth: 2,
        }}]
      }},
      options: {{
        responsive: true,
        plugins: {{ legend: {{ display: false }}, tooltip: {{ callbacks: {{ label: ctx => 'val_bpb: ' + ctx.parsed.y.toFixed(4) }} }} }},
        scales: {{
          y: {{ grid: {{ color: 'rgba(48,54,61,0.5)' }}, title: {{ display: true, text: 'val_bpb (lower is better)', color: '#8b949e' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ maxRotation: 45 }} }}
        }}
      }}
    }});

    // Steps bar
    new Chart(document.getElementById('stepsChart'), {{
      type: 'bar',
      data: {{
        labels,
        datasets: [{{
          label: 'Steps',
          data: stepsData,
          backgroundColor: 'rgba(188,140,255,0.5)',
          borderColor: '#bc8cff',
          borderWidth: 1,
          borderRadius: 6,
        }}]
      }},
      options: {{
        responsive: true,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          y: {{ grid: {{ color: 'rgba(48,54,61,0.5)' }}, title: {{ display: true, text: 'Optimizer Steps', color: '#8b949e' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ maxRotation: 45 }} }}
        }}
      }}
    }});

    // VRAM bar
    new Chart(document.getElementById('vramChart'), {{
      type: 'bar',
      data: {{
        labels,
        datasets: [{{
          label: 'Peak VRAM (GB)',
          data: vramData,
          backgroundColor: vramData.map(v => v > 60 ? 'rgba(248,81,73,0.5)' : v > 40 ? 'rgba(210,153,34,0.5)' : 'rgba(63,185,80,0.5)'),
          borderColor: vramData.map(v => v > 60 ? '#f85149' : v > 40 ? '#d29922' : '#3fb950'),
          borderWidth: 1,
          borderRadius: 6,
        }}]
      }},
      options: {{
        responsive: true,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          y: {{ grid: {{ color: 'rgba(48,54,61,0.5)' }}, title: {{ display: true, text: 'VRAM (GB)', color: '#8b949e' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ maxRotation: 45 }} }}
        }}
      }}
    }});

    // Scatter: bpb vs steps
    new Chart(document.getElementById('scatterChart'), {{
      type: 'scatter',
      data: {{
        datasets: [{{
          label: 'Experiments',
          data: stepsData.map((s, i) => ({{ x: s, y: bpbData[i] }})),
          backgroundColor: bpbColors(bpbData),
          pointRadius: 8,
          pointHoverRadius: 10,
        }}]
      }},
      options: {{
        responsive: true,
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{
            callbacks: {{
              label: ctx => descriptions[ctx.dataIndex] + ' | bpb: ' + ctx.parsed.y.toFixed(4) + ' | steps: ' + ctx.parsed.x
            }}
          }}
        }},
        scales: {{
          x: {{ grid: {{ color: 'rgba(48,54,61,0.5)' }}, title: {{ display: true, text: 'Optimizer Steps', color: '#8b949e' }} }},
          y: {{ grid: {{ color: 'rgba(48,54,61,0.5)' }}, title: {{ display: true, text: 'val_bpb', color: '#8b949e' }} }}
        }}
      }}
    }});
  </script>
</body>
</html>"""
    return html


def main():
    research_info = parse_research_log(RESEARCH_LOG)
    experiments = build_all_experiments()

    if not experiments:
        print("No experiments found in logs/")
        return

    html = generate_html(experiments, research_info)

    with open(OUTPUT, "w") as f:
        f.write(html)

    best = min(e["val_bpb"] for e in experiments)
    print(f"Dashboard generated: {OUTPUT}")
    print(f"  {len(experiments)} experiments, best val_bpb = {best:.4f}")


if __name__ == "__main__":
    main()
