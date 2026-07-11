
"""
Digital Financial Literacy Agent
Entry Point
"""

import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    # use_reloader=False prevents Werkzeug from spawning a child process that
    # would silently re-initialize all services (including IBM Watsonx) in a
    # second Python process whose output is not captured by any log handler.
    # For live-reload during development, restart the server manually or use
    # an external watcher (e.g. watchdog).
    debug = os.getenv("FLASK_DEBUG", "False").lower() in ("1", "true", "yes")
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=debug,
        use_reloader=False,   # ← critical: keeps everything in one process
    )
