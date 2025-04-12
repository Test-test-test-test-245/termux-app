# This file ensures the app package is recognized as a Python package

from flask import Flask
from flask_socketio import SocketIO

# Initialize variables to be set in the app.py
socketio = None