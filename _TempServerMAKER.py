# local_server_for_scraper.py
#
# Version 7.1 (Community Edition - Hardened)
# - Fixed cross-platform bug causing "I/O operation on closed file" error by
#   removing global os.chdir and passing the directory to the handler directly.
# - Robust threading model to prevent UI blocking during file processing.
# - Graceful shutdown on Ctrl+C across Windows, macOS, and Linux.
# - Enhanced HTML markup with a navigable Table of Contents and collapsible sections.
# - Dynamic in-terminal progress bar for better user feedback during indexing.

import argparse
import http.server
import socketserver
import os
import webbrowser
import fnmatch
import html
import sys
import time
import threading
import functools # <--- 1. IMPORTED FUNCTOOLS
from pathlib import Path
from typing import Set, Optional

# --- Configuration (remains the same) ---
TEXT_FILE_EXTENSIONS = {
    '.txt', '.md', '.markdown', '.rst', '.py', '.js', '.ts', '.html', '.css',
    '.scss', '.json', '.xml', '.yaml', '.yml', '.ini', '.toml', '.cfg', '.env',
    '.sh', '.bat', '.ps1', '.sql', '.java', '.c', '.cpp', '.h', '.hpp', '.cs',
    '.go', '.rb', '.php', '.rs', '.swift', '.kt', '.kts', '.scala', '.pl',
    '.pm', '.t', '.r', '.dockerfile', 'dockerfile', '.gitignore'
}

DEFAULT_IGNORE_DIRS = {
    '.git', 'node_modules', 'venv', '.venv', 'env', '.env', 'build', 'dist',
    'target', '__pycache__', '.pytest_cache', '.mypy_cache', '.tox', '.idea',
    '.vscode'
}

# --- Server Threading ---
class ServerThread(threading.Thread):
    """A thread that runs the HTTP server and can be stopped gracefully."""
    def __init__(self, directory: Path, port: int):
        super().__init__()
        self.daemon = True
        self.port = port
        self.directory = directory
        self._server = None
        self._server_started = threading.Event()

    def run(self):
        """The core of the server thread. This is the updated section."""
        # --- 2. THE FIX ---
        # Instead of changing the global directory, we tell the handler
        # which directory to serve directly. This is much safer.
        Handler = functools.partial(
            http.server.SimpleHTTPRequestHandler,
            directory=str(self.directory)
        )
        # -----------------

        try:
            self._server = socketserver.TCPServer(("", self.port), Handler)
            self._server_started.set() # Signal that the server object is created
            self._server.serve_forever(poll_interval=0.5)
        except Exception as e:
            print(f"\n[Error] Could not start server: {e}", file=sys.stderr)
            self._server_started.set()

    def start_and_wait(self):
        """Starts the thread and waits until the server is initialized."""
        self.start()
        self._server_started.wait()
        if not self._server:
             raise ConnectionError("Server failed to initialize.")

    def stop(self):
        """Stops the running server."""
        if self._server:
            self._server.shutdown()
            self._server.server_close()

