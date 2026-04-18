import http.server
import socketserver
import markdown
import os

PORT = 8000
DIRECTORY = "."

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        # Serve index.html or handle / natively
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            
            try:
                with open('DASHBOARD.md', 'r', encoding='utf-8') as f:
                    md_text = f.read()
                    
                # Convert markdown to html
                html_body = markdown.markdown(md_text, extensions=['tables'])
                
                # Wrap in simple HTML structure with basic styling
                html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Executive Project Dashboard</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; line-height: 1.6; max-width: 1000px; margin: 0 auto; padding: 20px; color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f6f8fa; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        h1, h2, h3 {{ border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }}
    </style>
</head>
<body>
    {html_body}
</body>
</html>"""
                self.wfile.write(html.encode("utf-8"))
            except Exception as e:
                self.wfile.write(f"<p>Error loading dashboard: {e}</p>".encode("utf-8"))
        else:
            # Let the default handler serve other static files
            super().do_GET()

print(f"Starting server at http://localhost:{PORT}")
print("Serving DASHBOARD.md as a web page. Press Ctrl+C to stop.")

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")