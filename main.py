from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import glob
import os
import frontmatter
import markdown
from git import Repo
import git
from xhtml2pdf import pisa
import io
import functools
import random
from dotenv import load_dotenv
from datetime import datetime
import asyncio

# 1. Secure API Management
load_dotenv()
PORTFOLIO_MODE = os.getenv('PORTFOLIO_MODE', 'false').lower() == 'true'
MOCK_AI_MODE = os.getenv('MOCK_AI_MODE', 'true').lower() == 'true'

app = FastAPI(title="Mission Control | Observability Platform")

templates = Jinja2Templates(directory="templates")
PROJECTS_DIR = 'projects'

try:
    repo = Repo('.')
except git.exc.InvalidGitRepositoryError:
    repo = None
    print("Warning: Not a valid Git repository.")

def get_recent_commits_for_path(path_pattern, limit=3):
    if not repo:
        return ["[WARN] Git repository not initialized."]
    
    logs = []
    try:
        commits = list(repo.iter_commits(paths=path_pattern, max_count=limit))
        for c in commits:
            date_str = c.committed_datetime.strftime("%Y-%m-%d")
            msg_short = c.message.split('\n')[0][:50]
            logs.append(f"[{c.hexsha[:7]}] {msg_short} ({date_str})")
            
        if not logs:
            return ["[INFO] No recent deployment logs found."]
        return logs
    except Exception as e:
        return [f"[ERROR] Telemetry failure: {str(e)}"]

@functools.lru_cache(maxsize=1)
def get_projects_cached():
    projects_data = []
    search_pattern = os.path.join(PROJECTS_DIR, '**', '*.md')
    md_files = glob.glob(search_pattern, recursive=True)

    for idx, filepath in enumerate(md_files):
        try:
            if 'charter' in filepath.lower() or 'readme' in filepath.lower():
                with open(filepath, 'r', encoding='utf-8') as f:
                    post = frontmatter.load(f)
                    
                if 'project_name' in post.keys():
                    # 3. Portfolio Mode Anonymization
                    name = f"Project Alpha-{idx+1}" if PORTFOLIO_MODE else post['project_name']
                    status = post.get('status', 'Unknown')
                    comp_pct = post.get('completion_pct', 0)
                    monthly_spend = post.get('monthly_spend', 0)
                    
                    if isinstance(comp_pct, str):
                        comp_pct = int(comp_pct.replace('%', '').strip())
                    if isinstance(monthly_spend, str):
                        monthly_spend = int(monthly_spend.replace('$', '').replace(',', '').strip())

                    # Scramble budget if Portfolio Mode
                    if PORTFOLIO_MODE:
                        monthly_spend = random.randint(15000, 150000)

                    html_content = markdown.markdown(post.content, extensions=['tables', 'fenced_code'])

                    project_dir = os.path.dirname(filepath)
                    normalized_dir = project_dir.replace('\\', '/')
                    git_logs = get_recent_commits_for_path(normalized_dir, limit=3)

                    projects_data.append({
                        'id': f"proj-{idx}",
                        'name': name,
                        'status': status,
                        'owner': "Classified" if PORTFOLIO_MODE else post.get('owner', 'Unassigned'),
                        'completion_pct': comp_pct,
                        'monthly_spend': monthly_spend,
                        'next_steps': post.get('next_steps', 'None'),
                        'html_content': html_content,
                        'logs': git_logs
                    })
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            
    return projects_data

def get_projects():
    return get_projects_cached()

@functools.lru_cache(maxsize=1)
def get_risks_cached():
    risks = []
    filepath = 'risks/global_risks.md'
    
    if not os.path.exists(filepath):
        search_pattern = os.path.join(PROJECTS_DIR, '**', '*risk*.md')
        risk_files = glob.glob(search_pattern, recursive=True)
        if risk_files: filepath = risk_files[0]
        else: return risks

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            in_table = False
            for line in lines:
                if '|' in line and '---' in line:
                    in_table = True
                    continue
                if in_table and '|' in line:
                    cols = [c.strip() for c in line.split('|')]
                    if len(cols) > 5 and cols[1] != 'Risk ID':
                        try:
                            prob = int(cols[3])
                            impact = int(cols[4])
                        except ValueError:
                            prob = 3
                            impact = 3
                            
                        desc = "Classified Threat Vector" if PORTFOLIO_MODE else cols[2]
                        owner = "Classified" if PORTFOLIO_MODE else (cols[6] if len(cols) > 6 else 'Unassigned')
                        
                        details_md = f"**Risk Owner:** {owner}\n\n**Mitigation Strategy:**\n> {cols[5]}"
                        html_content = markdown.markdown(details_md)
                            
                        risks.append({
                            'id': cols[1],
                            'description': desc,
                            'probability': prob,
                            'impact': impact,
                            'status': cols[7] if len(cols) > 7 else 'Open',
                            'html_content': html_content
                        })
    except Exception as e:
        print(f"Error parsing risks: {e}")
    return risks

def get_risks():
    return get_risks_cached()

async def generate_ai_briefing(projects, risks):
    """1. Secure API Management & Mock Mode"""
    # Simulate LLM Latency for skeleton loading effect
    await asyncio.sleep(1)
    
    critical_risks = [r for r in risks if r['impact'] > 3]
    red_projects = [p for p in projects if p['status'].lower() == 'red']
    
    if MOCK_AI_MODE:
        responses = [
            "System intelligence suggests nominal behavior. Recommend maintaining current capacity allocation.",
            f"Heuristic analysis indicates {len(critical_risks)} vectors require immediate attention to prevent deployment bottleneck.",
            f"Resource contention detected in backend zones. Advise shifting compute allocation to mitigate {len(red_projects)} failing nodes."
        ]
        return random.choice(responses)
        
    # Real integration goes here using os.getenv('AWS_ACCESS_KEY_ID')
    return "Amazon Bedrock Response: System requires attention on High Impact risks."

