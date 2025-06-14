# Local Project Server for Scrapers

A simple, powerful Python script that serves an entire local project directory as a single, self-contained HTML file. It's perfect for feeding your project's source code to local Large Language Models (LLMs) and Retrieval-Augmented Generation (RAG) tools like AnythingLLM securely and privately.

## Features

* **Monolithic HTML Output**: Consolidates all relevant text-based project files into a single `index.html` for easy scraping.
* **Interactive & Modern UI**: The generated page includes a clickable table of contents and collapsible sections for each file, making it easy to navigate and review.
* **Smart Parsing**: Automatically respects your project's `.gitignore` file to exclude unnecessary files and folders, in addition to common temporary directories (`node_modules`, `venv`, etc.).
* **Flexible & User-Friendly**: Run it directly with command-line arguments or use the built-in GUI to select a folder if no path is provided.
* **Safe & Secure**: Runs a local-only server on `127.0.0.1`. Your code never leaves your machine.
* **Robust & Cross-Platform**: Built with a multi-threaded design for a non-blocking UI and graceful shutdown. It works on Windows, macOS, and Linux.

## Requirements

* Python 3.7+
* `tkinter` is required for the GUI folder picker. This is usually included with Python on Windows and macOS. On Linux, it may need to be installed separately:
    ```bash
    # For Debian/Ubuntu-based systems
    sudo apt-get install python3-tk
    ```

## Usage

1.  Save the script to a file (e.g., `serve_project.py`).
2.  Open your terminal or command prompt.
3.  Run the script using one of the methods below.

---

### **Method 1: Interactive Mode (Recommended)**

If you run the script without specifying a directory, a graphical folder selection dialog will automatically open.

```bash
python serve_project.py
```

Simply choose the project folder you wish to serve.

### **Method 2: Command-Line Mode**

You can specify the directory and other options directly via command-line flags.

**Serve the current directory:**

```bash
python serve_project.py -d .
```

**Serve a specific project on a different port:**

```bash
python serve_project.py --directory /path/to/your/project --port 8080
```

**Keep the generated `index.html` file after the server stops:**

```bash
python serve_project.py -d . --keep-file
```

**Run without automatically opening a web browser:**

```bash
python serve_project.py -d . --no-browser
```

### **Accessing the Served Project**

Once the server is running, the script will print a URL to the console (e.g., `http://127.0.0.1:8000/`).

1.  Use this URL in your scraping tool or open it in a web browser.
2.  To stop the server, press **`Ctrl+C`** in the terminal. The temporary `index.html` file will be cleaned up automatically unless you used the `--keep-file` flag.