# --- Core Logic (remains the same) ---
def is_port_in_use(port: int) -> bool:
    """Checks if a TCP port is already in use."""
    with socketserver.socket.socket(socketserver.socket.AF_INET, socketserver.socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def is_text_file(p: Path) -> bool:
    """Checks if a file is likely a text file based on its extension."""
    if p.name.startswith('.') and not p.suffix:
        return False
    return p.suffix.lower() in TEXT_FILE_EXTENSIONS

def load_gitignore_patterns(root_path: Path) -> Set[str]:
    """Finds and parses a .gitignore file, returning a set of ignore patterns."""
    gitignore_path = root_path / '.gitignore'
    patterns = set()
    if gitignore_path.is_file():
        try:
            with gitignore_path.open('r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    stripped_line = line.strip()
                    if stripped_line and not stripped_line.startswith('#'):
                        patterns.add(stripped_line)
        except Exception as e:
            print(f"\nWarning: Could not read .gitignore file. Error: {e}")
    return patterns

def create_monolithic_html_file(root_path: Path, ignore_patterns: Set[str]) -> tuple[Path, int]:
    """Generates a single HTML file containing the content of all relevant files."""
    index_filepath = root_path / "index.html"
    files_to_process = []

    # First, walk the directory to gather a list of files to process
    for dirpath, dirnames, filenames in os.walk(root_path, topdown=True):
        current_dir = Path(dirpath)
        dirs_to_exclude = DEFAULT_IGNORE_DIRS.copy()
        for pattern in ignore_patterns:
            dirs_to_exclude.update(fnmatch.filter(dirnames, pattern))
        dirnames[:] = [d for d in dirnames if d not in dirs_to_exclude]

        for filename in filenames:
            file_path = current_dir / filename
            is_ignored_by_pattern = any(fnmatch.fnmatch(str(file_path.relative_to(root_path)), p) for p in ignore_patterns)
            if is_text_file(file_path) and file_path != index_filepath and not is_ignored_by_pattern:
                files_to_process.append(file_path)
    
    # Now, process the files and write the HTML
    total_files = len(files_to_process)
    files_processed_count = 0
    
    with index_filepath.open("w", encoding="utf-8") as f:
        # --- HTML Header and Enhanced Styling ---
        f.write('<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">\n')
        f.write(f'<title>Consolidated Index of {root_path.name}</title>\n')
        f.write("""
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen-Sans, Ubuntu, Cantarell, "Helvetica Neue", sans-serif; line-height: 1.6; margin: 0; background-color: #f8f9fa; }
            .container { max-width: 1200px; margin: 0 auto; padding: 2em; }
            .header { background-color: #343a40; color: white; padding: 2em; text-align: center; border-radius: 8px; margin-bottom: 2em; }
            .toc { background-color: #fff; border: 1px solid #dee2e6; border-radius: 8px; padding: 1.5em; margin-bottom: 2em; }
            .toc ul { padding-left: 20px; columns: 3; -webkit-columns: 3; -moz-columns: 3; }
            .file-section { background-color: #fff; border: 1px solid #dee2e6; border-radius: 8px; margin-bottom: 1em; }
            .file-title { font-size: 1.2em; font-weight: 600; padding: 0.8em 1.2em; background-color: #f1f3f5; border-bottom: 1px solid #dee2e6; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
            .file-title::after { content: '▼'; font-size: 0.8em; }
            .file-content { display: none; padding: 1.5em; max-height: 500px; overflow: auto; }
            .file-content pre { margin: 0; background-color: #e9ecef; padding: 1em; border-radius: 5px; white-space: pre-wrap; word-wrap: break-word; }
            .active .file-content { display: block; }
            .active .file-title::after { content: '▲'; }
        </style>""")
        f.write("</head><body>\n<div class='container'>\n")
        f.write(f"<div class='header'><h1>Consolidated Files for Project: {html.escape(root_path.name)}</h1></div>\n")

        # --- Table of Contents ---
        f.write("<div class='toc'><h2>Table of Contents</h2><ul>\n")
        for file_path in sorted(files_to_process):
            relative_path = file_path.relative_to(root_path)
            f.write(f"<li><a href='#{html.escape(str(relative_path))}'>{html.escape(str(relative_path))}</a></li>\n")
        f.write("</ul></div>\n")

        # --- File Contents ---
        for file_path in sorted(files_to_process):
            relative_path = file_path.relative_to(root_path)
            
            f.write(f"<div class='file-section' id='{html.escape(str(relative_path))}'>\n")
            f.write(f"<h2 class='file-title'>{html.escape(str(relative_path))}</h2>\n")
            f.write("<div class='file-content'><pre><code>")
            
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                f.write(html.escape(content))
            except Exception as e:
                f.write(f"Could not read file. Error: {e}")
            
            f.write("</code></pre></div>\n</div>\n")
            files_processed_count += 1
            # --- Progress Bar ---
            progress = int((files_processed_count / total_files) * 50)
            sys.stdout.write(f"\r  Indexing: [{'#' * progress}{'-' * (50 - progress)}] {files_processed_count}/{total_files} files")
            sys.stdout.flush()

        # **** THE FIX IS HERE ****
        # These lines are now INDENTED to be inside the 'with' block
        f.write("""
            <script>
                document.querySelectorAll('.file-title').forEach(title => {
                    title.addEventListener('click', () => {
                        title.parentElement.classList.toggle('active');
                    });
                });
            </script>
        """)
        f.write("</div></body></html>")
    
    # This line now correctly happens after the file is closed.
    sys.stdout.write("\n") 
    return index_filepath, files_processed_count
    
def select_directory_gui() -> Optional[Path]:
    """Shows a GUI folder selection dialog."""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        print("\n[Warning] tkinter not found. For GUI folder selection, please install it.", file=sys.stderr)
        print("  On Debian/Ubuntu: sudo apt-get install python3-tk", file=sys.stderr)
        print("  Please specify a directory using the -d flag instead.", file=sys.stderr)
        return None

    print("No directory specified. Opening folder selection dialog...")
    root = tk.Tk()
    root.withdraw()
    selected_path_str = filedialog.askdirectory(title="Select Project Folder to Serve")
    return Path(selected_path_str) if selected_path_str else None
# --- Main Execution (Version 7.2 - Sequential Logic) ---
def main():
    parser = argparse.ArgumentParser(
        description="Serve a local project directory as a single HTML file for scraping.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('-d', '--directory', type=Path, help="Project directory to serve.\nIf not provided, a GUI dialog will open.")
    parser.add_argument('-p', '--port', type=int, default=8000, help="Port to run the server on (default: 8000).")
    parser.add_argument('--keep-file', action='store_true', help="Do not delete the generated index.html on exit.")
    parser.add_argument('--no-browser', action='store_true', help="Do not automatically open a web browser.")
    args = parser.parse_args()

    # --- Step 1: Select Directory ---
    selected_path = args.directory
    if not selected_path:
        selected_path = select_directory_gui()

    if not selected_path or not selected_path.is_dir():
        print("No valid directory selected. Exiting.", file=sys.stderr)
        sys.exit(1)
    
    selected_path = selected_path.resolve()
    print(f"\nProject folder: {selected_path}")

    # --- Step 2: Generate the HTML file FIRST ---
    print("\nStarting file indexing process...")
    ignore_patterns = load_gitignore_patterns(selected_path)
    index_filepath, file_count = create_monolithic_html_file(selected_path, ignore_patterns)
    print(f"Successfully indexed {file_count} files.")

    # --- Step 3: Check port and start the server ONLY AFTER file is ready ---
    if is_port_in_use(args.port):
        print(f"\n[Error] Port {args.port} is already in use.", file=sys.stderr)
        print("Please choose a different port using the -p flag (e.g., -p 8001).", file=sys.stderr)
        sys.exit(1)

    server_thread = None
    try:
        server_thread = ServerThread(selected_path, args.port)
        server_thread.start_and_wait()
        server_url = f"http://127.0.0.1:{args.port}/"

        print("\n" + "="*50)
        print("  SERVER IS RUNNING! ✅")
        print("="*50)
        print(f"  URL: {server_url}")
        print("Your project is now ready for scraping.")
        print("\nTo stop the server, press Ctrl+C in this terminal.")

        if not args.no_browser:
            webbrowser.open_new_tab(server_url)

        # Keep the main thread alive to handle KeyboardInterrupt
        while True:
            time.sleep(1)

    except (KeyboardInterrupt, SystemExit):
        print("\n\n[Info] Shutdown signal received. Cleaning up...")
    except Exception as e:
        print(f"\n[Error] An unexpected error occurred: {e}", file=sys.stderr)
    finally:
        if server_thread and server_thread.is_alive():
            server_thread.stop()
            server_thread.join()
        
        if index_filepath and index_filepath.exists():
            if args.keep_file:
                print(f"[Info] Kept generated file at: {index_filepath}")
            else:
                try:
                    print("[Info] Removing temporary index file...")
                    index_filepath.unlink()
                except Exception as e:
                    print(f"[Error] Could not remove index file: {e}", file=sys.stderr)
        
        print("Goodbye! 👋")
if __name__ == "__main__":
    main()