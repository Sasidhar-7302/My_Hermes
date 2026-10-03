# -*- coding: utf-8 -*-
import os, json, re
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
from role_registry import ROLES, VERIFIED_MODELS

app = FastAPI(title="Hermes Agent Company")

ROLE_META = {
    "CEO": {
        "icon": "🧠",
        "title": "Chief Executive Officer",
        "desc": "System orchestrator. Delegates tasks, reviews outputs, and synthesizes lessons into memory.",
        "color": "#38bdf8"
    },
    "PM": {
        "icon": "📋",
        "title": "Product Manager",
        "desc": "Converts user vision into unambiguous specs, acceptance criteria, and prioritized feature scope.",
        "color": "#a78bfa"
    },
    "ARCHITECT": {
        "icon": "🏗️",
        "title": "System Architect",
        "desc": "Designs directory structure, database schemas, API contracts, protocols, and scaling topology.",
        "color": "#fbbf24"
    },
    "CODER": {
        "icon": "💻",
        "title": "Lead Software Engineer",
        "desc": "Writes clean, tested, and documented code based strictly on architecture specs.",
        "color": "#34d399"
    },
    "TESTER": {
        "icon": "🧪",
        "title": "QA & Test Engineer",
        "desc": "Validates edge cases, writes automated test suites, and blocks buggy implementations.",
        "color": "#f472b6"
    },
    "SECURITY": {
        "icon": "🔒",
        "title": "Security Auditor",
        "desc": "Audits code for OWASP vulnerabilities, credential leaks, and insecure dependencies.",
        "color": "#f87171"
    },
    "DEVOPS": {
        "icon": "🚀",
        "title": "DevOps & Infrastructure",
        "desc": "Manages scripts, Docker containers, CI/CD automation, and deployment stability.",
        "color": "#fb923c"
    },
    "OPERATOR": {
        "icon": "🖥️",
        "title": "Desktop & Computer Operator",
        "desc": "Automates OS tasks, window management, and application workflows under strict deletion & payment shields.",
        "color": "#06b6d4"
    }
}

