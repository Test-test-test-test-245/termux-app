from flask import Blueprint, request, jsonify
from app.services.terminal_service import TerminalService
import os

terminal_api = Blueprint('terminal_api', __name__, url_prefix='/api/terminal')
terminal_service = TerminalService()

@terminal_api.route('/sessions', methods=['GET'])
def list_sessions():
    """List all active terminal sessions"""
    sessions = terminal_service.get_all_sessions()
    return jsonify({
        'sessions': [session.to_dict() for session in sessions]
    })

@terminal_api.route('/sessions', methods=['POST'])
def create_session():
    """Create a new terminal session"""
    data = request.json or {}
    shell = data.get('shell', os.environ.get('SHELL', '/bin/bash'))
    cols = data.get('cols', 80)
    rows = data.get('rows', 24)
    cwd = data.get('cwd', os.environ.get('HOME', '/'))
    env = data.get('env', {})
    
    # Merge with current environment
    environment = os.environ.copy()
    environment.update(env)
    
    try:
        session = terminal_service.create_session(
            shell=shell,
            cwd=cwd,
            env=environment,
            cols=cols,
            rows=rows
        )
        return jsonify(session.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@terminal_api.route('/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get information about a specific terminal session"""
    session = terminal_service.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    return jsonify(session.to_dict())

@terminal_api.route('/sessions/<session_id>/size', methods=['POST'])
def resize_session(session_id):
    """Resize a terminal session"""
    data = request.json or {}
    cols = data.get('cols')
    rows = data.get('rows')
    
    if not cols or not rows:
        return jsonify({'error': 'Both cols and rows are required'}), 400
    
    try:
        terminal_service.resize_session(session_id, cols, rows)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@terminal_api.route('/sessions/<session_id>', methods=['DELETE'])
def terminate_session(session_id):
    """Terminate a terminal session"""
    try:
        terminal_service.terminate_session(session_id)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
