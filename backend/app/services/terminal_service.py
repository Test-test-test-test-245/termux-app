import threading
import time
import os
import shutil
import logging
from app.models.terminal_session import TerminalSession
from flask_socketio import emit

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TerminalService:
    """
    Service to manage terminal sessions.
    
    This service handles:
    - Creating and tracking terminal sessions
    - Routing input/output between WebSocket clients and terminal processes
    - Terminal session lifecycle management
    - Session isolation and resource cleanup
    """
    
    def __init__(self, inactive_timeout=3600):
        """
        Initialize the terminal service.
        
        Args:
            inactive_timeout (int): Time in seconds after which inactive sessions
                                   are cleaned up (default: 1 hour)
        """
        self.sessions = {}
        self.session_lock = threading.Lock()
        self.inactive_timeout = inactive_timeout
        
        # Create base directory for user sessions
        self.users_base_dir = "/app/storage/users"
        os.makedirs(self.users_base_dir, exist_ok=True)
        
        # Start background cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_inactive_sessions)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
        
        # Initial cleanup of any orphaned session directories
        self._cleanup_orphaned_session_directories()
    
    def create_session(self, shell, cwd, env, cols=80, rows=24):
        """
        Create a new terminal session with isolated environment.
        
        Args:
            shell (str): The shell program to run
            cwd (str): Current working directory
            env (dict): Environment variables
            cols (int): Number of columns
            rows (int): Number of rows
            
        Returns:
            TerminalSession: The created terminal session
        """
        try:
            # Create session with its own isolated environment
            session = TerminalSession(shell, cwd, env, cols, rows)
            
            # Register output callback to broadcast terminal output to WebSocket clients
            session.register_output_callback(self._broadcast_output)
            
            with self.session_lock:
                self.sessions[session.id] = session
            
            logger.info(f"Created new terminal session: {session.id}")
            return session
        except Exception as e:
            logger.error(f"Failed to create terminal session: {str(e)}")
            raise Exception(f"Failed to create terminal session: {str(e)}")
    
    def get_session(self, session_id):
        """
        Get a terminal session by ID.
        
        Args:
            session_id (str): The session ID
            
        Returns:
            TerminalSession or None: The terminal session if found, None otherwise
        """
        with self.session_lock:
            return self.sessions.get(session_id)
    
    def get_all_sessions(self):
        """
        Get all active terminal sessions.
        
        Returns:
            list: List of active terminal sessions
        """
        with self.session_lock:
            return list(self.sessions.values())
    
    def write_to_session(self, session_id, data):
        """
        Write data to a terminal session.
        
        Args:
            session_id (str): The session ID
            data (str): Data to write to the terminal
            
        Raises:
            Exception: If the session is not found or is inactive
        """
        session = self.get_session(session_id)
        if not session:
            raise Exception(f"Session not found: {session_id}")
        
        if not session.active:
            raise Exception(f"Session is no longer active: {session_id}")
        
        session.write(data)
    
    def resize_session(self, session_id, cols, rows):
        """
        Resize a terminal session.
        
        Args:
            session_id (str): The session ID
            cols (int): New number of columns
            rows (int): New number of rows
            
        Raises:
            Exception: If the session is not found or is inactive
        """
        session = self.get_session(session_id)
        if not session:
            raise Exception(f"Session not found: {session_id}")
        
        if not session.active:
            raise Exception(f"Session is no longer active: {session_id}")
        
        session.resize(cols, rows)
    
    def terminate_session(self, session_id, remove_files=False):
        """
        Terminate a terminal session and optionally remove all its files.
        
        Args:
            session_id (str): The session ID
            remove_files (bool): If True, remove all files associated with the session
            
        Raises:
            Exception: If the session is not found
        """
        session = self.get_session(session_id)
        if not session:
            raise Exception(f"Session not found: {session_id}")
        
        logger.info(f"Terminating session: {session_id} (remove_files={remove_files})")
        
        # Clean up the session and optionally remove files
        session.cleanup(remove_files=remove_files)
        
        # Remove the session from the sessions dictionary
        with self.session_lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                
        # Emit a terminated event to all clients subscribed to this session
        emit('terminated', {
            'session_id': session_id,
            'message': 'Session terminated'
        }, room=session_id, namespace='/')
    
    def _broadcast_output(self, session_id, output):
        """
        Broadcast terminal output to WebSocket clients subscribed to the session.
        
        Args:
            session_id (str): The session ID
            output (str): Terminal output data
        """
        # This will be called from the terminal session read thread
        # We use Flask-SocketIO's emit function with a "room" parameter to broadcast 
        # to only clients subscribed to this session
        emit('output', {
            'session_id': session_id,
            'data': output
        }, room=session_id, namespace='/')
    
    def _cleanup_inactive_sessions(self):
        """
        Background thread to periodically clean up inactive sessions.
        """
        while True:
            try:
                current_time = time.time()
                sessions_to_terminate = []
                
                with self.session_lock:
                    for session_id, session in self.sessions.items():
                        # If session is inactive for more than the timeout, add to cleanup list
                        if current_time - session.last_activity > self.inactive_timeout:
                            sessions_to_terminate.append(session_id)
                
                # Terminate sessions outside the lock to avoid deadlocks
                for session_id in sessions_to_terminate:
                    try:
                        logger.info(f"Cleaning up inactive session: {session_id}")
                        self.terminate_session(session_id, remove_files=True)
                    except Exception as e:
                        logger.error(f"Error terminating inactive session: {str(e)}")
                
                # Also check for orphaned session directories
                self._cleanup_orphaned_session_directories()
            
            except Exception as e:
                logger.error(f"Error in cleanup thread: {str(e)}")
            
            # Sleep for a minute before checking again
            time.sleep(60)
    
    def _cleanup_orphaned_session_directories(self):
        """
        Clean up any session directories that don't have corresponding active sessions.
        """
        try:
            # Skip if the base directory doesn't exist yet
            if not os.path.exists(self.users_base_dir):
                return
                
            active_session_ids = set()
            with self.session_lock:
                active_session_ids = set(self.sessions.keys())
            
            # List directories in the users base directory
            for dir_name in os.listdir(self.users_base_dir):
                dir_path = os.path.join(self.users_base_dir, dir_name)
                
                # If this is a directory and not in our active sessions, it's orphaned
                if os.path.isdir(dir_path) and dir_name not in active_session_ids:
                    try:
                        # Check if the directory is older than the inactive_timeout
                        dir_stat = os.stat(dir_path)
                        dir_age = time.time() - dir_stat.st_mtime
                        
                        if dir_age > self.inactive_timeout:
                            logger.info(f"Removing orphaned session directory: {dir_name}")
                            shutil.rmtree(dir_path)
                    except Exception as e:
                        logger.error(f"Error removing orphaned directory {dir_path}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error in cleanup_orphaned_session_directories: {str(e)}")
    
    def get_session_files(self, session_id, path=None):
        """
        Get a list of files in the session's files directory.
        
        Args:
            session_id (str): The session ID
            path (str): Optional sub-path within the user's files directory
            
        Returns:
            list: List of file information dictionaries
            
        Raises:
            Exception: If the session is not found
        """
        session = self.get_session(session_id)
        if not session:
            raise Exception(f"Session not found: {session_id}")
        
        # Default to the root of the user's files directory
        if path is None:
            target_path = session.user_files
        else:
            # Make sure the path is within the user's files directory
            target_path = os.path.join(session.user_files, path.lstrip('/'))
            if not os.path.abspath(target_path).startswith(os.path.abspath(session.user_files)):
                raise Exception("Invalid path")
        
        if not os.path.exists(target_path):
            raise Exception("Path does not exist")
        
        if not os.path.isdir(target_path):
            raise Exception("Path is not a directory")
        
        files = []
        for item in os.listdir(target_path):
            item_path = os.path.join(target_path, item)
            item_stat = os.stat(item_path)
            
            rel_path = os.path.relpath(item_path, session.user_files)
            if rel_path == '.':
                rel_path = ''
                
            files.append({
                'name': item,
                'path': rel_path,
                'is_dir': os.path.isdir(item_path),
                'size': item_stat.st_size,
                'modified': item_stat.st_mtime,
                'created': item_stat.st_ctime
            })
        
        return files
