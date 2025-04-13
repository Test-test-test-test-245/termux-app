#!/usr/bin/env python3
"""
WSGI entry point for gunicorn.
This file helps avoid naming conflicts between the app/ directory and our Flask app.
"""

# Import the Flask app instance from flask_app.py (renamed from app.py)
from flask_app import app, socketio

# This is the object that gunicorn will use
if __name__ == "__main__":
    socketio.run(app)