@app.get("/api/ai-briefing")
async def api_ai_briefing():
    """Async endpoint for the AI Briefing to load independently"""
    projects = get_projects()
    risks = get_risks()
    briefing = await generate_ai_briefing(projects, risks)
    return JSONResponse({"briefing": briefing})

@app.get("/api/state")
async def get_system_state():
    """2. Dynamic Data Refresh Endpoint"""
    projects = get_projects()
    # Return light-weight state for polling
    state = {
        "projects": [
            {
                "id": p["id"],
                "logs": p["logs"]
            } for p in projects
        ]
    }
    return JSONResponse(state)

@app.get("/events")
async def get_system_events():
    if not repo:
        return JSONResponse({"events": ["[WARN] Observability degraded. Git repository missing."] * 3})
    
    events = []
    try:
        commits = list(repo.iter_commits(max_count=10))
        for c in commits:
            date_str = c.committed_datetime.strftime("%Y-%m-%d %H:%M:%S")
            msg_short = c.message.split('\n')[0]
            
            prefix = "[OK]"
            if "fix" in msg_short.lower() or "risk" in msg_short.lower() or "alert" in msg_short.lower():
                prefix = "[WARN]"
                
            events.append(f"[{date_str}] {prefix} {msg_short}")
            
        if not events:
            events = ["[INFO] System nominal. Awaiting telemetry..."]
    except Exception as e:
        events = [f"[ERROR] Event aggregation failed: {e}"]
        
    return JSONResponse({"events": events})

@app.post("/sync")
async def manual_sync():
    if not repo:
        get_projects_cached.cache_clear()
        get_risks_cached.cache_clear()
        return JSONResponse({"status": "success", "message": "Local Cache Cleared"})
    try:
        origin = repo.remotes.origin
        origin.pull()
        get_projects_cached.cache_clear()
        get_risks_cached.cache_clear()
        return JSONResponse({"status": "success", "message": "Telemetry Synced with Origin"})
    except Exception as e:
        get_projects_cached.cache_clear()
        get_risks_cached.cache_clear()
        return JSONResponse({"status": "error", "message": str(e)})

@app.get("/export")
async def export_report(request: Request):
    projects = get_projects()
    risks = get_risks()
    
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Helvetica, Arial, sans-serif; color: #333; }}
            h1 {{ color: #0f172a; border-bottom: 2px solid #0ea5e9; padding-bottom: 10px; }}
            h2 {{ color: #1e293b; margin-top: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ border: 1px solid #cbd5e1; padding: 8px; text-align: left; }}
            th {{ background-color: #f1f5f9; }}
        </style>
    </head>
    <body>
        <h1>Mission Control | Executive Summary</h1>
        <h2>Active Projects</h2>
        <table>
            <tr><th>Project</th><th>Status</th><th>Completion</th><th>Monthly Spend</th></tr>
            {"".join(f"<tr><td>{p['name']}</td><td>{p['status']}</td><td>{p['completion_pct']}%</td><td>${p['monthly_spend']}</td></tr>" for p in projects)}
        </table>
        <h2>Critical Risks</h2>
        <table>
            <tr><th>ID</th><th>Description</th><th>Impact</th><th>Probability</th></tr>
            {"".join(f"<tr><td>{r['id']}</td><td>{r['description']}</td><td>{r['impact']}</td><td>{r['probability']}</td></tr>" for r in risks if r['impact'] > 3)}
        </table>
    </body>
    </html>
    """
    
    pdf_path = "executive_summary.pdf"
    with open(pdf_path, "w+b") as result_file:
        pisa_status = pisa.CreatePDF(io.StringIO(html_content), dest=result_file)
        
    return FileResponse(pdf_path, filename="Executive_Summary.pdf")

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    projects = get_projects()
    risks = get_risks()
    
    total_projects = len(projects)
    green_count = sum(1 for p in projects if p.get('status', '').lower() == 'green')
    health_pct = round((green_count / total_projects * 100)) if total_projects > 0 else 100
    active_risks = sum(1 for r in risks if r.get('impact', 0) > 3 and r.get('status', '').lower() != 'closed')
    total_monthly_spend = sum(p.get('monthly_spend', 0) for p in projects)
    
    roadmap_content = ""
    if os.path.exists("roadmap.mmd"):
        with open("roadmap.mmd", "r", encoding='utf-8') as f:
            roadmap_content = f.read()
            
        dynamic_styles = "\n    classDef green fill:#10b981,stroke:#047857;\n    classDef yellow fill:#f59e0b,stroke:#b45309;\n    classDef red fill:#ef4444,stroke:#b91c1c;\n"
        
        # Only inject if we aren't in portfolio mode which breaks the name matching
        if not PORTFOLIO_MODE and "Demo Cloud Migration" in [p['name'] for p in projects]:
            status = next(p['status'] for p in projects if p['name'] == "Demo Cloud Migration").lower()
            dynamic_styles += f"    class des1,des2 {status};\n"
            
        roadmap_content += dynamic_styles

    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={
            "projects": projects,
            "roadmap": roadmap_content,
            "telemetry": {
                "total_projects": total_projects,
                "health": health_pct,
                "active_risks": active_risks,
                "monthly_spend": total_monthly_spend
            },
            "risks": risks,
            "portfolio_mode": PORTFOLIO_MODE,
            "system_time": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        }
    )