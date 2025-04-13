import os
import logging
import json
import time
from wsgidav.wsgidav_app import WsgiDAVApp
from wsgidav.fs_dav_provider import FilesystemProvider

# Import compatibility layer to handle different wsgidav versions
try:
    # Try newer module structure
    from wsgidav.dav_provider import DAVProvider
    from wsgidav.dav_error import DAVError
    from wsgidav.dc.base_dc import BaseDomainController
except ImportError:
    # Fall back to older module structure
    logger = logging.getLogger(__name__)
    logger.info("Using older WsgiDAV module structure")
    # In older versions, these may be directly in wsgidav module
    from wsgidav import DAVProvider
    from wsgidav import DAVError
    try:
        from wsgidav.domaincontroller import BaseDomainController
    except ImportError:
        # For very old versions
        from wsgidav.domaincontroller import AbstractDomainController as BaseDomainController

from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from flask import Flask, request, Response

# Configure logging
logger = logging.getLogger(__name__)

# Global variable to hold reference to the WebDAVService instance
# This is needed to access credentials from the domain controller
_webdav_service_instance = None

# Create a proper domain controller class that inherits from BaseDomainController
# and accepts wsgidav_app and config as required by the library
class TermuxDomainController(BaseDomainController):
    """Custom domain controller for WebDAV authentication."""
    
    def __init__(self, wsgidav_app, config):
        super().__init__()
        # We can't pass the webdav_service directly due to circular deps,
        # so we access it through the global variable
        global _webdav_service_instance
        self.webdav_service = _webdav_service_instance
        logger.info("TermuxDomainController initialized")
    
    def get_domain_realm(self, path_info, environ):
        """Return realm name for given URL."""
        return "TermuxWebTerminal"
    
    def require_authentication(self, realm, environ):
        """Return True if authentication is required for this resource."""
        return True
    
    def is_realm_user(self, realm, user_name, environ):
        """Check if user has access to realm."""
        if not self.webdav_service or not hasattr(self.webdav_service, 'credentials'):
            logger.error("WebDAV service not available in domain controller")
            return False
        return user_name in self.webdav_service.credentials
    
    def get_realm_user_password(self, realm, user_name, environ):
        """Return the stored password for the user name (plaintext)."""
        # We don't store or return plaintext passwords
        return None
    
    def auth_domain_user(self, realm, user_name, password, environ):
        """Return True if user has access to realm with given password."""
        if not self.webdav_service or not hasattr(self.webdav_service, 'credentials'):
            logger.error("WebDAV service not available in domain controller")
            return False
            
        if user_name not in self.webdav_service.credentials:
            return False
        
        # Check password using werkzeug's secure password checking
        return check_password_hash(self.webdav_service.credentials[user_name]["password_hash"], password)
        
    # Additional methods required by the WsgiDAV interface
    def basic_auth_user(self, realm, user_name, password, environ):
        """
        Check basic authentication for user_name, password, and realm.
        (This method is for HTTP basic authentication, which is what we use)
        """
        return self.auth_domain_user(realm, user_name, password, environ)
        
    def supports_http_digest_auth(self):
        """
        Return True if digest authentication is enabled.
        We only use basic auth so this should return False.
        """
        return False

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
        # Set the global reference so the domain controller can access it
        global _webdav_service_instance
        _webdav_service_instance = self
        
        # Configure the WebDAV application
        config = {
            "provider_mapping": {
                # The root path will be mapped dynamically based on session
                "/": self._create_root_provider(),
            },
            "http_authenticator": {
                "domain_controller": TermuxDomainController,  # Pass the CLASS, not an instance
                "accept_basic": True,
                "accept_digest": False,
                "default_to_digest": False,
            },
            "simple_dc": {
                "user_mapping": {},  # We'll handle auth in domain_controller
            },
            "verbose": 2,
            "logging": {
                "enable_loggers": []  # Updated from deprecated enable_loggers
            },
            "property_manager": True,  # True: use property_manager.PropertyManager
            "lock_storage": True,  # Updated from deprecated lock_manager
        }
        
        logger.info("Creating WebDAV app with TermuxDomainController class")
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
        terminal_service = self.terminal_service
        
        # Define the SessionAwareProvider as a proper DAVProvider subclass
        class SessionAwareProvider(DAVProvider):
            """
            A DAV provider that maps to different session directories 
            based on the authenticated user.
            """
            
            def __init__(self):
                super(SessionAwareProvider, self).__init__()
                self.terminal_service = terminal_service
                # Cache of session providers to improve performance
                self.session_providers = {}
                # Last cleanup time for cache
                self.last_cleanup = time.time()
            
            def get_resource_inst(self, path, environ):
                """Return a DAVResource object for the path.
                
                This is the main entry point for the provider.
                """
                # Extract session ID from the authentication credentials
                session_id = environ.get("wsgidav.auth.user_name")
                if not session_id:
                    logger.warning("WebDAV access attempt without credentials")
                    return None
                
                # Get the provider for this session
                file_provider = self._get_provider_for_session(session_id)
                if not file_provider:
                    logger.warning(f"No provider found for session: {session_id}")
                    return None
                
                # Delegate to the session's file provider
                return file_provider.get_resource_inst(path, environ)
            
            def _get_provider_for_session(self, session_id):
                """Get or create a file provider for the given session ID."""
                # Check if we already have a provider for this session
                if session_id in self.session_providers:
                    return self.session_providers[session_id]
                
                # Periodic cleanup of old providers
                self._cleanup_old_providers()
                
                # Get the session from the terminal service
                session = self.terminal_service.get_session(session_id)
                if not session:
                    logger.warning(f"Session not found: {session_id}")
                    return None
                
                # Get the session's file directory
                try:
                    user_files_dir = session.user_files
                    if not os.path.exists(user_files_dir):
                        logger.warning(f"Files directory does not exist: {user_files_dir}")
                        os.makedirs(user_files_dir, exist_ok=True)
                    
                    # Create a new file provider for this session
                    logger.info(f"Creating file provider for session {session_id} in {user_files_dir}")
                    provider = FilesystemProvider(user_files_dir)
                    
                    # Store in cache
                    self.session_providers[session_id] = provider
                    return provider
                except Exception as e:
                    logger.error(f"Error creating provider for session {session_id}: {str(e)}")
                    return None
            
            def _cleanup_old_providers(self):
                """Clean up providers for sessions that no longer exist."""
                # Only clean up every 5 minutes to avoid excessive checking
                current_time = time.time()
                if current_time - self.last_cleanup < 300:  # 5 minutes in seconds
                    return
                
                self.last_cleanup = current_time
                expired_sessions = []
                
                # Find sessions that no longer exist
                for session_id in list(self.session_providers.keys()):
                    if not self.terminal_service.get_session(session_id):
                        expired_sessions.append(session_id)
                
                # Remove expired sessions from cache
                for session_id in expired_sessions:
                    logger.info(f"Removing provider for expired session: {session_id}")
                    del self.session_providers[session_id]
            
            # Required DAVProvider methods
            def get_resource_inst_by_href(self, href, environ):
                """Get a resource by its href."""
                # WsgiDAV calls get_resource_inst, so we don't need to implement this
                return None
            
            def is_readonly(self):
                """Return True if provider is read-only."""
                return False
            
            def is_collection(self, path, environ):
                """Check if path maps to a collection."""
                # This won't be called directly since we delegate to FilesystemProvider
                return False
            
            def custom_request_handler(self, environ, start_response, path):
                """Handle custom requests."""
                # We don't handle custom requests
                return False
            
            def get_ref_url(self, path):
                """Return the URL of a resource, based on its path."""
                # We delegate all resource handling to the file provider
                return None
            
            def set_ref_url(self, path, ref_url):
                """Set the URL of a resource."""
                # We don't support this operation
                pass
            
            def set_props_for_principal(self, principal, propsdef):
                """Set property for a principal."""
                # We don't support direct property setting
                pass
        
        # Return an instance of the SessionAwareProvider
        return SessionAwareProvider()
    
    # We've moved domain controller methods to the TermuxDomainController class
    
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
