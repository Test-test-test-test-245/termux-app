import os
import time
import uuid
import ptyprocess
import threading
import pyte
from collections import deque
import json

class TerminalSession:
    """
    Represents a terminal session with a PTY process and terminal emulator.
    This class manages the process lifecycle and maintains the terminal state.
    """
    
    def __init__(self, shell, cwd, env, cols=80, rows=24, buffer_size=10000):
        """
        Initialize a new terminal session.
        
        Args:
            shell (str): The shell program to run (e.g., /bin/bash)
            cwd (str): Current working directory to start the shell in
            env (dict): Environment variables for the shell
            cols (int): Number of columns in the terminal
            rows (int): Number of rows in the terminal
            buffer_size (int): Maximum size of output buffer in lines
        """
        self.id = str(uuid.uuid4())
        self.shell = shell
        self.cwd = cwd
        self.cols = cols
        self.rows = rows
        self.created_at = time.time()
        self.last_activity = time.time()
        self.buffer_size = buffer_size
        
        # Configure environment properly for full terminal experience
        self.env = env.copy() if env else os.environ.copy()
        
        # Set HOME to the persistent storage location for user files
        home_dir = os.environ.get('HOME_DIR', '/app/storage/home')
        self.env['HOME'] = home_dir
        
        # Ensure proper terminal settings
        if 'TERM' not in self.env:
            self.env['TERM'] = 'xterm-256color'
        
        # Configure editor environment variables
        self.env['EDITOR'] = 'nano'  # Default editor
        self.env['VISUAL'] = 'nano'  # Default visual editor
        
        # Ensure proper PATH environment
        if 'PATH' not in self.env:
            self.env['PATH'] = '/usr/local/bin:/usr/bin:/bin'
        if '/app/storage/user_files' not in self.env['PATH']:
            self.env['PATH'] = f"{self.env['PATH']}:/app/storage/user_files"
            
        # Create output buffer with deque for efficient append and trim operations
        self.output_buffer = deque(maxlen=buffer_size)
        
        # Set up terminal emulator
        self.screen = pyte.Screen(cols, rows)
        self.stream = pyte.Stream()
        self.stream.attach(self.screen)
        
        # Create a custom shell RC file if it doesn't exist
        self._ensure_shell_rc_exists(home_dir)
        
        # Start the PTY process
        self.pty = ptyprocess.PtyProcess.spawn(
            argv=[shell],
            cwd=cwd,
            env=self.env
        )
        
        # Flag to indicate if the session is active
        self.active = True
        
        # Set up reading thread
        self.read_thread = threading.Thread(target=self._read_pty_output)
        self.read_thread.daemon = True
        self.read_thread.start()
        
        # List of callbacks to call when output is received
        self.output_callbacks = []
    
    def _ensure_shell_rc_exists(self, home_dir):
        """Ensure shell RC file exists with proper configuration for editors"""
        os.makedirs(home_dir, exist_ok=True)
        
        # Create a basic .bashrc if it doesn't exist
        bashrc_path = os.path.join(home_dir, '.bashrc')
        if not os.path.exists(bashrc_path):
            with open(bashrc_path, 'w') as f:
                f.write('''
# Terminal configuration for Termux Web
export PS1="\\[\\033[01;32m\\]\\u@termux-web\\[\\033[00m\\]:\\[\\033[01;34m\\]\\w\\[\\033[00m\\]\\$ "

# Editor configurations
export EDITOR=nano
export VISUAL=nano

# Aliases
alias ll="ls -la"
alias python=python3

# Path configuration
export PATH=$PATH:/app/storage/user_files

# Welcome message
echo "Welcome to Termux Web Terminal!"
echo "Use 'nano filename.py' to create or edit Python files."
echo "Type 'pip install packagename' to install Python packages."
''')
            os.chmod(bashrc_path, 0o755)
        
        # Create empty .bash_history
        history_path = os.path.join(home_dir, '.bash_history')
        if not os.path.exists(history_path):
            open(history_path, 'w').close()
            os.chmod(history_path, 0o644)
            
        # Add .vimrc with basic configuration
        vimrc_path = os.path.join(home_dir, '.vimrc')
        if not os.path.exists(vimrc_path):
            with open(vimrc_path, 'w') as f:
                f.write('''
syntax on
set autoindent
set expandtab
set number
set tabstop=4
set shiftwidth=4
set softtabstop=4
set background=dark
colorscheme default
''')
    
    def _read_pty_output(self):
        """
        Read output from the PTY and process it through the terminal emulator.
        This runs in a separate thread.
        """
        try:
            while self.active:
                try:
                    # Read up to 1024 bytes from the PTY
                    data = self.pty.read(1024)
                    if not data:
                        break
                    
                    # Update last activity timestamp
                    self.last_activity = time.time()
                    
                    # Feed data to the terminal emulator
                    self.stream.feed(data.decode('utf-8', errors='replace'))
                    
                    # Store the current display in the buffer
                    self.update_buffer()
                    
                    # Call output callbacks
                    for callback in self.output_callbacks:
                        try:
                            callback(self.id, data.decode('utf-8', errors='replace'))
                        except Exception as e:
                            print(f"Error in output callback: {e}")
                            
                except (EOFError, OSError):
                    break
        finally:
            if self.active:
                self.terminate()
    
    def update_buffer(self):
        """Update the output buffer with the current screen state"""
        # Get the display from the screen
        display = []
        for line in range(self.rows):
            line_data = self.screen.display[line]
            display.append(line_data)
        
        # Add to the buffer
        self.output_buffer.append('\n'.join(display))
    
    def write(self, data):
        """
        Write data to the PTY.
        
        Args:
            data (str): Data to write to the PTY
        """
        if not self.active:
            raise Exception("Session is no longer active")
        
        self.last_activity = time.time()
        self.pty.write(data.encode('utf-8'))
    
    def resize(self, cols, rows):
        """
        Resize the PTY.
        
        Args:
            cols (int): New number of columns
            rows (int): New number of rows
        """
        if not self.active:
            raise Exception("Session is no longer active")
        
        self.cols = cols
        self.rows = rows
        self.pty.setwinsize(rows, cols)
        
        # Resize the terminal emulator
        self.screen.resize(lines=rows, columns=cols)
    
    def terminate(self):
        """Terminate the session and clean up resources."""
        if self.active:
            self.active = False
            try:
                self.pty.terminate(force=True)
            except:
                pass
            
            # Wait for the read thread to exit
            if self.read_thread.is_alive():
                self.read_thread.join(timeout=1.0)
    
    def register_output_callback(self, callback):
        """
        Register a callback to be called when output is received.
        
        Args:
            callback (callable): A function that will be called with 
                                (session_id, output_data) as arguments
        """
        self.output_callbacks.append(callback)
    
    def unregister_output_callback(self, callback):
        """
        Unregister a previously registered output callback.
        
        Args:
            callback (callable): The callback to unregister
        """
        if callback in self.output_callbacks:
            self.output_callbacks.remove(callback)
    
    def get_buffer(self, max_lines=None):
        """
        Get the terminal output buffer.
        
        Args:
            max_lines (int, optional): Maximum number of lines to return
                                      (from the end of the buffer)
        
        Returns:
            list: List of buffer lines
        """
        buffer_list = list(self.output_buffer)
        if max_lines is not None and max_lines < len(buffer_list):
            return buffer_list[-max_lines:]
        return buffer_list
    
    def to_dict(self):
        """
        Convert session to a dictionary representation.
        
        Returns:
            dict: Dictionary representation of the terminal session
        """
        return {
            'id': self.id,
            'shell': self.shell,
            'cwd': self.cwd,
            'cols': self.cols,
            'rows': self.rows,
            'created_at': self.created_at,
            'last_activity': self.last_activity,
            'active': self.active,
            'pid': self.pty.pid
        }
