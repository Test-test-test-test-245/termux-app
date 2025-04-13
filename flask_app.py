#!/usr/bin/env python3

import os
import sys

# Try to use gevent first (more compatible with Python 3.11 on Render),
# fall back to other options if not available
async_mode = 'gevent'
try:
    import gevent
    import gevent.monkey
    gevent.monkey.patch_all()
    print("Using gevent for async mode")
except ImportError:
    try:
        import eventlet
        # Use eventlet as fallback (may have issues on Python 3.11)
        eventlet.monkey_patch()
        async_mode = 'eventlet'
        print("Using eventlet for async mode")
    except ImportError:
        print("Neither gevent nor eventlet is available. Using threading mode.")
        async_mode = 'threading'

from flask import Flask, jsonify
from flask_socketio import SocketIO
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_key_for_websocket_secure_connection')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload size

# Initialize SocketIO with CORS allowed for the iOS app
socketio = SocketIO(app, cors_allowed_origins="*", async_mode=async_mode)

# Import and register API routes
from app.api.terminal_api import terminal_api
from app.api.files_api import files_api
from app.api.python_api import python_api
from app.api.maintenance_api import maintenance_api
# Re-enabled WebDAV API with fixed implementation
from app.api.webdav_api import webdav_api

app.register_blueprint(terminal_api)
app.register_blueprint(files_api)
app.register_blueprint(python_api)
app.register_blueprint(maintenance_api)
app.register_blueprint(webdav_api)

# Import and register WebSocket handlers
from app.api.terminal_ws import register_socket_events
from app.api.webdav_ws import register_webdav_socket_events
register_socket_events(socketio)
register_webdav_socket_events(socketio)

# Re-enabled WebDAV mounting with fixed implementation
from app.api.webdav_api import get_webdav_service
from app.services.webdav_service import mount_webdav_to_flask_app

# Mount WebDAV at /webdav endpoint
mount_webdav_to_flask_app(app, get_webdav_service())

# Create a root endpoint that shows API status and version
@app.route('/')
def index():
    return jsonify({
        'name': 'Termux Web API',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': [
            '/api/terminal/sessions',
            '/api/files',
            '/api/python/packages',
            '/api/python/venvs',
            '/api/python/run',
            '/api/maintenance/cleanup'
        ]
    })

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Use eventlet WSGI server for better WebSocket performance
    port = int(os.getenv('PORT', 5000))
    print(f"Starting Termux Web API server on port {port}")
    socketio.run(app, host='0.0.0.0', port=port)
