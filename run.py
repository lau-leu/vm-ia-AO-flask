#!/usr/bin/env python3
"""Script de lancement de l'application AppliWeb-AO."""
import subprocess
import sys

def main():
    """Lancer l'application Streamlit."""
    port = 8501
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "app/streamlit_app.py",
        f"--server.port={port}",
        "--server.address=0.0.0.0",
	"--server.headless=true"
    ])

if __name__ == "__main__":
    main()
