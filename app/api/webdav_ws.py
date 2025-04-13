import os
import subprocess
import threading
import json
import logging
import time
from flask_socketio import emit, join_room, leave_room
from app.services.terminal_service import TerminalService
from app.services.webdav_service import WebDAVService
from app.api.webdav_api import get_webdav_service

# Get singleton instances
terminal_service = TerminalService()
webdav_service = get_webdav_service()

# Configure logging
logger = logging.getLogger(__name__)

def register_webdav_socket_events(socketio):
    """Register WebDAV testing WebSocket events."""
    
    @socketio.on('webdav_connect')
    def handle_webdav_connect():
        """Handle client connection for WebDAV testing."""
        emit('webdav_connected', {'status': 'connected'})
    
    @socketio.on('webdav_get_credentials')
    def handle_get_credentials(data):
        """Get or create WebDAV credentials for a session."""
        session_id = data.get('session_id')
        
        if not session_id:
            emit('webdav_error', {'message': 'Session ID is required'})
            return
        
        # Check if session exists
        session = terminal_service.get_session(session_id)
        if not session:
            emit('webdav_error', {'message': f'Session not found: {session_id}'})
            return
        
        # Get or create credentials
        credentials = webdav_service.add_session(session_id)
        
        if not credentials:
            emit('webdav_error', {'message': 'Failed to create WebDAV credentials'})
            return
        
        # Get base URL dynamically
        host = data.get('host', 'localhost')
        scheme = data.get('scheme', 'http')
        base_url = f"{scheme}://{host}"
        
        # Update the URL in credentials if host provided
        if 'host' in data:
            credentials['url'] = f"{base_url}/webdav"
        
        emit('webdav_credentials', {
            'session_id': session_id,
            'credentials': credentials
        })
    
    @socketio.on('webdav_test_connection')
    def handle_test_connection(data):
        """Test WebDAV connection by checking credentials and access."""
        session_id = data.get('session_id')
        
        if not session_id:
            emit('webdav_error', {'message': 'Session ID is required'})
            return
        
        # Check if credentials exist for this session
        has_credentials = session_id in webdav_service.credentials
        
        if not has_credentials:
            emit('webdav_error', {'message': 'WebDAV not enabled for this session'})
            return
        
        # Check if session exists
        session = terminal_service.get_session(session_id)
        if not session:
            emit('webdav_error', {'message': f'Session not found: {session_id}'})
            return
        
        # Test that files directory exists
        if not os.path.exists(session.user_files):
            emit('webdav_test_result', {
                'status': 'error',
                'message': 'Files directory does not exist',
                'user_files_path': session.user_files
            })
            return
        
        # Return success with path information
        emit('webdav_test_result', {
            'status': 'success',
            'message': 'WebDAV connection is ready',
            'user_files_path': session.user_files,
            'files_count': len(os.listdir(session.user_files))
        })
    
    @socketio.on('webdav_list_files')
    def handle_list_files(data):
        """List files in the WebDAV directory."""
        session_id = data.get('session_id')
        path = data.get('path', '')
        
        if not session_id:
            emit('webdav_error', {'message': 'Session ID is required'})
            return
        
        try:
            files = terminal_service.get_session_files(session_id, path)
            emit('webdav_files_list', {
                'session_id': session_id,
                'path': path,
                'files': files
            })
        except Exception as e:
            emit('webdav_error', {'message': str(e)})
    
    @socketio.on('execute_command')
    def handle_execute_command(data):
        """Execute a shell command and stream output."""
        session_id = data.get('session_id')
        command = data.get('command')
        
        if not session_id or not command:
            emit('webdav_error', {'message': 'Session ID and command are required'})
            return
        
        # Check if session exists
        session = terminal_service.get_session(session_id)
        if not session:
            emit('webdav_error', {'message': f'Session not found: {session_id}'})
            return
        
        # Create a unique room for this command
        command_id = f"{session_id}_{int(time.time())}"
        join_room(command_id)
        
        # Start command in a separate thread
        thread = threading.Thread(
            target=_execute_command_thread, 
            args=(command_id, session, command)
        )
        thread.daemon = True
        thread.start()
        
        emit('command_started', {
            'command_id': command_id,
            'session_id': session_id,
            'command': command
        })
    
    @socketio.on('webdav_create_test_file')
    def handle_create_test_file(data):
        """Create a test file in the WebDAV directory."""
        session_id = data.get('session_id')
        filename = data.get('filename', f'test_file_{int(time.time())}.txt')
        content = data.get('content', 'This is a test file created via WebSocket.')
        
        if not session_id:
            emit('webdav_error', {'message': 'Session ID is required'})
            return
        
        # Check if session exists
        session = terminal_service.get_session(session_id)
        if not session:
            emit('webdav_error', {'message': f'Session not found: {session_id}'})
            return
        
        try:
            # Create file in the user files directory
            file_path = os.path.join(session.user_files, filename)
            
            # Make sure the file path is within the user files directory
            if not os.path.abspath(file_path).startswith(os.path.abspath(session.user_files)):
                emit('webdav_error', {'message': 'Invalid file path'})
                return
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            emit('webdav_file_created', {
                'session_id': session_id,
                'filename': filename,
                'path': file_path,
                'size': len(content)
            })
        except Exception as e:
            emit('webdav_error', {'message': f'Error creating file: {str(e)}'})

def _execute_command_thread(command_id, session, command):
    """Execute a command in a separate thread and stream output."""
    try:
        # Change to the user's files directory
        cwd = session.user_files
        
        # Create the process
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            text=True,
            bufsize=1
        )
        
        # Read output and emit events
        for line in iter(process.stdout.readline, ''):
            emit('command_output', {
                'command_id': command_id,
                'output': line
            }, room=command_id)
        
        # Wait for process to complete
        exit_code = process.wait()
        
        # Send completion event
        emit('command_completed', {
            'command_id': command_id,
            'exit_code': exit_code
        }, room=command_id)
        
    except Exception as e:
        logger.error(f"Error executing command: {str(e)}")
        emit('command_error', {
            'command_id': command_id,
            'error': str(e)
        }, room=command_id)
