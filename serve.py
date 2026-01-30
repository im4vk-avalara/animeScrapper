#!/usr/bin/env python3
"""
Simple HTTP server for the anime website.
Serves both the website and the scraped data.

Usage:
    python serve.py
    python serve.py --port 8080
"""

import http.server
import socketserver
import os
import argparse
import webbrowser
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='Serve the anime website')
    parser.add_argument('--port', type=int, default=8000, help='Port to serve on (default: 8000)')
    parser.add_argument('--no-browser', action='store_true', help="Don't open browser automatically")
    args = parser.parse_args()
    
    # Change to the animewebsite directory
    os.chdir(Path(__file__).parent)
    
    Handler = http.server.SimpleHTTPRequestHandler
    
    # Add CORS headers for local development
    class CORSHandler(Handler):
        def end_headers(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET')
            self.send_header('Cache-Control', 'no-cache')
            super().end_headers()
        
        def do_GET(self):
            # Mimic GitHub Pages structure:
            # - / serves website/index.html
            # - /styles.css, /app.js from website/
            # - /scraped_data/ from scraped_data/
            
            if self.path == '/' or self.path == '/index.html':
                self.path = '/website/index.html'
            elif self.path in ['/styles.css', '/app.js']:
                self.path = '/website' + self.path
            # scraped_data paths stay as-is (already correct)
            
            super().do_GET()
    
    with socketserver.TCPServer(("", args.port), CORSHandler) as httpd:
        url = f"http://localhost:{args.port}"
        print(f"\n🎬 Anime Stream Server")
        print(f"{'='*40}")
        print(f"Server running at: {url}")
        print(f"Website: {url}/website/")
        print(f"Data: {url}/scraped_data/current/")
        print(f"{'='*40}")
        print(f"Press Ctrl+C to stop\n")
        
        # Open browser
        if not args.no_browser:
            webbrowser.open(url)
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")

if __name__ == "__main__":
    main()
