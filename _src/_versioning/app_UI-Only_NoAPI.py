from __future__ import annotations
import argparse, contextlib, http.server, json, mimetypes, os, socket, socketserver, sys, threading, time, webbrowser
from pathlib import Path

try:
    import tkinter as tk
    import tkinter.filedialog as fd
    import tkinter.scrolledtext as tkscrolled
except Exception:
    tk = None
    fd = None
    tkscrolled = None

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
    MAX_TEXT_BYTES = 400_000  # per-file preview cap

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

        self.index_file = self.root_dir / "index.html"
        self.logs_dir = self.root_dir / "_logs" / "_temp-server"
        ensure_dir(self.logs_dir)
        self.log_path = self.logs_dir / f"server_{int(time.time())}.log"
        self.report_path = self.logs_dir / "ai_report.txt"

    # ------------------------ Index / Report ------------------------ #
    def _gather_files(self) -> list[Path]:
        files: list[Path] = []
        for p in self.root_dir.rglob("*"):
            if not p.is_file():
                continue
            if self.logs_dir in p.parents:
                continue
            if p == self.index_file or p == self.report_path:
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
        include_text = mtype.startswith("text/") or size <= self.MAX_TEXT_BYTES
        if include_text:
            try:
                data = p.read_bytes()
                if b"\0" not in data[:4096]:
                    if len(data) > self.MAX_TEXT_BYTES:
                        data = data[: self.MAX_TEXT_BYTES]
                    rec["text"] = data.decode("utf-8", errors="replace")
            except Exception:
                pass
        return rec

    def build_index_html(self) -> None:
        files = [self._file_record(p) for p in self._gather_files()]
        meta = {
            "generated_at": now_iso(),
            "root": str(self.root_dir),
            "file_count": len(files),
            "total_bytes": sum(f.get("size", 0) for f in files),
        }
        # Embed JSON safely for <script type="application/json"> blocks
        def safe_json(obj: object) -> str:
            return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")

        files_json = safe_json(files)
        meta_json = safe_json(meta)

        css = (
            ":root{--bg:#0b0d10;--panel:#12161b;--muted:#8aa0b5;--text:#e8eef5;--accent:#6cb2ff;--border:#233241}"
            "*{box-sizing:border-box}html,body{height:100%}"
            "body{margin:0;background:var(--bg);color:var(--text);font:14px/1.4 system-ui,Segoe UI,Roboto,Arial}"
            ".header{display:flex;gap:12px;align-items:center;padding:10px 14px;border-bottom:1px solid var(--border);background:var(--panel);position:sticky;top:0;z-index:10}"
            ".header .title{font-weight:600}.header .spacer{flex:1}"
            ".btn{background:#18212a;color:var(--text);border:1px solid var(--border);padding:6px 10px;border-radius:8px;cursor:pointer}"
            ".btn:hover{border-color:var(--accent)}"
            ".main{display:grid;grid-template-columns:320px 1fr;min-height:calc(100vh - 48px)}"
            ".sidebar{border-right:1px solid var(--border);background:#0f141a;padding:10px;overflow:auto}"
            ".content{padding:12px;overflow:auto}"
            ".tree ul{list-style:none;margin:0;padding-left:14px}.tree li{margin:2px 0}"
            ".tree .folder{cursor:pointer}.tree .folder::before{content:'▸ ';color:var(--muted)}"
            ".tree .folder.open::before{content:'▾ '}"
            ".card{border:1px solid var(--border);border-radius:10px;background:var(--panel);margin:0 0 12px}"
            ".card h3{margin:0;padding:10px;border-bottom:1px solid var(--border);font-size:13px;color:var(--muted)}"
            ".card .body{padding:10px}.meta{display:flex;gap:14px;flex-wrap:wrap;color:var(--muted)}"
            "details>summary{cursor:pointer;user-select:none}"
            "pre{white-space:pre-wrap;word-wrap:break-word;background:#0b1117;padding:10px;border-radius:8px;border:1px solid var(--border)}"
            ".small{font-size:12px;color:var(--muted)}.search{width:100%;padding:6px 8px;border-radius:8px;border:1px solid var(--border);background:#0b1117;color:var(--text);margin:0 0 10px}"
        )

        # Plain JS strings with explicit \n — no template literals, no raw newlines inside quotes
        js = (
            "var META=JSON.parse(document.getElementById(\"meta-json\").textContent);"
            "var FILES=JSON.parse(document.getElementById(\"files-json\").textContent);"
            "var $=function(s,e){return (e||document).querySelector(s)};"
            "var $$=function(s,e){return Array.from((e||document).querySelectorAll(s))};"
            # Tree
            "function makeTree(f){var r={};for(var i=0;i<f.length;i++){var x=f[i];var p=x.path.split('/');var n=r;for(var j=0;j<p.length;j++){var part=p[j];n.children=n.children||{};n.children[part]=n.children[part]||{};n=n.children[part];if(j===p.length-1){n.file=x;}}}return r;}"
            "function renderTree(n){var ul=document.createElement('ul');var entries=Object.keys(n.children||{}).sort();for(var i=0;i<entries.length;i++){var k=entries[i];var c=n.children[k];var li=document.createElement('li');if(c.file){var a=document.createElement('a');a.href='#';a.textContent=k;a.className='file';a.onclick=function(ff){return function(e){e.preventDefault();scrollToCard(ff.path);};}(c.file);li.appendChild(a);}else{var d=document.createElement('div');d.textContent=k;d.className='folder';var u=renderTree(c);u.hidden=true;d.onclick=function(dd,uu){return function(){dd.classList.toggle('open');uu.hidden=!dd.classList.contains('open');};}(d,u);li.appendChild(d);li.appendChild(u);}ul.appendChild(li);}return ul;}"
            # Render cards
            "function humanBytes(n){var u=['B','KB','MB','GB'];var i=0,x=n;while(x>=1024&&i<u.length-1){x/=1024;i++;}return (i?x.toFixed(1):x.toFixed(0))+' '+u[i];}"
            "function escapeHtml(s){return s.replace(/[&<>]/g,function(ch){return {'&':'&amp;','<':'&lt;','>':'&gt;'}[ch];});}"
            "function cssId(s){return s.replace(/[^a-zA-Z0-9_-]+/g,'_');}"
            "function cardHTML(f){var text=(typeof f.text==='string')?('<details><summary>Contents</summary><pre>'+escapeHtml(f.text)+'</pre></details>'):'<div class=small>(binary or too large to preview)</div>';var sha=f.sha1?('<div><b>sha1:</b> '+f.sha1+'</div>'):'';return '<div class=card id=\"card-'+cssId(f.path)+'\"><h3>'+f.path+'</h3><div class=body><div class=meta><div><b>Size:</b> '+humanBytes(f.size)+'</div><div><b>MIME:</b> '+f.mime+'</div>'+sha+'</div>'+text+'</div></div>'; }"
            "function renderAll(){var c=$('.content');c.innerHTML='';c.insertAdjacentHTML('beforeend','<div class=card><h3>Overview</h3><div class=body><div class=meta><div><b>Root:</b> <code>'+META.root+'</code></div><div><b>Generated:</b> '+META.generated_at+'</div><div><b>Files:</b> '+META.file_count+'</div><div><b>Total:</b> '+humanBytes(META.total_bytes)+'</div></div></div></div>');for(var i=0;i<FILES.length;i++){c.insertAdjacentHTML('beforeend',cardHTML(FILES[i]));}}"
            # Actions
            "function expandAll(){var a=$$('details');for(var i=0;i<a.length;i++){a[i].open=true;}}"
            "function collapseAll(){var a=$$('details');for(var i=0;i<a.length;i++){a[i].open=false;}}"
            "function filterCards(q){q=(q||'').trim().toLowerCase();var cards=$$('.card');for(var i=0;i<cards.length;i++){var card=cards[i];var h3=card.querySelector('h3');if(!h3)continue;var isOverview=h3.textContent==='Overview';if(isOverview){card.style.display=q?'none':'';continue;}var match=h3.textContent.toLowerCase().indexOf(q)!==-1;card.style.display=match?'':'none';}}"
            "function scrollToCard(path){var el=document.getElementById('card-'+cssId(path));if(el){el.scrollIntoView({behavior:'smooth',block:'start'});el.style.outline='1px solid var(--accent)';setTimeout(function(){el.style.outline='none';},1200);}}"
            # Exports (escaped newlines)
            "function exportHtml(){var html='<!DOCTYPE html>\\n'+document.documentElement.outerHTML;var b=new Blob([html],{type:'text/html'});var a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='index_export.html';a.click();setTimeout(function(){URL.revokeObjectURL(a.href);},2000);}"
            "function exportAiReport(){var lines=[JSON.stringify(META)];for(var i=0;i<FILES.length;i++){var f=FILES[i];lines.push('\\n'+Array(81).join('='));lines.push('FILE: '+f.path);lines.push(Array(81).join('-'));lines.push(typeof f.text==='string'?f.text:'[binary or omitted]');}var b=new Blob([lines.join('\\n')],{type:'text/plain'});var a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='ai_report.txt';a.click();setTimeout(function(){URL.revokeObjectURL(a.href);},2000);}"
            # Boot
            "window.addEventListener('DOMContentLoaded',function(){document.title='Index of '+META.root;$('.title').textContent='Index of '+META.root;$('.tree').appendChild(renderTree(makeTree(FILES)));renderAll();$('#export-html').onclick=exportHtml;$('#export-report').onclick=exportAiReport;$('#search').addEventListener('input',function(e){filterCards(e.target.value)});$('#expand').onclick=expandAll;$('#collapse').onclick=collapseAll;});"
        )

        html_doc = (
            "<!doctype html><html lang='en'><head><meta charset='utf-8'/>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'/><title>Index</title>"
            f"<style>{css}</style></head><body>"
            "<div class=header><div class=title>Index</div><div class=spacer></div>"
            "<input id=search class=search placeholder='Filter files…' style='max-width:320px'/>"
            "<button id=expand class=btn>Expand All</button><button id=collapse class=btn>Collapse All</button>"
            "<button id=export-html class=btn>Export HTML</button><button id=export-report class=btn>Export AI Report</button></div>"
            "<div class=main><aside class=sidebar><div class=tree></div></aside><section class=content></section></div>"
            f"<script id=meta-json type=application/json>{meta_json}</script>"
            f"<script id=files-json type=application/json>{files_json}</script>"
            f"<script>{js}</script></body></html>"
        )
        self.index_file.write_text(html_doc, encoding="utf-8")

    def write_ai_report(self) -> None:
        if not self.write_report_flag:
            return
        files = [self._file_record(p) for p in self._gather_files()]
        meta = {
            "generated_at": now_iso(),
            "root": str(self.root_dir),
            "file_count": len(files),
            "total_bytes": sum(f.get("size", 0) for f in files),
        }
        lines = [json.dumps(meta, ensure_ascii=False)]
        for f in files:
            lines += ["\n" + "=" * 80, f"FILE: {f['path']}", "-" * 80, f.get("text") if isinstance(f.get("text"), str) else "[binary or omitted]"]
        self.report_path.write_text("\n".join(lines), encoding="utf-8")

    # --------------------------- Server ----------------------------- #
    def _make_server(self) -> tuple[QuietTCPServer, str]:
        os.chdir(self.root_dir)
        port = self.port if self.port != 0 else pick_free_port(self.host)
        handler = http.server.SimpleHTTPRequestHandler
        httpd = QuietTCPServer((self.host, port), handler)
        url = f"http://{self.host}:{port}/"
        return httpd, url

    def start(self) -> None:
        self.build_index_html()
        self.write_ai_report()
        self.httpd, self.url = self._make_server()

        def serve() -> None:
            with contextlib.suppress(KeyboardInterrupt):
                self.httpd.serve_forever(poll_interval=0.25)

        self.thread = threading.Thread(target=serve, daemon=True)
        self.thread.start()
        self._log(f"Serving {self.root_dir} at {self.url}")
        if self.open_browser:
            webbrowser.open(self.url)

    def shutdown(self) -> None:
        if self.httpd:
            with contextlib.suppress(Exception):
                self.httpd.shutdown()
            with contextlib.suppress(Exception):
                self.httpd.server_close()
            self.httpd = None
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
        if not self.keep_index and self.index_file.exists():
            with contextlib.suppress(Exception):
                self.index_file.unlink()
        self._log("Server stopped")

    # --------------------------- Logging ---------------------------- #
    def _log(self, msg: str) -> None:
        line = f"[{now_iso()}] {msg}\n"
        sys.stdout.write(line)
        sys.stdout.flush()
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line)

    # ---------------------------- GUI (picker) ---------------------- #
    def run_gui(self) -> int:
        if tk is None:
            self._log("Tkinter not available; running headless.")
            return self.run_headless()

        root = tk.Tk()
        root.title("Temp Server Maker")
        try:
            root.tk.call('tk', 'scaling', 1.5)
        except Exception:
            pass

        dir_var = tk.StringVar(value=str(self.root_dir))
        host_var = tk.StringVar(value=self.host)
        port_var = tk.StringVar(value=str(self.port))
        url_var = tk.StringVar(value="(stopped)")

        frm = tk.Frame(root, padx=10, pady=10)
        frm.pack(fill='both', expand=True)

        # Directory picker
        r1 = tk.Frame(frm); r1.pack(fill='x')
        tk.Label(r1, text="Directory:").pack(side='left')
        ent_dir = tk.Entry(r1, textvariable=dir_var, width=48)
        ent_dir.pack(side='left', fill='x', expand=True)
        def pick_dir() -> None:
            d = fd.askdirectory(initialdir=dir_var.get() or ".") if fd else None
            if d:
                dir_var.set(d)
        tk.Button(r1, text="Choose…", command=pick_dir).pack(side='left', padx=(6, 0))

        # Host/Port
        r2 = tk.Frame(frm); r2.pack(fill='x', pady=(6, 0))
        tk.Label(r2, text="Host:").pack(side='left')
        tk.Entry(r2, textvariable=host_var, width=12).pack(side='left', padx=(4, 10))
        tk.Label(r2, text="Port:").pack(side='left')
        tk.Entry(r2, textvariable=port_var, width=8).pack(side='left', padx=(4, 10))

        # Controls
        r3 = tk.Frame(frm); r3.pack(fill='x', pady=(8, 6))
        btn_open = tk.Button(r3, text="Open Browser", command=lambda: webbrowser.open(self.url or 'about:blank'))
        btn_open.pack(side='left')

        def start_server() -> None:
            if self.httpd:
                self.shutdown()
            self.root_dir = Path(os.path.expanduser(dir_var.get())).resolve()
            self.host = host_var.get().strip() or '127.0.0.1'
            try:
                self.port = int(port_var.get())
            except Exception:
                self.port = 8000
            self.start()
            url_var.set(self.url)

        def stop_server() -> None:
            self.shutdown()
            url_var.set('(stopped)')

        tk.Button(r3, text="Start", command=start_server).pack(side='left', padx=(8, 0))
        tk.Button(r3, text="Stop", command=stop_server).pack(side='left', padx=(6, 0))

        # Save buttons
        r4 = tk.Frame(frm); r4.pack(fill='x', pady=(6, 6))
        def save_log() -> None:
            try:
                if not self.log_path.exists():
                    with open(self.log_path, 'a', encoding='utf-8') as _:
                        pass
                dest = fd.asksaveasfilename(defaultextension=".log", initialfile=self.log_path.name) if fd else None
                if dest:
                    with open(self.log_path, 'r', encoding='utf-8') as src, open(dest, 'w', encoding='utf-8') as out:
                        out.write(src.read())
            except Exception as e:
                self._log(f"save_log error: {e}")
        def save_ai_report() -> None:
            try:
                # regenerate fresh report then let user save a copy
                self.write_report_flag = True
                self.write_ai_report()
                dest = fd.asksaveasfilename(defaultextension=".txt", initialfile="ai_report.txt") if fd else None
                if dest and self.report_path.exists():
                    with open(self.report_path, 'r', encoding='utf-8') as src, open(dest, 'w', encoding='utf-8') as out:
                        out.write(src.read())
            except Exception as e:
                self._log(f"save_ai_report error: {e}")
        tk.Button(r4, text="Save Log", command=save_log).pack(side='left')
        tk.Button(r4, text="Save AI Report", command=save_ai_report).pack(side='left', padx=(6, 0))

        # URL row
        r5 = tk.Frame(frm); r5.pack(fill='x')
        tk.Label(r5, text="URL:").pack(side='left')
        tk.Entry(r5, textvariable=url_var, width=50).pack(side='left', fill='x', expand=True)

        # Log area
        log_box = None
        try:
            log_box = tkscrolled.ScrolledText(frm, height=12)
            log_box.pack(fill='both', expand=True, pady=(6, 0))
            def write_log(msg: str) -> None:
                log_box.insert('end', msg + "\n"); log_box.see('end')
            old_log = self._log
            def _log_ui(msg: str) -> None:
                old_log(msg); write_log(msg)
            self._log = _log_ui
        except Exception:
            pass

        def on_close() -> None:
            try:
                self.shutdown()
            finally:
                root.destroy()
        root.protocol('WM_DELETE_WINDOW', on_close)

        # Do NOT auto-start; user must press Start
        root.mainloop()
        return 0

    # ------------------------- Headless loop ------------------------ #
    def run_headless(self) -> int:
        self.start()
        self._log("Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            self._log("Shutting down…")
            self.shutdown()
        return 0

# ----------------------------- CLI entry ---------------------------- #

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Temp Server Maker — simple HTTP server with rich HTML index")
    p.add_argument('-d', '--directory', default='.', help='Directory to serve (default: .)')
    p.add_argument('--host', default='127.0.0.1', help='Host/IP to bind (default: 127.0.0.1)')
    p.add_argument('-p', '--port', type=int, default=8000, help='Port (0 = random free port; default: 8000)')
    p.add_argument('--open', action='store_true', help='Open default browser to the server URL')
    p.add_argument('--keep-file', action='store_true', help='Keep generated index.html on exit')
    p.add_argument('--no-gui', action='store_true', help='Run headless (no Tk window)')
    p.add_argument('--report', action='store_true', help='Also write ai_report.txt to _logs/_temp-server/')
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    directory = Path(os.path.expanduser(args.directory)).resolve()
    if not directory.exists() or not directory.is_dir():
        print(f"[error] directory does not exist: {directory}")
        return 2

    app = App(
        directory=directory,
        host=args.host,
        port=args.port,
        open_browser=args.open,
        keep_index=args.keep_file,
        headless=bool(args.no_gui),
        write_report=bool(args.report),
    )

    if app.headless:
        return app.run_headless()
    else:
        return app.run_gui()


if __name__ == '__main__':
    raise SystemExit(main())

