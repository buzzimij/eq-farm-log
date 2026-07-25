"""
Sebilis Farm Log — local server (matches the eq_inventory_pricer pattern).
Run this (or start.bat), it opens the dashboard, and the "Refresh Data"
button re-parses your EQ logs and reloads. Stdlib only.
"""
import http.server, subprocess, os, sys, webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
PORT = 8731


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/refresh":
            print("  Refresh requested -> re-running farmgen.py ...")
            subprocess.run([sys.executable, os.path.join(HERE, "farmgen.py")])
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
            return
        return super().do_GET()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    url = "http://localhost:%d/" % PORT
    print("\n  Sebilis Farm Log")
    print("  Open: %s" % url)
    print("  Press the 'Refresh Data' button on the page to re-pull from logs.")
    print("  Keep this window open; Ctrl+C or close it to stop.\n")
    server = http.server.HTTPServer(("localhost", PORT), Handler)
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")
