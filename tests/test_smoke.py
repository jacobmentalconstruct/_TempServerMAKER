import time
import threading
import requests
from contextlib import contextmanager
from pathlib import Path

# To make this runnable from the root, we need to adjust the path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _src.app import App

# --- Test Configuration ---
TEST_HOST = "127.0.0.1"
TEST_PORT = 0 # Use port 0 to let the OS pick a random free port
TEST_DIR = Path(__file__).resolve().parent

@contextmanager
def running_server():
    """Context manager to handle server startup and shutdown."""
    app_instance = App(
        directory=TEST_DIR,
        host=TEST_HOST,
        port=TEST_PORT,
        open_browser=False,
        keep_index=False,
        headless=True,
        write_report=False
    )
    
    # Start the server using its own method. This creates the httpd object 
    # and runs it in a background thread.
    app_instance.start()
    
    try:
        # Wait a moment for the server to be ready
        time.sleep(0.2)
        yield app_instance.url # Yield the actual URL provided by the app
    finally:
        # Use the app's own shutdown method for a clean exit
        app_instance.shutdown()

def test_api_ping():
    """Tests if the /__api__/ping endpoint is responsive."""
    with running_server() as base_url:
        response = requests.get(f"{base_url}__api__/ping")
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True
        assert "time" in data

def test_api_meta():
    """Tests the /__api__/meta endpoint for correct structure."""
    with running_server() as base_url:
        response = requests.get(f"{base_url}__api__/meta")
        assert response.status_code == 200
        data = response.json()
        assert "root" in data
        assert "file_count" in data
        assert data["file_count"] > 0 # Should find at least this test file

def test_api_files():
    """Tests the /__api__/files endpoint to ensure it returns a list."""
    with running_server() as base_url:
        response = requests.get(f"{base_url}__api__/files")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Check if a known file is in the list
        assert any(item.get("path") == "test_smoke.py" for item in data)

def test_api_shutdown():
    """Tests the /__api__/shutdown endpoint."""
    base_url_for_test = ""
    with running_server() as base_url:
        base_url_for_test = base_url
        # This request will be sent, and the server will shut down afterwards
        response = requests.post(f"{base_url}__api__/shutdown")
        assert response.status_code == 200
        assert response.json().get("ok") is True
        # Give shutdown a moment to complete
        time.sleep(0.2)
    
    # After exiting the 'with' block, the server should be down.
    # Attempting to connect should fail.
    try:
        requests.get(f"{base_url_for_test}__api__/ping", timeout=1)
        assert False, "Server should be down but was reachable."
    except requests.exceptions.ConnectionError:
        # This is the expected outcome, so the test passes.
        assert True