def get_tasks():
    tasks_file = os.path.join(os.path.dirname(__file__), 'role_tasks.json')
    if os.path.exists(tasks_file):
        try:
            with open(tasks_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
def get_employee_logs(role: str = None):
    emp_dir = os.path.join(os.path.dirname(__file__), 'employee_logs')
    if role:
        emp_file = os.path.join(emp_dir, f"{role}.json")
        if os.path.exists(emp_file):
            try:
                with open(emp_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        # Fallback to filtering global tasks
        all_tasks = get_tasks()
        return [t for t in all_tasks if t.get("role") == role]
    return get_tasks()

@app.get("/api/employee_logs/{role}")
async def api_get_employee_logs(role: str):
    logs = get_employee_logs(role)
    return JSONResponse(content={"role": role, "count": len(logs), "logs": logs})

def save_soul(role, new_soul):
    reg_file = os.path.join(os.path.dirname(__file__), 'role_registry.py')
    with open(reg_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    pattern = rf'("{role}":\s*\{{[^}}]*?"soul":\s*")(?:[^"\\]|\\.)*(")'
    escaped_soul = new_soul.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    new_content, count = re.subn(pattern, rf'\g<1>{escaped_soul}\g<2>', content, count=1)
    
    if count > 0:
        with open(reg_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

@app.post("/api/update_soul")
async def api_update_soul(request: Request):
    data = await request.json()
    role = data.get("role")
    soul = data.get("soul")
    if role and soul is not None:
        success = save_soul(role, soul)
        return {"status": "ok" if success else "error"}
    return {"status": "bad_request"}

@app.get("/", response_class=HTMLResponse)
def dashboard():
    tasks = get_tasks()
    
    import importlib
    import role_registry
    importlib.reload(role_registry)
    current_roles = role_registry.ROLES

    num_roles = len(current_roles)
    num_tasks = len(tasks)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Hermes Multi-Agent Company</title>
    <style>
        :root {{
            --bg-canvas: #041411;
            --bg-card: #061e19;
            --bg-card-alt: #082620;
            --bg-input: #020d0b;
            --border-subtle: #0d3830;
            --border-bright: #1c6153;
            --text-heading: #f6e6a1;
            --text-main: #d3f3e3;
            --text-muted: #719f8e;
            --accent-green: #34d399;
            --btn-bg: #0b332b;
            --btn-hover: #124b3f;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: var(--bg-canvas);
            color: var(--text-main);
            padding: 24px 32px 60px;
            font-size: 13px;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }}

        ::-webkit-scrollbar {{
            width: 6px;
            height: 6px;
        }}
        ::-webkit-scrollbar-track {{
            background: transparent;
        }}
        ::-webkit-scrollbar-thumb {{
            background: var(--border-subtle);
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: var(--border-bright);
        }}

        /* TOP STATS BAR */
        .stats-bar {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}

        .stat-widget {{
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 8px;
            padding: 14px 18px;
            display: flex;
            align-items: center;
            gap: 14px;
        }}

        .stat-icon {{
            font-size: 24px;
            width: 44px;
            height: 44px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            border-radius: 8px;
        }}

        .stat-meta {{
            display: flex;
            flex-direction: column;
        }}

        .stat-label {{
            font-size: 10px;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--text-muted);
            font-weight: 600;
        }}

        .stat-val {{
            font-size: 16px;
            font-weight: 700;
            color: var(--text-heading);
            margin-top: 2px;
        }}

        /* TABS HEADER */
        .nav-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-subtle);
            padding-bottom: 14px;
            margin-bottom: 24px;
        }}

        .nav-title-group {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .section-title {{
            color: var(--text-heading);
            font-size: 16px;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}

        .tab-controls {{
            display: flex;
            gap: 8px;
            background: var(--bg-card);
            padding: 3px;
            border-radius: 6px;
            border: 1px solid var(--border-subtle);
        }}

        .tab-btn {{
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 6px 14px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            cursor: pointer;
            transition: all 0.15s ease;
        }}

        .tab-btn:hover {{
            color: var(--text-main);
        }}

        .tab-btn.active {{
            background: var(--btn-bg);
            color: var(--text-heading);
            border: 1px solid var(--border-bright);
        }}

        .tab-panel {{
            display: none;
        }}

        .tab-panel.active {{
            display: block;
        }}

        /* EMPLOYEE CARDS GRID */
        .cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
            gap: 20px;
        }}

        .employee-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 8px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 16px;
            transition: transform 0.15s ease, border-color 0.15s ease;
        }}

        .employee-card:hover {{
            border-color: var(--border-bright);
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);
        }}

        .card-top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }}

        .role-identity {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .role-avatar {{
            font-size: 26px;
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            width: 48px;
            height: 48px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .role-details {{
            display: flex;
            flex-direction: column;
        }}

        .role-badge-row {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .role-name {{
            color: var(--text-heading);
            font-size: 16px;
            font-weight: 700;
            letter-spacing: 0.05em;
        }}

        .role-subhead {{
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 2px;
        }}

        .status-pill {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 3px 8px;
            border-radius: 9999px;
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            background: rgba(52, 211, 153, 0.12);
            color: var(--accent-green);
            border: 1px solid rgba(52, 211, 153, 0.25);
        }}

        .pulse-dot {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background-color: var(--accent-green);
            animation: pulse 2s infinite;
        }}

        @keyframes pulse {{
            0% {{ opacity: 0.4; transform: scale(0.9); }}
            50% {{ opacity: 1; transform: scale(1.1); }}
            100% {{ opacity: 0.4; transform: scale(0.9); }}
        }}

        /* FALLBACK ROSTER CHAIN */
        .roster-section {{
            display: flex;
            flex-direction: column;
            gap: 8px;
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            border-radius: 6px;
            padding: 12px;
        }}

        .roster-title-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 10px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--text-muted);
            font-weight: 600;
        }}

        .chain-flow {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 6px;
        }}

        .chain-node {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-family: ui-monospace, SFMono-Regular, monospace;
            color: var(--text-main);
        }}

        .node-idx {{
            color: var(--text-heading);
            font-weight: 700;
            font-size: 10px;
        }}

        .node-quota {{
            font-size: 9px;
            color: var(--text-muted);
            background: rgba(255, 255, 255, 0.05);
            padding: 1px 4px;
            border-radius: 3px;
        }}

        .chain-arrow {{
            color: var(--text-muted);
            font-size: 10px;
        }}

        /* SOUL DIRECTIVES TEXTAREA */
        .soul-container {{
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}

        .soul-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 10px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--text-muted);
            font-weight: 600;
        }}

        .soul-box {{
            width: 100%;
            height: 85px;
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            border-radius: 6px;
            color: var(--text-main);
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 11px;
            line-height: 1.5;
            padding: 10px 12px;
            resize: vertical;
            outline: none;
            transition: border-color 0.15s;
        }}

        .soul-box:focus {{
            border-color: var(--accent-green);
        }}

        .action-row {{
            display: flex;
            justify-content: flex-end;
            align-items: center;
            gap: 10px;
            margin-top: 4px;
        }}

        .save-indicator {{
            font-size: 11px;
            color: var(--accent-green);
            opacity: 0;
            transition: opacity 0.2s;
            font-weight: 600;
        }}

        .save-indicator.visible {{
            opacity: 1;
        }}

        .btn-save {{
            background: var(--btn-bg);
            border: 1px solid var(--border-subtle);
            color: var(--text-heading);
            padding: 7px 16px;
            border-radius: 5px;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            cursor: pointer;
            transition: all 0.15s ease;
        }}

        .btn-save:hover {{
            background: var(--btn-hover);
            border-color: var(--text-heading);
        }}

        /* EMPLOYEE LOGS ACCORDION */
        .emp-logs-accordion {{
            margin-top: 14px;
            border-top: 1px solid var(--border-subtle);
            padding-top: 12px;
        }}

        .btn-toggle-logs {{
            width: 100%;
            background: var(--bg-card-alt);
            border: 1px solid var(--border-subtle);
            color: var(--text-main);
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.15s ease;
        }}

        .btn-toggle-logs:hover {{
            background: var(--btn-bg);
            border-color: var(--accent-green);
            color: var(--text-heading);
        }}

        .emp-logs-panel {{
            margin-top: 10px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 260px;
            overflow-y: auto;
            padding-right: 4px;
        }}

        .emp-log-item {{
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            border-radius: 4px;
            padding: 8px 10px;
            font-size: 11px;
        }}

        .emp-log-top {{
            display: flex;
            justify-content: space-between;
            color: var(--text-muted);
            margin-bottom: 4px;
            font-size: 10px;
        }}

        .emp-log-task {{
            font-weight: 600;
            color: var(--text-heading);
            margin-bottom: 4px;
        }}

        .emp-log-resp {{
            color: var(--text-main);
            font-family: ui-monospace, SFMono-Regular, monospace;
            font-size: 10px;
            white-space: pre-wrap;
            max-height: 70px;
            overflow: hidden;
            text-overflow: ellipsis;
            line-height: 1.4;
        }}

        /* FILTER BAR IN LOGS TAB */
        .filter-bar {{
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            margin-bottom: 16px;
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 6px;
            padding: 10px 16px;
        }}

        .filter-chips {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}

        .chip {{
            background: var(--bg-card-alt);
            border: 1px solid var(--border-subtle);
            color: var(--text-muted);
            padding: 5px 12px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
        }}

        .chip:hover {{
            color: var(--text-main);
            border-color: var(--border-bright);
        }}

        .chip.active {{
            background: var(--btn-bg);
            border-color: var(--accent-green);
            color: var(--text-heading);
        }}

        .search-input {{
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            color: var(--text-main);
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 11px;
            min-width: 240px;
        }}

        .search-input:focus {{
            outline: none;
            border-color: var(--accent-green);
        }}

        /* AUDIT TRAIL LOGS */
        .logs-stream {{
            display: flex;
            flex-direction: column;
            gap: 14px;
        }}

        .log-entry {{
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-left: 3px solid var(--accent-green);
            border-radius: 6px;
            padding: 16px 20px;
        }}

        .log-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}

        .log-role-tag {{
            font-weight: 700;
            color: var(--text-heading);
            font-size: 13px;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .log-metrics {{
            display: flex;
            gap: 12px;
            font-size: 11px;
            color: var(--text-muted);
        }}

        .log-prompt {{
            font-weight: 500;
            color: var(--text-main);
            background: var(--bg-input);
            padding: 8px 12px;
            border-radius: 4px;
            margin-bottom: 10px;
            font-size: 12px;
            border-left: 2px solid var(--border-bright);
        }}

        .log-output {{
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            border-radius: 4px;
            padding: 12px 14px;
            font-family: ui-monospace, SFMono-Regular, monospace;
            font-size: 11px;
            color: var(--text-main);
            white-space: pre-wrap;
            max-height: 240px;
            overflow-y: auto;
            line-height: 1.6;
        }}

        .empty-logs {{
            padding: 48px;
            text-align: center;
            color: var(--text-muted);
            border: 1px dashed var(--border-subtle);
            border-radius: 8px;
            background: var(--bg-card);
        }}

        /* TOAST */
        #toast {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: var(--bg-card);
            border: 1px solid var(--accent-green);
            color: var(--text-heading);
            padding: 10px 18px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            gap: 8px;
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            z-index: 9999;
        }}

        #toast.show {{
            transform: translateY(0);
            opacity: 1;
        }}
    </style>
