import threading
import sys
import os
from server import run_server
from gui import IDMCloneGUI

# Redirect stdout/stderr to a log file to avoid UnicodeEncodeError on Windows console
_log_path = os.path.join(os.path.dirname(__file__), "app.log")
try:
    _log_file = open(_log_path, "w", encoding="utf-8", errors="replace")
    sys.stdout = _log_file
    sys.stderr = _log_file
except Exception:
    pass


def main():
    # Start the Flask server in a background thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Start the CustomTkinter GUI in the main thread
    app = IDMCloneGUI()
    app.mainloop()


if __name__ == '__main__':
    main()
