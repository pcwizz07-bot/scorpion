#!/usr/bin/env python3
"""
Dungbeetle API Proxy - forwards Pi device requests to Convex backend
Listens on 0.0.0.0:3001, routes to Convex at 127.0.0.1:3210
"""
import json, urllib.request, urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

CONVEX_URL = "http://127.0.0.1:3210"

ROUTES = {
    "/api/devices/register": ("devices:register", "mutation"),
    "/api/devices/heartbeat": ("devices:heartbeat", "mutation"),
    "/api/observations/imsi": ("observations:recordObservation", "mutation"),
    "/api/observations/raw": (None, None),
    "/api/health": (None, None),
}

class ProxyHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_cors()
        self.send_response(200)
        self.end_headers()

    def send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len)
        
        route = ROUTES.get(self.path)
        if not route or not route[0]:
            self.send_error(404, f"No route: {self.path}")
            return
        
        fn_name, fn_type = route
        try:
            # Convex API expects: {"path": "module:fn", "args": {...}}
            # Pi sends the args directly, so we wrap them
            args = json.loads(body.decode()) if body else {}
            convex_body = json.dumps({"path": fn_name, "args": args}).encode()
            
            convex_url = f"{CONVEX_URL}/api/{fn_type}"
            req = urllib.request.Request(convex_url, data=convex_body,
                headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=10)
            resp_data = json.loads(resp.read().decode())
            
            # Extract the value from Convex's response wrapper: {status: "success", value: ...}
            result = resp_data.get("value", resp_data)
            
            self.send_response(200)
            self.send_cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        except Exception as e:
            self.send_response(500)
            self.send_cors()
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_GET(self):
        self.send_response(200)
        self.send_cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "service": "dungbeetle-api"}).encode())

if __name__ == "__main__":
    port = 3001
    server = HTTPServer(("0.0.0.0", port), ProxyHandler)
    print(f"Dungbeetle API Proxy on 0.0.0.0:{port} -> Convex {CONVEX_URL}")
    server.serve_forever()