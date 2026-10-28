import http.server
import socketserver
import os
import mimetypes

PORT = 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

mimetypes.add_type('image/webp', '.webp')
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/html', '.html')

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
        
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, must-revalidate')
        super().end_headers()

def run():
    port = PORT
    for _ in range(10):
        try:
            with socketserver.TCPServer(("", port), Handler) as httpd:
                print(f"Luxury Portfolio Server running at: http://localhost:{port}")
                print(f"Direct URL: http://localhost:{port}/public/index.html")
                print("Press Ctrl+C to stop.")
                httpd.serve_forever()
                break
        except OSError:
            port += 1

if __name__ == "__main__":
    run()
