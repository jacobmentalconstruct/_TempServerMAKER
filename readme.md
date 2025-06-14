# 🌐 _TempServerMAKER

**_TempServerMAKER** is a simple, standalone tool that serves a local project directory as a single, self-contained HTML file. It's designed for securely feeding your project's source code to local Large Language Models (LLMs) and Retrieval-Augmented Generation (RAG) tools like AnythingLLM.

It's a single Python script with a graphical user interface that runs on Windows, macOS, and Linux without any external dependencies.

![_TempServerMAKER Screenshot](https://i.imgur.com/your-screenshot-url.png)
*(To add a screenshot: run the script, take a picture of the generated HTML page in your browser, upload it to a host like [Imgur](https://imgur.com), and paste the link here.)*

## Features

* **Monolithic HTML Output:** Consolidates all relevant project files into one `index.html` for easy scraping. 
* **Interactive HTML Page:** The generated page includes a clickable table of contents and collapsible sections for each file, making it easy to navigate.
* **Smart Parsing:** Automatically uses your project's `.gitignore` file to exclude unnecessary files and folders.
* **Flexible Usage:** Run it with a simple command or use the built-in GUI to select a folder.
* **Safe & Secure:** Runs a local-only server. Your code never leaves your machine.
* **Cross-Platform:** Works on Windows, macOS, and Linux.
* **No Installation Needed:** Runs on any system with a standard Python 3 installation.

## How to Use

Choose the instructions for your operating system.

### ▶️ On Windows

1.  Place the `_TempServerMAKER` folder (containing the scripts) inside your project directory.
2.  Open the `_TempServerMAKER` folder and double-click the **`start.bat`** file to start the server. A terminal window will open, and your web browser should launch automatically.
3.  When you are finished, close the terminal window or press `Ctrl+C` to stop the server.

### ▶️ On macOS or Linux (Ubuntu, etc.)

**First-Time Setup (One-Time Only):**
Before running the script for the first time, you need to make it executable. You only have to do this once.

1.  Open your **Terminal** application.
2.  Navigate into the `_TempServerMAKER` folder.
3.  Run the following command and press Enter:
    ```sh
    chmod +x start.sh
    ```

**Running the Application:**
1.  Open a terminal in the `_TempServerMAKER` folder.
2.  Run the application by typing:
    ```sh
    ./start.sh
    ```
3.  Your web browser should launch automatically with the project page. To stop the server, go back to the terminal and press `Ctrl+C`.

## How It Works

This application is built with Python and its standard `tkinter` and `http.server` libraries. It is intentionally kept as a single, self-contained script to ensure it is portable and requires no complex setup.