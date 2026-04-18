from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import glob
import os
import frontmatter
import markdown
import subprocess

app = FastAPI(title="Cloud-Native PM Dashboard")

# Setup Jinja2 templates directory
templates = Jinja2Templates(directory="templates")

PROJECTS_DIR = 'projects'

def get_git_logs(filepath, limit=5):
    """Attempt to get the last N git commits for a specific file/directory"""
    try:
        # Get absolute path or rely on relative git execution
        result = subprocess.run(
            ['git', 'log', f'-n {limit}', '--pretty=format:%h - %ad - %s', '--date=short', '--', filepath],
            capture_output=True, text=True, check=True
        )
        logs = result.stdout.split('\n')
        if logs == ['']: return []
        return logs
    except Exception as e:
        return [f"Git log unavailable ({e})"]

def get_projects():
    projects_data = []
    # Crawl the projects directory for all markdown files
    search_pattern = os.path.join(PROJECTS_DIR, '**', '*.md')
    md_files = glob.glob(search_pattern, recursive=True)

    for filepath in md_files:
        try:
            # We assume project data is mainly in the charter or a main readme file
            if 'charter' in filepath.lower() or 'readme' in filepath.lower():
                with open(filepath, 'r', encoding='utf-8') as f:
                    post = frontmatter.load(f)
                    
                # Ensure it's one of our project markdown files
                if 'project_name' in post.keys():
                    # Safely extract and format variables with defaults
                    status = post.get('status', 'Unknown')
                    comp_pct = post.get('completion_pct', 0)
                    
                    if isinstance(comp_pct, str):
                        comp_pct = int(comp_pct.replace('%', '').strip())

                    # Parse the markdown content to HTML for the modal
                    html_content = markdown.markdown(post.content, extensions=['tables', 'fenced_code'])

                    # Attempt to get local git logs
                    git_logs = get_git_logs(os.path.dirname(filepath))

                    projects_data.append({
                        'name': post['project_name'],
                        'status': status,
                        'owner': post.get('owner', 'Unassigned'),
                        'completion_pct': comp_pct,
                        'next_steps': post.get('next_steps', 'None'),
                        'html_content': html_content,
                        'logs': git_logs
                    })
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            
    return projects_data

def get_global_risks():
    risks = []
    filepath = 'risks/global_risks.md'
    if not os.path.exists(filepath):
        # Fallback to local project risks if global isn't found
        search_pattern = os.path.join(PROJECTS_DIR, '**', '*risk*.md')
        risk_files = glob.glob(search_pattern, recursive=True)
        if not risk_files:
            return risks
        filepath = risk_files[0] # Just grab the first one for demonstration

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
                        risks.append({
                            'id': cols[1],
                            'description': cols[2],
                            'probability': cols[3],
                            'impact': cols[4],
                            'status': cols[7] if len(cols) > 7 else 'Open'
                        })
    except Exception as e:
        print(f"Error parsing risks: {e}")
    return risks

def get_system_events():
    """Mock up some system events based on git global logs"""
    try:
        result = subprocess.run(
            ['git', 'log', '-n 10', '--pretty=format:[%ad] SYSTEM: %s', '--date=iso-local'],
            capture_output=True, text=True, check=True
        )
        logs = result.stdout.split('\n')
        if logs == ['']: return ["[SYS_INIT] Observability enabled. Ready for events."]
        return logs
    except:
        return [
            "[2026-04-17 21:30:15] INSTANCE: Demo Cloud Migration - STATUS updated to GREEN.",
            "[2026-04-17 21:28:42] ENGINE: Heatmap component re-rendered.",
            "[2026-04-17 21:15:00] PIPELINE: Build #402 passed.",
            "[2026-04-17 20:05:11] ALERT: Global Risk G-01 probability escalated to HIGH."
        ]

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    projects = get_projects()
    risks = get_global_risks()
    
    # Telemetry Calculations
    total_projects = len(projects)
    green_count = sum(1 for p in projects if p.get('status', '').lower() == 'green')
    health_pct = round((green_count / total_projects * 100)) if total_projects > 0 else 100
    open_risks = sum(1 for r in risks if r.get('status', '').lower() == 'open')

    # Roadmap
    roadmap_content = ""
    if os.path.exists("roadmap.mmd"):
        with open("roadmap.mmd", "r", encoding='utf-8') as f:
            roadmap_content = f.read()

    system_events = get_system_events()

    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={
            "projects": projects,
            "roadmap": roadmap_content,
            "telemetry": {
                "total_projects": total_projects,
                "health": health_pct,
                "open_risks": open_risks
            },
            "risks": risks,
            "system_events": system_events
        }
    )