</head>
<body>
    <!-- TOP STATS OVERVIEW -->
    <div class="stats-bar">
        <div class="stat-widget">
            <div class="stat-icon">🏢</div>
            <div class="stat-meta">
                <span class="stat-label">Active Agents</span>
                <span class="stat-val">{num_roles} Autonomous Roles</span>
            </div>
        </div>
        <div class="stat-widget">
            <div class="stat-icon">⚡</div>
            <div class="stat-meta">
                <span class="stat-label">System-1 Router</span>
                <span class="stat-val">Laya (ONNX ~33ms)</span>
            </div>
        </div>
        <div class="stat-widget">
            <div class="stat-icon">🛡️</div>
            <div class="stat-meta">
                <span class="stat-label">Quota Strategy</span>
                <span class="stat-val">Free Tier Optimized</span>
            </div>
        </div>
        <div class="stat-widget">
            <div class="stat-icon">📊</div>
            <div class="stat-meta">
                <span class="stat-label">Dispatched Tasks</span>
                <span class="stat-val">{num_tasks} Recorded</span>
            </div>
        </div>
    </div>

    <!-- NAVIGATION TABS -->
    <div class="nav-header">
        <div class="nav-title-group">
            <span class="section-title">Company Workspace</span>
        </div>
        <div class="tab-controls">
            <button class="tab-btn active" onclick="setTab('roster')">Team Roster ({num_roles})</button>
            <button class="tab-btn" onclick="setTab('logs')">Task Audit Trail ({num_tasks})</button>
        </div>
    </div>

    <!-- ROSTER TAB -->
    <div id="tab-roster" class="tab-panel active">
        <div class="cards-grid">
