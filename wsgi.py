"""Production WSGI entry point (e.g. `gunicorn wsgi:app`).

Separate from `python -m shopping_shorts_sync web` (the dev-server CLI
command) because a real deployment needs a WSGI callable a server like
gunicorn can import, not a `.run()` call that starts Flask's own
dev server.
"""
import os

from shopping_shorts_sync.webapp import create_app

app = create_app(products_path=os.environ.get("PRODUCTS_PATH", "data/products.example.json"))
