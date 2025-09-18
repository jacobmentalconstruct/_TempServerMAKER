from __future__ import annotations
import argparse, contextlib, http.server, json, mimetypes, os, socket, socketserver, sys, threading, time, webbrowser
from pathlib import Path

try:
    import tkinter as tk
    import tkinter.filedialog as fd
except Exception:
    tk = None
    fd = None

# ------------------------------ Utilities ------------------------------ #
class QuietTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def pick_free_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

# ---------------------------- Core Application ------------------------- #
class App:
    MAX_TEXT_BYTES = 400_000

    def __init__(self, directory: Path, host: str, port: int,
                 open_browser: bool, keep_index: bool,
                 headless: bool, write_report: bool) -> None:
        self.root_dir = Path(directory).resolve()
        self.host = host
        self.port = port
        self.open_browser = open_browser
        self.keep_index = keep_index
        self.headless = headless
        self.write_report_flag = write_report
        self.httpd: QuietTCPServer | None = None
        self.thread: threading.Thread | None = None
        self.url: str = ""
        self.template_path = self.root_dir / "index.html"
        self.logs_dir = self.root_dir / "_logs" / "_temp-server"
        ensure_dir(self.logs_dir)
        self.log_path = self.logs_dir / f"server_{int(time.time())}.log"
        self.report_path = self.logs_dir / "ai_report.txt"

    def _gather_files(self) -> list[Path]:
        files: list[Path] = []
        for p in self.root_dir.rglob("*"):
            if not p.is_file():
                continue
            if any(part.startswith('.') for part in p.parts) or self.logs_dir in p.parents or p.name == "app.py":
                continue
            files.append(p)
        files.sort()
        return files

    def _file_record(self, p: Path) -> dict:
        rel = str(p.relative_to(self.root_dir))
        size = p.stat().st_size
        mtype, _ = mimetypes.guess_type(rel)
        mtype = mtype or "application/octet-stream"
        rec: dict[str, object] = {"path": rel, "size": size, "mime": mtype}
        if (mtype.startswith("text/") or size <= self.MAX_TEXT_BYTES):
            try:
                data = p.read_bytes()
                if b"\x00" not in data[:4096]:
                    rec["text"] = data[:self.MAX_TEXT_BYTES].decode("utf-8", errors="replace")
            except Exception:
                pass
        return rec

    def generate_populated_html(self) -> str:
        if not self.template_path.exists():
            return "<html><body><h1>Error</h1><p>index.html not found in the root directory.</p></body></html>"
        files = [self._file_record(p) for p in self._gather_files()]
        meta = {"generated_at": now_iso(), "root": str(self.root_dir), "file_count": len(files), "total_bytes": sum(f.get("size", 0) for f in files)}
        def safe_json(obj: object) -> str:
            return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")
        template_content = self.template_path.read_text(encoding="utf-8")
        populated_html = template_content.replace('<script id="meta-json" type="application/json"></script>', f'<script id="meta-json" type="application/json">{safe_json(meta)}</script>')
        populated_html = populated_html.replace('<script id="files-json" type="application/json"></script>', f'<script id="files-json" type="application/json">{safe_json(files)}</script>')
        return populated_html

    def write_ai_report(self) -> None:
        if not self.write_report_flag:
            return
        files = [self._file_record(p) for p in self._gather_files()]
        meta = {"generated_at": now_iso(), "root": str(self.root_dir), "file_count": len(files), "total_bytes": sum(f.get("size", 0) for f in files)}
        lines = [json.dumps(meta, ensure_ascii=False)]
        for f in files:
            lines += ["\n" + "=" * 80, f"FILE: {f['path']}", "-" * 80, f.get("text") if isinstance(f.get("text"), str) else "[binary or omitted]"]
        self.report_path.write_text("\n".join(lines), encoding="utf-8")

    def refresh(self) -> None:
        self.write_ai_report()
        self._log("Refreshed AI report")

    def _make_server(self) -> tuple[QuietTCPServer, str]:
        os.chdir(self.root_dir)
        port = self.port if self.port != 0 else pick_free_port(self.host)
        app_ref = self

        class Handler(http.server.SimpleHTTPRequestHandler):
            def _set_cors(self):
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')

            def _send_json(self, obj: object, code: int = 200):
                data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
                self.send_response(code)
                self._set_cors()
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _send_text(self, text: str, code: int = 200, ctype: str = 'text/plain; charset=utf-8'):
                b = text.encode('utf-8')
                self.send_response(code)
                self._set_cors()
                self.send_header('Content-Type', ctype)
                self.send_header('Content-Length', str(len(b)))
                self.end_headers()
                self.wfile.write(b)

            def do_OPTIONS(self):
                self.send_response(204)
                self._set_cors()
                self.end_headers()

            def do_POST(self):
                if self.path.startswith('/__api__/refresh'):
                    app_ref.refresh()
                    return self._send_json({"ok": True, "url": app_ref.url, "root": str(app_ref.root_dir)})
                if self.path.startswith('/__api__/shutdown'):
                    self._send_json({"ok": True})
                    threading.Thread(target=app_ref.shutdown, daemon=True).start()
                    return
                return super().do_POST()

            def do_GET(self):
                if self.path.startswith('/__api__/'):
                    if self.path == '/__api__/ping':
                        return self._send_json({"ok": True, "time": now_iso()})
                    if self.path == '/__api__/meta':
                        files = [app_ref._file_record(p) for p in app_ref._gather_files()]
                        meta = {"generated_at": now_iso(), "root": str(app_ref.root_dir), "file_count": len(files), "total_bytes": sum(f.get('size', 0) for f in files)}
                        return self._send_json(meta)
                    if self.path == '/__api__/files':
                        files = [app_ref._file_record(p) for p in app_ref._gather_files()]
                        return self._send_json(files)
                    return self._send_json({"error": "not found"}, 404)

                if self.path == '/' or self.path == '/index.html':
                    html_content = app_ref.generate_populated_html()
                    return self._send_text(html_content, ctype='text/html; charset=utf-8')

                return super().do_GET()

        httpd = QuietTCPServer((self.host, port), Handler)
        url = f"http://{self.host}:{port}/"
        return httpd, url

    def start(self) -> None:
        self.write_ai_report()
        self.httpd, self.url = self._make_server()
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self._log(f"Serving {self.root_dir} at {self.url}")
        if self.open_browser:
            webbrowser.open(self.url)

    def shutdown(self) -> None:
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
        self._log("Server stopped")

    def _log(self, msg: str) -> None:
        line = f"[{now_iso()}] {msg}\n"
        sys.stdout.write(line)
        sys.stdout.flush()
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line)

    def run_headless(self) -> int:
        self.start()
        print(f"[info] Serving {self.root_dir} at {self.url}")
        try:
            while self.thread and self.thread.is_alive():
                time.sleep(0.2)
        except KeyboardInterrupt:
            print("\n[info] Keyboard interrupt received, shutting down.")
        finally:
            self.shutdown()
        return 0

    def run_gui(self) -> int:
        if tk is None:
            print("[error] Tkinter is not available on this system.")
            return 1
        root = tk.Tk()
        root.title("Temp Server Maker")
        status_var = tk.StringVar(value=f"Directory: {self.root_dir}")
        tk.Label(root, textvariable=status_var, anchor='w', padx=10, pady=5).pack(fill='x')
        ctrls = tk.Frame(root, padx=10, pady=5)
        ctrls.pack(fill='x')
        def start_server():
            self.start()
            status_var.set(f"Server running at {self.url}")
        def stop_server():
            self.shutdown()
            status_var.set("Server stopped.")
        for text, cmd in (("Start", start_server), ("Stop", stop_server), ("Open", lambda: webbrowser.open(self.url)), ("Quit", root.destroy)):
            tk.Button(ctrls, text=text, command=cmd).pack(side='left')
        root.mainloop()
        return 0

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Temp Server Maker — simple HTTP server with rich HTML index")
    p.add_argument('-d', '--directory', default='.', help='Directory to serve (default: .)')
    p.add_argument('--host', default='127.0.0.1', help='Host/IP to bind (default: 127.0.0.1)')
    p.add_argument('-p', '--port', type=int, default=8000, help='Port (0 = random; default: 8000)')
    p.add_argument('--open', action='store_true', help='Open default browser to the server URL')
    p.add_argument('--no-gui', action='store_true', help='Run headless (no Tk window)')
    p.add_argument('--report', action='store_true', help='Also write ai_report.txt to _logs/_temp-server/')
    p.add_argument('--keep-file', action='store_true', help='Keep generated files on exit (deprecated)')
    return p.parse_args(argv)

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    directory = (Path(__file__).resolve().parent if args.directory == '.' else Path(os.path.expanduser(args.directory)).resolve())
    if not directory.is_dir():
        print(f"[error] directory does not exist: {directory}")
        return 2
    app = App(directory=directory, host=args.host, port=args.port, open_browser=args.open, headless=args.no_gui, write_report=args.report, keep_index=args.keep_file)
    return app.run_headless() if app.headless else app.run_gui()

if __name__ == "__main__":
    raise SystemExit(main())
