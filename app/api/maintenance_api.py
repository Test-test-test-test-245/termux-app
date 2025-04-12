from flask import Blueprint, jsonify
from app.services.terminal_service import TerminalService

maintenance_api = Blueprint('maintenance_api', __name__, url_prefix='/api/maintenance')
terminal_service = TerminalService()

@maintenance_api.route('/cleanup', methods=['POST'])
def cleanup_sessions():
    """
    Endpoint to clean up inactive sessions and orphaned directories.
    This can be called by a CRON job or manually.
    """
    # Do a manual cleanup cycle
    current_service = TerminalService()
    
    # Clean up inactive sessions
    inactive_count = current_service.cleanup_inactive_sessions()
    
    # Clean up orphaned directories
    orphaned_count = current_service.cleanup_orphaned_directories()
    
    return jsonify({
        'status': 'success', 
        'message': 'Cleanup completed',
        'inactive_sessions_cleaned': inactive_count,
        'orphaned_directories_cleaned': orphaned_count
    })
