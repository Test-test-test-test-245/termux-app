#!/usr/bin/env python3

import os
import eventlet
# Use eventlet for better WebSocket performance with Flask-SocketIO
eventlet.monkey_patch()

from flask import Flask
from flask_socketio import SocketIO
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_key_for_websocket_secure_connection')

# Initialize SocketIO with CORS allowed for the iOS app
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Import and register API routes
from app.api.terminal_api import terminal_api
app.register_blueprint(terminal_api)

# Import and register WebSocket handlers
from app.api.terminal_ws import register_socket_events
register_socket_events(socketio)

if __name__ == '__main__':
    # Use eventlet WSGI server for better WebSocket performance
    port = int(os.getenv('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)