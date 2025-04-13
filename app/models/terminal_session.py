import os
import time
import uuid
import ptyprocess
import threading
import pyte
import subprocess
import shutil
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
        # Generate a unique session ID
        self.id = str(uuid.uuid4())
        self.shell = shell
        self.cols = cols
        self.rows = rows
        self.created_at = time.time()
        self.last_activity = time.time()
        self.buffer_size = buffer_size
        
        # Get storage directory from environment or use default
        storage_base = os.environ.get('STORAGE_DIR', './storage/users')
        
        # Create user-specific directories for isolated storage
        self.user_dir = os.path.join(storage_base, self.id)
        self.user_home = os.path.join(self.user_dir, 'home')
        self.user_files = os.path.join(self.user_dir, 'files')
        self.user_venv = os.path.join(self.user_dir, 'venv')
        
        # Create these directories
        os.makedirs(self.user_home, exist_ok=True)
        os.makedirs(self.user_files, exist_ok=True)
        os.makedirs(f"{self.user_home}/bin", exist_ok=True)
        
        # Use user-specific files directory if cwd is not specified
        if not cwd or cwd == "/":
            self.cwd = self.user_files
        else:
            # If a custom cwd is provided, make sure it exists
            self.cwd = cwd
            if not os.path.exists(self.cwd):
                os.makedirs(self.cwd, exist_ok=True)
        
        # Configure environment properly for full terminal experience with user isolation
        self.env = env.copy() if env else os.environ.copy()
        
        # Set HOME to the user's isolated home directory
        self.env['HOME'] = self.user_home
        
        # Ensure proper terminal settings
        if 'TERM' not in self.env:
            self.env['TERM'] = 'xterm-256color'
        
        # Configure editor environment variables
        self.env['EDITOR'] = 'nano'  # Default editor
        self.env['VISUAL'] = 'nano'  # Default visual editor
        
        # Create a Python virtual environment for this session
        self._create_virtual_environment()
        
        # Ensure proper PATH environment that includes user's own binaries and virtual environment
        base_path = '/usr/local/bin:/usr/bin:/bin'
        session_paths = f"{self.user_home}/bin:{self.user_files}:{self.user_venv}/bin"
        self.env['PATH'] = f"{session_paths}:{base_path}"
        
        # Set PYTHONUSERBASE to user's home directory for pip install --user
        self.env['PYTHONUSERBASE'] = self.user_home
        
        # Set user ID in environment for scripts to identify user's session
        self.env['USER_SESSION_ID'] = self.id
            
        # Create output buffer with deque for efficient append and trim operations
        self.output_buffer = deque(maxlen=buffer_size)
        
        # Set up terminal emulator
        self.screen = pyte.Screen(cols, rows)
        self.stream = pyte.Stream()
        self.stream.attach(self.screen)
        
        # Create shell config files and other user files
        self._setup_user_environment()
        
        # Start the PTY process with user-specific environment
        self.pty = ptyprocess.PtyProcess.spawn(
            argv=[shell],
            cwd=self.cwd,
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
        
        # Activate the virtual environment automatically on session start
        self._activate_virtual_environment()
    
    def _create_virtual_environment(self):
        """Create a Python virtual environment specific to this user session"""
        try:
            if not os.path.exists(self.user_venv):
                # Create virtual environment
                subprocess.run(
                    [sys.executable, '-m', 'venv', self.user_venv], 
                    check=True,
                    capture_output=True
                )
                
                # Upgrade pip in the virtual environment
                subprocess.run(
                    [f"{self.user_venv}/bin/pip", "install", "--upgrade", "pip", "setuptools", "wheel"],
                    check=True,
                    capture_output=True
                )
        except Exception as e:
            print(f"Error creating virtual environment: {str(e)}")
    
    def _activate_virtual_environment(self):
        """Activate the virtual environment by sending commands to the terminal"""
        # Add virtual environment activation to the startup
        venv_activate_path = f"{self.user_venv}/bin/activate"
        if os.path.exists(venv_activate_path):
            # Send command to source the activate script
            self.write(f"source {venv_activate_path}\n")
            # Show python version to confirm
            self.write("python --version\n")
            # Show pip version
            self.write("pip --version\n")
    
    def _setup_user_environment(self):
        """Set up the user's environment with configuration files"""
        # Create a custom .bashrc with user-specific paths and config
        bashrc_path = os.path.join(self.user_home, '.bashrc')
        with open(bashrc_path, 'w') as f:
            f.write(f'''
# Terminal configuration for user session {self.id}
export PS1="\\[\\033[01;32m\\]user@termux-web\\[\\033[00m\\]:\\[\\033[01;34m\\]\\w\\[\\033[00m\\]\\$ "

# Environment variables
export EDITOR=nano
export VISUAL=nano
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export HISTSIZE=5000
export HISTFILESIZE=10000
export HISTCONTROL=ignoreboth:erasedups

# Session-specific paths
export USER_SESSION_ID="{self.id}"
export USER_FILES="{self.user_files}"
export USER_HOME="{self.user_home}"
export USER_VENV="{self.user_venv}"
export PYTHONUSERBASE="{self.user_home}"

# Path configuration
export PATH="{self.user_home}/bin:{self.user_files}:{self.user_venv}/bin:$PATH"

# Automatically activate the virtual environment
source "{self.user_venv}/bin/activate" 2>/dev/null || echo "Virtual environment not initialized yet."

# Aliases
alias ll="ls -la"
alias py=python
alias python=python3
alias pip=pip3
alias cls="clear"
alias h="history"
alias ..="cd .."
alias ...="cd ../.."
alias myfiles="cd {self.user_files}"
alias myvenv="cd {self.user_venv}"

# Colors for ls command
export LS_COLORS="di=1;34:ln=1;36:so=1;35:pi=1;33:ex=1;32:bd=1;33:cd=1;33:su=1;31:sg=1;31:tw=1;34:ow=1;34"
alias ls="ls --color=auto"
alias grep="grep --color=auto"

# Welcome message
echo "Welcome to your isolated Termux Web Terminal! (Session ID: {self.id})"
echo "• Your files are stored in: {self.user_files}"
echo "• Edit files:  nano filename.py, vim filename.py"
echo "• Run scripts: python filename.py"
echo "• Install packages: pip install packagename"
echo "• Your packages are isolated to this session only"
echo ""
''')
        os.chmod(bashrc_path, 0o755)
        
        # Create .bash_profile to source .bashrc
        bash_profile_path = os.path.join(self.user_home, '.bash_profile')
        with open(bash_profile_path, 'w') as f:
            f.write('''
# Source bashrc
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi
''')
        os.chmod(bash_profile_path, 0o755)
        
        # Create empty .bash_history
        history_path = os.path.join(self.user_home, '.bash_history')
        open(history_path, 'w').close()
        os.chmod(history_path, 0o644)
            
        # Add .vimrc with basic configuration
        vimrc_path = os.path.join(self.user_home, '.vimrc')
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
set ruler
set showcmd
set incsearch
set hlsearch
set showmatch
filetype plugin indent on
''')
        
        # Create .tmux.conf
        tmux_conf_path = os.path.join(self.user_home, '.tmux.conf')
        with open(tmux_conf_path, 'w') as f:
            f.write('''
set -g default-terminal "screen-256color"
set -g history-limit 10000
set -g base-index 1
setw -g pane-base-index 1
set -g status-bg black
set -g status-fg white
''')
        
        # Create .inputrc
        inputrc_path = os.path.join(self.user_home, '.inputrc')
        with open(inputrc_path, 'w') as f:
            f.write('''
set completion-ignore-case on
set show-all-if-ambiguous on
set mark-symlinked-directories on
"\e[A": history-search-backward
"\e[B": history-search-forward
''')
        
        # Create a basic README in the user's files directory
        readme_path = os.path.join(self.user_files, 'README.txt')
        with open(readme_path, 'w') as f:
            f.write(f'''
Welcome to your personal workspace!

This is your isolated environment where you can:
- Create and edit files
- Install Python packages
- Run scripts and applications

Your session ID is: {self.id}

All files and packages you create here are only accessible to you.
''')
        
        # Create an example Python file
        example_path = os.path.join(self.user_files, 'example.py')
        with open(example_path, 'w') as f:
            f.write('''
#!/usr/bin/env python3
"""
Example Python script
"""

def hello(name="World"):
    """Say hello to the specified name."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(hello())
    
    # You can also get input from the user
    name = input("Enter your name: ")
    print(hello(name))
    
    print("\\nTry installing packages with:")
    print("pip install requests")
''')
        os.chmod(example_path, 0o755)
    
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
    
    def cleanup(self, remove_files=False):
        """
        Clean up resources associated with this session.
        
        Args:
            remove_files (bool): If True, remove all user files
        """
        self.terminate()
        
        if remove_files and os.path.exists(self.user_dir):
            try:
                shutil.rmtree(self.user_dir)
            except Exception as e:
                print(f"Error removing user directory: {str(e)}")
    
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
            'user_dir': self.user_dir,
            'user_files': self.user_files,
            'user_venv': self.user_venv,
            'pid': self.pty.pid if self.active else None
        }

# Make sure we import sys
import sys
