import threading
import time
from app.models.terminal_session import TerminalSession
from flask_socketio import emit

class TerminalService:
    """
    Service to manage terminal sessions.
    
    This service handles:
    - Creating and tracking terminal sessions
    - Routing input/output between WebSocket clients and terminal processes
    - Terminal session lifecycle management
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
        
        # Start background cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_inactive_sessions)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
    
    def create_session(self, shell, cwd, env, cols=80, rows=24):
        """
        Create a new terminal session.
        
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
            session = TerminalSession(shell, cwd, env, cols, rows)
            
            # Register output callback to broadcast terminal output to WebSocket clients
            session.register_output_callback(self._broadcast_output)
            
            with self.session_lock:
                self.sessions[session.id] = session
            
            return session
        except Exception as e:
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
    
    def terminate_session(self, session_id):
        """
        Terminate a terminal session.
        
        Args:
            session_id (str): The session ID
            
        Raises:
            Exception: If the session is not found
        """
        session = self.get_session(session_id)
        if not session:
            raise Exception(f"Session not found: {session_id}")
        
        session.terminate()
        
        # Remove the session from the sessions dictionary
        with self.session_lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
    
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
                        self.terminate_session(session_id)
                        print(f"Terminated inactive session: {session_id}")
                    except Exception as e:
                        print(f"Error terminating inactive session: {str(e)}")
            
            except Exception as e:
                print(f"Error in cleanup thread: {str(e)}")
            
            # Sleep for a minute before checking again
            time.sleep(60)