"""

    for role_name, data in current_roles.items():
        soul = data.get("soul", "")
        models = data.get("models", [])
        meta = ROLE_META.get(role_name, {
            "icon": "🤖",
            "title": f"{role_name} Agent",
            "desc": "Autonomous specialist",
            "color": "#38bdf8"
        })

        nodes_html = []
        for i, m in enumerate(models):
            nodes_html.append(f"""
                <div class="chain-node">
                    <span class="node-idx">#{i+1}</span>
                    <span>{m['name']}</span>
                    <span class="node-quota">{m['quota']}</span>
                </div>
            """)
        
        chain_html = ' <span class="chain-arrow">&rarr;</span> '.join(nodes_html)

        html += f"""
            <div class="employee-card">
                <div class="card-top">
                    <div class="role-identity">
                        <div class="role-avatar">{meta['icon']}</div>
                        <div class="role-details">
                            <div class="role-badge-row">
                                <span class="role-name">{role_name}</span>
                            </div>
                            <span class="role-subhead">{meta['title']}</span>
                        </div>
                    </div>
                    <div class="status-pill">
                        <div class="pulse-dot"></div>
                        <span>ONLINE</span>
                    </div>
                </div>

                <div class="roster-section">
                    <div class="roster-title-row">
                        <span>Model Failover Cascade</span>
                        <span>Auto-Failover</span>
                    </div>
                    <div class="chain-flow">
                        {chain_html}
                    </div>
                </div>

                <div class="soul-container">
                    <div class="soul-header">
                        <span>Soul Directives & Memory</span>
                        <span>Auto-Synchronized</span>
                    </div>
                    <textarea id="soul-{role_name}" class="soul-box">{soul}</textarea>
                    <div class="action-row">
                        <span id="saved-{role_name}" class="save-indicator">&check; Updated!</span>
                        <button class="btn-save" onclick="updateSoul('{role_name}')">Save Directives</button>
                    </div>
                </div>

                <div class="emp-logs-accordion">
                    <button class="btn-toggle-logs" onclick="toggleEmpLogs('{role_name}')">
                        <span>📜 Employee Activity Log ({len(get_employee_logs(role_name))})</span>
                        <span id="arrow-{role_name}">▼</span>
                    </button>
                    <div id="logs-{role_name}" class="emp-logs-panel" style="display: none;">
        """

        emp_logs = get_employee_logs(role_name)
        if emp_logs:
            for item in emp_logs[:10]:
                ts = item.get("timestamp", "")[:19].replace("T", " ")
                lat = item.get("latency_ms", 0)
                mdl = item.get("model", "")
                tsk = item.get("task", "")
                rsp = item.get("response", "")
                html += f"""
                        <div class="emp-log-item">
                            <div class="emp-log-top">
                                <span>{ts}</span>
                                <span style="color: var(--accent-green);">{lat}ms &bull; {mdl}</span>
                            </div>
                            <div class="emp-log-task"><strong>Task:</strong> {tsk}</div>
                            <div class="emp-log-resp">{rsp}</div>
                        </div>
                """
        else:
            html += f"""
                        <div class="emp-log-item" style="color: var(--text-muted); text-align: center; padding: 12px;">
                            No tasks recorded yet for {role_name}. Dispatched actions will appear here.
                        </div>
            """

        html += f"""
                    </div>
                </div>
            </div>
        """

    # Role counts for filter chips
    role_counts = {}
    for t in tasks:
        r = t.get("role", "OTHER")
        role_counts[r] = role_counts.get(r, 0) + 1

    chips_html = f'<button class="chip active" onclick="filterLogs(\'ALL\')">All Tasks ({num_tasks})</button>'
    for r in current_roles.keys():
        c = role_counts.get(r, 0)
        chips_html += f'<button class="chip" onclick="filterLogs(\'{r}\')">{r} ({c})</button>'

    html += f"""
        </div>
    </div>

    <!-- LOGS TAB -->
    <div id="tab-logs" class="tab-panel">
        <div class="filter-bar">
            <div class="filter-chips">
                {chips_html}
            </div>
            <input type="text" class="search-input" id="log-search" placeholder="Search tasks, models, or outputs..." onkeyup="searchLogs()" />
        </div>
        <div class="logs-stream">
    """

    if not tasks:
        html += """
            <div class="empty-logs">
                <p>No agent tasks logged yet. Tasks run through <code>agent_dispatcher.py</code> will appear here automatically.</p>
            </div>
        """
    else:
        for t in tasks:
            timestamp = t.get("timestamp", "")[:19].replace("T", " ")
            role = t.get("role", "SYSTEM")
            meta = ROLE_META.get(role, {"icon": "🤖"})
            html += f"""
            <div class="log-entry" data-role="{role}">
                <div class="log-header">
                    <div class="log-role-tag">
                        <span>{meta['icon']}</span>
                        <span>{role} &bull; {t.get('model', 'Model')}</span>
                    </div>
                    <div class="log-metrics">
                        <span>{timestamp}</span>
                        <span style="color: var(--accent-green); font-weight: 600;">{t.get('latency_ms', 0)}ms</span>
                    </div>
                </div>
                <div class="log-prompt"><strong>Prompt:</strong> {t.get('task', '')}</div>
                <div class="log-output">{t.get('response', '')}</div>
            </div>
            """

    html += """
        </div>
    </div>

    <div id="toast">
        <span>&check;</span>
        <span id="toast-msg">Directives updated successfully</span>
    </div>

    <script>
        function setTab(tabId) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));

            if (tabId === 'roster') {
                event.target.classList.add('active');
                document.getElementById('tab-roster').classList.add('active');
            } else {
                event.target.classList.add('active');
                document.getElementById('tab-logs').classList.add('active');
            }
        }

        function toggleEmpLogs(role) {
            const panel = document.getElementById('logs-' + role);
            const arrow = document.getElementById('arrow-' + role);
            if (!panel) return;
            if (panel.style.display === 'none' || !panel.style.display) {
                panel.style.display = 'flex';
                arrow.innerText = '▲';
            } else {
                panel.style.display = 'none';
                arrow.innerText = '▼';
            }
        }

        let currentFilter = 'ALL';
        function filterLogs(role) {
            currentFilter = role;
            document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
            event.target.classList.add('active');
            applyFilters();
        }

        function searchLogs() {
            applyFilters();
        }

        function applyFilters() {
            const query = (document.getElementById('log-search')?.value || '').toLowerCase();
            const entries = document.querySelectorAll('.log-entry');
            entries.forEach(entry => {
                const role = entry.getAttribute('data-role');
                const text = entry.innerText.toLowerCase();
                const roleMatch = (currentFilter === 'ALL' || role === currentFilter);
                const searchMatch = !query || text.includes(query);
                entry.style.display = (roleMatch && searchMatch) ? 'block' : 'none';
            });
        }

        async function updateSoul(role) {
            const textarea = document.getElementById('soul-' + role);
            const soul = textarea.value;
            const indicator = document.getElementById('saved-' + role);

            try {
                const res = await fetch('/api/update_soul', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ role: role, soul: soul })
                });
                const data = await res.json();
                if (data.status === 'ok') {
                    indicator.classList.add('visible');
                    setTimeout(() => indicator.classList.remove('visible'), 2500);
                    showToast(`Updated ${role} Soul memory`);
                } else {
                    alert('Error saving directives');
                }
            } catch (err) {
                alert('Connection error: ' + err);
            }
        }

        function showToast(text) {
            const toast = document.getElementById('toast');
            document.getElementById('toast-msg').innerText = text;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 3000);
        }
    </script>
</body>
</html>
    """
    return html

if __name__ == "__main__":
    print("Starting Hermes Modern Company Dashboard on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
