🖥️ T E M P S E R V E R M A K E R 
══════════════════════════════


TempServerMAKER is a simple, standalone tool that serves a local project
directory as an interactive web page. It's designed for securely feeding
your project's source code to Large Language Models (LLMs) and Retrieval-
Augmented Generation (RAG) from the convenience of your browser.
It ships as a portable project with a graphical user interface that runs on
Windows, macOS, and Linux without any external dependencies.


✨ FEATURES
══════════════════════════════
• Interactive UI: Serves a clean, modern web interface with a
collapsible file tree and expandable content cards for each file.
• Smart Parsing: Automatically uses your project's .gitignore file to
exclude unnecessary files and folders.
• No Installation Needed: Runs on any system with a standard Python 3
installation.
• Client-Server Architecture: Separates the Python back-end from the
front-end (HTML, CSS, JS), making the code easier to maintain and
customize.
• Exporting: Allows you to export the entire project view as a single,
self-contained HTML file or a detailed text-based AI report, directly
from the web interface.
• API Hooks: Includes a simple REST API for programmatic access to file
data, refreshing, and shutting down the server.


⚙️ HOW TO USE
══════════════════════════════

► On Windows
────────────────────────────
1. Place the _Temp-Server-Maker/ folder (containing the start_app.py
script) inside your project directory.
2. Open the _Temp-Server-Maker/ folder and double-click the
start_app.py file to start the server.
3. Your web browser should launch automatically with the project page.
4. When you are finished, close the terminal window to stop the server.

► On macOS or Linux (Ubuntu, etc.)
────────────────────────────
First-Time Setup (One Time Only): Before running the script for the
first time, you need to make it executable. You only have to do this
once.
1. Open your Terminal application.
2. Navigate into the _Temp-Server-Maker/ folder.
3. Run the following command and press Enter:
    ┌───────────────────────┐
    │ chmod +x start_app.py │
    └───────────────────────┘
    
Running the Application:
 1. Open a terminal in the _Temp-Server-Maker/ folder.
 2. Run the application by typing:
    ┌──────────────────┐
    │ ./start_app.py   │
    └──────────────────┘
    
 3. Your web browser should launch automatically with the project page. 
    To stop the server, go back to the terminal and press Ctrl+C.

💡 HOW IT WORKS
══════════════════════════════
This application is built with Python and its standard http.server library.
It operates on a client-server model:
• Back-End (_src/app.py): A Python script that acts as a web server. When started, it scans the project directory, gathers all relevant file data, and serves the front-end files. It also provides a simple API to access project data.
• Front-End (_src/index.html, _src/style.css, _src/index.js): A modern, single-page web application that runs in your browser. It fetches the file data from the Python back-end and dynamically renders the interactive UI.
