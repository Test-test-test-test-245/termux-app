# Terminal Usage Guide

This guide demonstrates how to use the terminal interface for Python development and file management within the Termux Web backend.

## Basic Terminal Navigation

```bash
# List files
ls

# List files with details
ls -la

# Change directory
cd /path/to/directory

# Print current directory
pwd

# Create directory
mkdir my_project

# Remove directory
rm -rf directory_name  # Be careful with this command!
```

## File Editing

The terminal includes multiple text editors that you can use directly within the terminal:

### Nano (Beginner-Friendly)

```bash
# Create or edit a file with nano
nano my_script.py
```

Nano Keyboard Shortcuts:
- `Ctrl+O`: Save file
- `Ctrl+X`: Exit
- `Ctrl+K`: Cut line
- `Ctrl+U`: Paste line
- `Ctrl+W`: Search text
- `Ctrl+G`: Get help

### Vim (Advanced)

```bash
# Create or edit a file with vim
vim my_script.py
```

Vim Basic Commands:
- `i`: Enter insert mode
- `Esc`: Exit insert mode
- `:w`: Save file
- `:q`: Quit
- `:wq`: Save and quit
- `:q!`: Quit without saving

### Emacs

```bash
# Create or edit a file with emacs
emacs my_script.py
```

Emacs Basic Commands:
- `Ctrl+X Ctrl+S`: Save file
- `Ctrl+X Ctrl+C`: Exit
- `Ctrl+K`: Cut line
- `Ctrl+Y`: Paste line

## Python Development

### Creating and Running Python Scripts

```bash
# Create a new Python script
nano hello.py

# Add content to the script
# Example:
# #!/usr/bin/env python3
# print("Hello, world!")

# Make the script executable
chmod +x hello.py

# Run the script
python hello.py
# or
./hello.py
```

### Installing Python Packages

```bash
# Install a package
pip install requests

# Install multiple packages
pip install numpy pandas matplotlib

# Install a specific version
pip install flask==2.0.1

# Upgrade a package
pip install --upgrade requests

# Uninstall a package
pip uninstall requests

# List installed packages
pip list

# Show package info
pip show numpy
```

### Using Virtual Environments

```bash
# Create a virtual environment
python -m venv myenv

# Activate the virtual environment
source myenv/bin/activate

# Your prompt will change to show you're in the virtual environment
# Install packages in the virtual environment
pip install flask

# Deactivate when done
deactivate
```

## Example Python Development Workflow

Here's a complete workflow example:

```bash
# Create a project directory
mkdir my_flask_app
cd my_flask_app

# Create a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install flask

# Create an app file
nano app.py

# Add content to app.py:
# from flask import Flask
# 
# app = Flask(__name__)
# 
# @app.route('/')
# def hello():
#     return "Hello, World!"
# 
# if __name__ == '__main__':
#     app.run(debug=True, host='0.0.0.0')

# Save and exit (Ctrl+O, Enter, Ctrl+X in nano)

# Run your app
python app.py

# You will see output showing the Flask server starting
# Press Ctrl+C to stop the server when done
```

## File Transfer

While you can create and edit files directly in the terminal, you can also upload and download files using the REST API:

- **Upload**: Use the `/api/files/upload` endpoint to upload files from your local machine
- **Download**: Use the `/api/files/download` endpoint to download files

## Using Git

```bash
# Clone a repository
git clone https://github.com/username/repository.git

# Check status
git status

# Add files
git add .

# Commit changes
git commit -m "Your commit message"

# Push changes
git push origin main
```

## Other Useful Commands

```bash
# View file content
cat filename.txt

# View file content with pagination
less filename.txt

# Search within files
grep "search_term" filename.txt

# Find files
find . -name "*.py"

# Check disk usage
df -h

# Check process status
ps aux

# Kill a process
kill -9 PROCESS_ID
```
