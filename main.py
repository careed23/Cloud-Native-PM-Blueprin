from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import glob
import os
import frontmatter
import markdown
from git import Repo
import git

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
            return ["[INFO] No recent deployment logs found for instance."]
        return logs
    except Exception as e:
        return [f"[ERROR] Telemetry failure: {str(e)}"]

def get_projects():
    projects_data = []
    search_pattern = os.path.join(PROJECTS_DIR, '**', '*.md')
    md_files = glob.glob(search_pattern, recursive=True)

    for filepath in md_files:
        try:
            if 'charter' in filepath.lower() or 'readme' in filepath.lower():
                with open(filepath, 'r', encoding='utf-8') as f:
                    post = frontmatter.load(f)
                    
                if 'project_name' in post.keys():
                    status = post.get('status', 'Unknown')
                    comp_pct = post.get('completion_pct', 0)
                    monthly_spend = post.get('monthly_spend', 0) # Day 2 Ops: Cost Projection
                    
                    if isinstance(comp_pct, str):
                        comp_pct = int(comp_pct.replace('%', '').strip())
                    if isinstance(monthly_spend, str):
                        monthly_spend = int(monthly_spend.replace('$', '').replace(',', '').strip())

                    html_content = markdown.markdown(post.content, extensions=['tables', 'fenced_code'])

                    project_dir = os.path.dirname(filepath)
                    normalized_dir = project_dir.replace('\\', '/')
                    git_logs = get_recent_commits_for_path(normalized_dir, limit=3)

                    projects_data.append({
                        'name': post['project_name'],
                        'status': status,
                        'owner': post.get('owner', 'Unassigned'),
                        'completion_pct': comp_pct,
                        'monthly_spend': monthly_spend,
                        'next_steps': post.get('next_steps', 'None'),
                        'html_content': html_content,
                        'logs': git_logs
                    })
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            
    return projects_data

def get_risks():
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
                            
                        # Create markdown body for the modal deep dive
                        details_md = f"**Risk Owner:** {cols[6] if len(cols) > 6 else 'Unassigned'}\n\n**Mitigation Strategy:**\n> {cols[5]}"
                        html_content = markdown.markdown(details_md)
                            
                        risks.append({
                            'id': cols[1],
                            'description': cols[2],
                            'probability': prob,
                            'impact': impact,
                            'status': cols[7] if len(cols) > 7 else 'Open',
                            'html_content': html_content
                        })
    except Exception as e:
        print(f"Error parsing risks: {e}")
    return risks

@app.get("/events")
async def get_system_events():
    if not repo:
        return JSONResponse({"events": ["[WARN] Observability degraded. Git repository missing."]})
    
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
    """Endpoint for Trigger Manual Sync"""
    if not repo:
        return JSONResponse({"status": "error", "message": "Git repository not initialized"})
    try:
        origin = repo.remotes.origin
        origin.pull()
        return JSONResponse({"status": "success", "message": "Telemetry Synced with Origin"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    projects = get_projects()
    risks = get_risks()
    
    total_projects = len(projects)
    green_count = sum(1 for p in projects if p.get('status', '').lower() == 'green')
    health_pct = round((green_count / total_projects * 100)) if total_projects > 0 else 100
    
    active_risks = sum(1 for r in risks if r.get('impact', 0) > 3 and r.get('status', '').lower() != 'closed')
    
    # OPEX FORECAST
    total_monthly_spend = sum(p.get('monthly_spend', 0) for p in projects)

    roadmap_content = ""
    if os.path.exists("roadmap.mmd"):
        with open("roadmap.mmd", "r", encoding='utf-8') as f:
            roadmap_content = f.read()

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
            "risks": risks
        }
    )