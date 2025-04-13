from flask import Blueprint, request, jsonify, current_app
from app.services.terminal_service import TerminalService
from app.services.webdav_service import WebDAVService

webdav_api = Blueprint('webdav_api', __name__, url_prefix='/api/webdav')

# Get singleton instances
terminal_service = TerminalService()

# Initialize WebDAV service as a global variable 
# The actual mounting happens in flask_app.py
webdav_service = WebDAVService(terminal_service)

@webdav_api.route('/info', methods=['GET'])
def webdav_info():
    """Get information about WebDAV server status"""
    # Get base URL from request
    host = request.headers.get('Host', request.host)
    scheme = request.environ.get('wsgi.url_scheme', 'http')
    base_url = f"{scheme}://{host}"
    
    return jsonify({
        'status': 'running' if webdav_service.running else 'stopped',
        'webdav_url': f"{base_url}/webdav",
        'mount_path': '/webdav'
    })

@webdav_api.route('/credentials', methods=['GET'])
def get_credentials():
    """Get WebDAV credentials for a specific session"""
    session_id = request.args.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'Session ID is required'}), 400
    
    # Check if session exists
    session = terminal_service.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    # Get or create credentials for this session
    credentials = webdav_service.add_session(session_id)
    
    if not credentials:
        return jsonify({'error': 'Failed to create WebDAV credentials'}), 500
    
    return jsonify({
        'credentials': credentials,
        'instructions': [
            "To access your files via WebDAV:",
            "1. Use a WebDAV client (like Cyberduck, WinSCP, or built-in OS support)",
            "2. Connect to the URL with the provided username and password",
            "3. Files are available at the root of the WebDAV connection",
            "4. Any changes you make will be immediately visible in your terminal session"
        ],
        'clients': {
            'windows': [
                "Windows Explorer: Map Network Drive > Connect to a website > Next > " + 
                "Enter the URL > Next > Enter your credentials",
                "Or use WinSCP, FileZilla, or other WebDAV clients"
            ],
            'macos': [
                "Finder: Go > Connect to Server > Enter the URL > Connect > Enter your credentials",
                "Or use Cyberduck, FileZilla, or other WebDAV clients"
            ],
            'ios': [
                "Files app: Browse > Three dots > Connect to Server > Enter the URL and credentials",
                "Or use Documents by Readdle, FileBrowser, or other WebDAV-compatible apps"
            ],
            'android': [
                "Use Solid Explorer, FX File Explorer, or other WebDAV-compatible apps"
            ]
        }
    })

@webdav_api.route('/disable', methods=['POST'])
def disable_webdav():
    """Disable WebDAV access for a session"""
    session_id = request.json.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'Session ID is required'}), 400
    
    # Check if session exists
    session = terminal_service.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    # Remove credentials for this session
    webdav_service.remove_session(session_id)
    
    return jsonify({
        'status': 'success',
        'message': 'WebDAV access disabled for this session'
    })

@webdav_api.route('/status', methods=['GET'])
def get_status():
    """Check if WebDAV is enabled for a session"""
    session_id = request.args.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'Session ID is required'}), 400
    
    # Check if credentials exist for this session
    has_credentials = session_id in webdav_service.credentials
    
    return jsonify({
        'session_id': session_id,
        'webdav_enabled': has_credentials
    })

# Make webdav_service available to other modules
def get_webdav_service():
    """Get the singleton WebDAV service instance."""
    return webdav_service
