#!/usr/bin/env python3
"""
WSGI entry point for gunicorn.
This file helps avoid naming conflicts between app.py and the app/ directory.
"""

# Import the Flask app instance from app.py
from app import app, socketio

# This is the object that gunicorn will use
if __name__ == "__main__":
    socketio.run(app)
