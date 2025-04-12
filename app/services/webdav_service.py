import os
import logging
from wsgidav.wsgidav_app import WsgiDAVApp
from wsgidav.fs_provider import FilesystemProvider  # Updated from fs_dav_provider
from wsgidav.dav_provider import DAVProvider
from wsgidav.dav_error import DAVError
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from flask import Flask, request, Response

# Configure logging
logger = logging.getLogger(__name__)

class WebDAVService:
    """
    Service to manage WebDAV access to user session files.
    
    This service provides:
    - WebDAV server integration with Flask
    - Authentication per session
    - Mapping each session to its own directory
    """
    
    def __init__(self, terminal_service):
        """
        Initialize the WebDAV service.
        
        Args:
            terminal_service: The terminal service instance to get sessions from
        """
        self.terminal_service = terminal_service
        self.running = False
        
        # Dictionary to store session credentials
        # {session_id: {"username": session_id, "password_hash": hashed_password}}
        self.credentials = {}
        
        # Dictionary to store session-specific random passwords
        # {session_id: cleartext_password} - only kept for returning to the user
        self.session_passwords = {}
        
        # Create the WebDAV WSGI app
        self.webdav_app = self._create_webdav_app()
        
        # Mark as running since we're integrating with Flask
        self.running = True
    
    def start(self):
        """
        Initialize the WebDAV integration.
        This method exists for compatibility with the original API.
        """
        logger.info("WebDAV service initialized and ready")
    
    def stop(self):
        """
        Stop the WebDAV service.
        This method exists for compatibility with the original API.
        """
        self.running = False
        logger.info("WebDAV service stopped")
    
    def _create_webdav_app(self):
        """Create the WebDAV WSGI application."""
        # Configure the WebDAV application
        config = {
            "provider_mapping": {
                # The root path will be mapped dynamically based on session
                "/": self._create_root_provider(),
            },
            "http_authenticator": {
                "domain_controller": self,  # This class implements domain_controller methods
                "accept_basic": True,
                "accept_digest": False,
                "default_to_digest": False,
            },
            "simple_dc": {
                "user_mapping": {},  # We'll handle auth in get_domain_controller
            },
            "verbose": 2,
            "logging": {
                "enable_loggers": []  # Updated from deprecated enable_loggers
            },
            "property_manager": True,  # True: use property_manager.PropertyManager
            "lock_storage": True,  # Updated from deprecated lock_manager
        }
        
        return WsgiDAVApp(config)
    
    def get_wsgi_app(self):
        """
        Get the WSGI application for WebDAV.
        This can be mounted to a specific URL path in Flask.
        """
        return self.webdav_app
    
    def _create_root_provider(self):
        """
        Create a dynamic provider that maps paths to user directories.
        
        This provider intercepts requests and routes them to the correct
        user's directory based on authentication.
        """
        from wsgidav.dav_provider import DAVProvider
        from wsgidav.fs_provider import FilesystemProvider
        from wsgidav.dav_error import DAVError
        from wsgidav.util import join_uri
        
        # Create a proper DAV provider by extending DAVProvider
        class SessionAwareProvider(DAVProvider):
            def __init__(self, terminal_service):
                super().__init__()
                self.terminal_service = terminal_service
                # Cache of providers for each session
                self.session_providers = {}
            
            def get_resource_inst(self, path, environ):
                # Extract session_id from authentication
                auth_user = environ.get("wsgidav.auth.user_name")
                
                if not auth_user:
                    logger.warning("WebDAV access without authentication")
                    return None
                
                # Get or create provider for this session
                provider = self._get_session_provider(auth_user, environ)
                if not provider:
                    return None
                
                # Use the session's provider to get the resource
                return provider.get_resource_inst(path, environ)
            
            def _get_session_provider(self, session_id, environ):
                """Get or create a provider for a session."""
                # Check if we already have a provider for this session
                if session_id in self.session_providers:
                    return self.session_providers[session_id]
                
                # Get the session to find user_files directory
                session = self.terminal_service.get_session(session_id)
                if not session:
                    logger.warning(f"WebDAV access for unknown session: {session_id}")
                    return None
                
                # Create a new provider for this session
                try:
                    user_files_dir = session.user_files
                    logger.info(f"Creating WebDAV provider for session {session_id} in {user_files_dir}")
                    provider = FilesystemProvider(user_files_dir)
                    # Cache the provider
                    self.session_providers[session_id] = provider
                    return provider
                except Exception as e:
                    logger.error(f"Error creating provider for session {session_id}: {str(e)}")
                    return None
            
            # Required DAVProvider methods that delegate to the session provider
            def is_collection(self, path, environ):
                provider = self._get_provider_for_request(environ)
                return provider.is_collection(path, environ) if provider else False
            
            def is_readonly(self):
                return False
            
            def _get_provider_for_request(self, environ):
                """Helper to get the appropriate provider for the current request."""
                auth_user = environ.get("wsgidav.auth.user_name")
                if not auth_user:
                    return None
                return self._get_session_provider(auth_user, environ)
        
        return SessionAwareProvider(self.terminal_service)
    
    # Domain controller methods for authentication
    
    def get_domain_realm(self, path_info, environ):
        """Return realm name for given URL."""
        return "TermuxWebTerminal"
    
    def require_authentication(self, realm, environ):
        """Return True if authentication is required for this resource."""
        return True
    
    def is_realm_user(self, realm, user_name, environ):
        """Check if user has access to realm."""
        return user_name in self.credentials
    
    def get_realm_user_password(self, realm, user_name, environ):
        """Return the stored password for the user name (plaintext)."""
        # We don't store or return plaintext passwords
        return None
    
    def auth_domain_user(self, realm, user_name, password, environ):
        """Return True if user has access to realm with given password."""
        if user_name not in self.credentials:
            return False
        
        # Check password using werkzeug's secure password checking
        return check_password_hash(self.credentials[user_name]["password_hash"], password)
    
    # Session credential management
    
    def add_session(self, session_id):
        """
        Add a session and generate credentials for WebDAV access.
        
        Args:
            session_id (str): The session ID to add
            
        Returns:
            dict: WebDAV access information (url, username, password)
        """
        if session_id in self.credentials:
            # Return existing credentials if already registered
            return self._get_credentials_info(session_id)
        
        # Generate a random password for this session
        import secrets
        password = secrets.token_urlsafe(12)
        
        # Store the password hash
        self.credentials[session_id] = {
            "username": session_id,
            "password_hash": generate_password_hash(password)
        }
        
        # Store the cleartext password temporarily for returning to the user
        self.session_passwords[session_id] = password
        
        logger.info(f"Added WebDAV credentials for session: {session_id}")
        
        return self._get_credentials_info(session_id)
    
    def remove_session(self, session_id):
        """
        Remove a session's WebDAV access.
        
        Args:
            session_id (str): The session ID to remove
        """
        if session_id in self.credentials:
            del self.credentials[session_id]
        
        if session_id in self.session_passwords:
            del self.session_passwords[session_id]
        
        logger.info(f"Removed WebDAV credentials for session: {session_id}")
    
    def _get_credentials_info(self, session_id):
        """
        Get WebDAV access information for a session.
        
        Args:
            session_id (str): The session ID
            
        Returns:
            dict: WebDAV access information (url, username, password)
        """
        if session_id not in self.credentials or session_id not in self.session_passwords:
            return None
        
        # Get base URL from environment variable or use the request host
        # We need a publicly accessible URL for WebDAV
        base_url = os.environ.get('WEBDAV_BASE_URL', '')
        
        # If no base URL set, try to determine from request
        if not base_url:
            if request:
                host = request.headers.get('Host', request.host)
                scheme = request.environ.get('wsgi.url_scheme', 'http')
                base_url = f"{scheme}://{host}"
        
        # Construct WebDAV url at the /webdav endpoint
        webdav_url = f"{base_url}/webdav" if base_url else "/webdav"
        
        return {
            "url": webdav_url,
            "username": session_id,
            "password": self.session_passwords[session_id],
            "protocol": "WebDAV"
        }

# Function to integrate WebDAV with a Flask application
def mount_webdav_to_flask_app(app, webdav_service, mount_path='/webdav'):
    """
    Mount the WebDAV service to a Flask application at the specified path.
    
    Args:
        app: The Flask application instance
        webdav_service: The WebDAVService instance
        mount_path: The URL path to mount WebDAV on
    """
    # Create a dispatcher middleware that routes requests to either Flask or WebDAV
    webdav_wsgi_app = webdav_service.get_wsgi_app()
    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {mount_path: webdav_wsgi_app})
    
    logger.info(f"WebDAV mounted at {mount_path}")
