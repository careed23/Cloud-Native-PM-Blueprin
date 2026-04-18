import os
import glob
import json
import frontmatter
from datetime import datetime, timezone
from jinja2 import Environment, FileSystemLoader

PROJECTS_DIR = 'projects'
HTML_OUTPUT = 'index.html'

def parse_risks(filepath):
    # Very basic markdown table parser for the risk register
    risks = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Find the markdown table start
            in_table = False
            for line in lines:
                if '|' in line and '---' in line:
                    in_table = True
                    continue
                if in_table and '|' in line:
                    cols = [c.strip() for c in line.split('|') if c.strip()] # Filter out empty strings
                    if len(cols) >= 4: # Check for at least 4 meaningful columns (ID, Desc, Prob, Impact)
                        # Assuming structure: Risk ID | Description | Probability | Impact | ...
                        risks.append({
                            'id': cols[0],
                            'description': cols[1],
                            'probability': cols[2],
                            'impact': cols[3]
                        })
    except Exception as e:
        print(f"Error parsing risks in {filepath}: {e}")
    return risks

def generate_dashboard():
    projects_data = []
    all_risks = []
    blockers = []

    # Crawl the projects directory for all markdown files
    search_pattern = os.path.join(PROJECTS_DIR, '**', '*.md')
    md_files = glob.glob(search_pattern, recursive=True)

    for filepath in md_files:
        try:
            # Parse Charters for main project cards
            if 'charter' in filepath.lower() or 'readme' in filepath.lower():
                with open(filepath, 'r', encoding='utf-8') as f:
                    post = frontmatter.load(f)
                    
                if all(key in post.keys() for key in ['project_name', 'status', 'next_steps']):
                    projects_data.append({
                        'name': post['project_name'],
                        'status': post['status'],
                        'next_steps': post['next_steps'],
                        'owner': post.get('owner', 'Unassigned'),
                        'duration': post.get('duration', '3 Months (Est)'),
                        'capacity': post.get('capacity', 'Standard Tier')
                    })
                    
                    # AI Insight Mock: Flag Blockers
                    if 'blocked' in post['next_steps'].lower() or 'blocker' in post['next_steps'].lower():
                        blockers.append({
                            'project': post['project_name'],
                            'text': post['next_steps']
                        })

            # Parse Risk Registers
            if 'risk' in filepath.lower():
                proj_risks = parse_risks(filepath)
                all_risks.extend(proj_risks)

        except Exception as e:
            print(f"Error processing {filepath}: {e}")

    # Set up Jinja2 Environment
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('dashboard_template.html')

    # Render Template
    html_out = template.render(
        timestamp=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        projects=projects_data,
        risks_json=json.dumps(all_risks),
        blockers=blockers
    )

    # Write output
    with open(HTML_OUTPUT, 'w', encoding='utf-8') as f:
        f.write(html_out)

    print(f"Successfully generated high-end UI at {HTML_OUTPUT}")

if __name__ == "__main__":
    generate_dashboard()