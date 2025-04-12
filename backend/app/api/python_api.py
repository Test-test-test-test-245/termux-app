import subprocess
import json
import sys
import os
import re
import venv
from flask import Blueprint, request, jsonify, current_app

python_api = Blueprint('python_api', __name__, url_prefix='/api/python')

# Base directory for Python virtual environments
VENV_DIR = os.environ.get('VENV_DIR', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'storage/venvs'))

# Ensure the directory exists
os.makedirs(VENV_DIR, exist_ok=True)

@python_api.route('/packages', methods=['GET'])
def list_packages():
    """List all installed Python packages"""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'list', '--format=json'],
            capture_output=True,
            text=True,
            check=True
        )
        packages = json.loads(result.stdout)
        return jsonify({'packages': packages})
    except subprocess.CalledProcessError as e:
        return jsonify({'error': e.stderr}), 500

@python_api.route('/packages/search', methods=['GET'])
def search_packages():
    """Search for Python packages on PyPI"""
    query = request.args.get('query', '')
    if not query:
        return jsonify({'error': 'Query parameter is required'}), 400

    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'search', query],
            capture_output=True,
            text=True
        )
        
        # pip search is deprecated, so as a fallback we use a simple API call to PyPI
        if 'ERROR: DEPRECATION:' in result.stderr:
            import requests
            response = requests.get(f'https://pypi.org/pypi/{query}/json')
            if response.status_code == 200:
                package_data = response.json()
                return jsonify({
                    'name': package_data['info']['name'],
                    'version': package_data['info']['version'],
                    'summary': package_data['info']['summary'],
                    'description': package_data['info']['description'],
                    'author': package_data['info']['author'],
                    'author_email': package_data['info']['author_email'],
                    'homepage': package_data['info']['home_page'],
                })
            
            # If specific package not found, search PyPI simple index
            response = requests.get('https://pypi.org/simple/')
            if response.status_code == 200:
                packages = re.findall(r'<a[^>]*>([^<]+)</a>', response.text)
                matches = [pkg for pkg in packages if query.lower() in pkg.lower()]
                return jsonify({'packages': matches[:20]})  # Limit to 20 results
            
            return jsonify({'error': 'Package search failed'}), 500
            
        # Parse pip search output
        packages = []
        lines = result.stdout.strip().split('\n')
        current_package = {}
        
        for line in lines:
            if line.strip():
                if not line.startswith(' '):
                    if current_package:
                        packages.append(current_package)
                    parts = line.split(' (', 1)
                    name = parts[0].strip()
                    version = parts[1].split(')', 1)[0] if len(parts) > 1 else ''
                    current_package = {'name': name, 'version': version}
                else:
                    if 'description' not in current_package:
                        current_package['description'] = line.strip()
        
        if current_package:
            packages.append(current_package)
            
        return jsonify({'packages': packages})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@python_api.route('/packages', methods=['POST'])
def install_package():
    """Install a Python package"""
    data = request.json
    package_name = data.get('package')
    
    if not package_name:
        return jsonify({'error': 'Package name is required'}), 400
    
    # Clean the package name to prevent command injection
    package_name = re.sub(r'[^a-zA-Z0-9._-]', '', package_name)
    
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', package_name],
            capture_output=True,
            text=True,
            check=True
        )
        return jsonify({
            'message': f'Package {package_name} installed successfully',
            'details': result.stdout
        })
    except subprocess.CalledProcessError as e:
        return jsonify({'error': e.stderr}), 500

@python_api.route('/packages', methods=['DELETE'])
def uninstall_package():
    """Uninstall a Python package"""
    package_name = request.args.get('package')
    
    if not package_name:
        return jsonify({'error': 'Package name is required'}), 400
    
    # Clean the package name to prevent command injection
    package_name = re.sub(r'[^a-zA-Z0-9._-]', '', package_name)
    
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'uninstall', '-y', package_name],
            capture_output=True,
            text=True,
            check=True
        )
        return jsonify({
            'message': f'Package {package_name} uninstalled successfully',
            'details': result.stdout
        })
    except subprocess.CalledProcessError as e:
        return jsonify({'error': e.stderr}), 500

@python_api.route('/packages/info', methods=['GET'])
def package_info():
    """Get detailed information about a Python package"""
    package_name = request.args.get('package')
    
    if not package_name:
        return jsonify({'error': 'Package name is required'}), 400
    
    try:
        # Check if package is installed
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'show', package_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return jsonify({'error': 'Package not found'}), 404
        
        # Parse the output
        lines = result.stdout.strip().split('\n')
        info = {}
        
        for line in lines:
            if ': ' in line:
                key, value = line.split(': ', 1)
                info[key.lower()] = value
        
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@python_api.route('/venvs', methods=['GET'])
def list_venvs():
    """List all Python virtual environments"""
    try:
        venvs = []
        for item in os.listdir(VENV_DIR):
            venv_path = os.path.join(VENV_DIR, item)
            if os.path.isdir(venv_path) and os.path.exists(os.path.join(venv_path, 'pyvenv.cfg')):
                venvs.append(item)
        
        return jsonify({'venvs': venvs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@python_api.route('/venvs', methods=['POST'])
def create_venv():
    """Create a new Python virtual environment"""
    data = request.json
    name = data.get('name')
    
    if not name:
        return jsonify({'error': 'Virtual environment name is required'}), 400
    
    # Sanitize name to prevent path traversal
    name = re.sub(r'[^a-zA-Z0-9_-]', '', name)
    
    venv_path = os.path.join(VENV_DIR, name)
    
    if os.path.exists(venv_path):
        return jsonify({'error': f'Virtual environment {name} already exists'}), 400
    
    try:
        venv.create(venv_path, with_pip=True)
        return jsonify({'message': f'Virtual environment {name} created successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@python_api.route('/venvs', methods=['DELETE'])
def delete_venv():
    """Delete a Python virtual environment"""
    name = request.args.get('name')
    
    if not name:
        return jsonify({'error': 'Virtual environment name is required'}), 400
    
    # Sanitize name to prevent path traversal
    name = re.sub(r'[^a-zA-Z0-9_-]', '', name)
    
    venv_path = os.path.join(VENV_DIR, name)
    
    if not os.path.exists(venv_path):
        return jsonify({'error': f'Virtual environment {name} does not exist'}), 404
    
    try:
        import shutil
        shutil.rmtree(venv_path)
        return jsonify({'message': f'Virtual environment {name} deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@python_api.route('/run', methods=['POST'])
def run_python_code():
    """Run Python code and return the result"""
    data = request.json
    code = data.get('code')
    
    if not code:
        return jsonify({'error': 'Python code is required'}), 400
    
    try:
        # Create a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
            f.write(code.encode('utf-8'))
            temp_file = f.name
        
        # Run the code
        result = subprocess.run(
            [sys.executable, temp_file],
            capture_output=True,
            text=True,
            timeout=30  # Timeout after 30 seconds to prevent long-running scripts
        )
        
        # Clean up
        os.unlink(temp_file)
        
        return jsonify({
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        })
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Script execution timed out'}), 408
    except Exception as e:
        return jsonify({'error': str(e)}), 500
