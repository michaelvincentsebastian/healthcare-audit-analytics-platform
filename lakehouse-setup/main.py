"""
Entry point.

- Interaktif (menu manual)      : python main.py
- Non-interaktif / automation   : python main.py auto
  (dipicu otomatis oleh docker-compose lewat `command: ["python", "main.py", "auto"]`
  begitu postgres & minio berstatus healthy -- lihat service `lakehouse-setup`)
"""

import sys

from lakehouse_manager.cli import run, run_auto

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].strip().lower() == "auto":
        run_auto()
    else:
        run()
