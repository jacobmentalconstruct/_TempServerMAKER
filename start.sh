#!/bin/bash
# =================================================================
#  Startup script for the Local Project Server on Linux/macOS
# =================================================================

echo "Starting the Local Project Server..."
echo "This will open the Python script and may prompt for folder selection."

# Runs the python script. Assumes 'python3' is in the user's PATH.
# The script name is hardcoded. If you rename it, change it here too.
python3 _TempServerMAKER.py

echo ""
echo "Server has been shut down. Terminal window can be closed."