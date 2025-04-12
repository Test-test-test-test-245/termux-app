from flask import Blueprint, request, jsonify, send_file, safe_join
import os
import shutil
import mimetypes
from werkzeug.utils import secure_filename

files_api = Blueprint('files_api', __name__, url_prefix='/api/files')

# Base directory for user files
USER_FILES_DIR = os.environ.get('USER_FILES_DIR', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'storage/user_files'))

# Ensure the directory exists
os.makedirs(USER_FILES_DIR, exist_ok=True)

@files_api.route('', methods=['GET'])
def list_files():
    """List files and directories in the specified path"""
    path = request.args.get('path', '')
    abs_path = os.path.join(USER_FILES_DIR, path.lstrip('/'))
    
    # Security check to prevent directory traversal
    if not os.path.abspath(abs_path).startswith(os.path.abspath(USER_FILES_DIR)):
        return jsonify({'error': 'Invalid path'}), 400
    
    if not os.path.exists(abs_path):
        return jsonify({'error': 'Path does not exist'}), 404
    
    if not os.path.isdir(abs_path):
        return jsonify({'error': 'Path is not a directory'}), 400
    
    files = []
    for item in os.listdir(abs_path):
        item_path = os.path.join(abs_path, item)
        item_stat = os.stat(item_path)
        files.append({
            'name': item,
            'path': os.path.join(path, item).replace('\\', '/').lstrip('/'),
            'is_dir': os.path.isdir(item_path),
            'size': item_stat.st_size,
            'modified': item_stat.st_mtime,
            'created': item_stat.st_ctime
        })
    
    return jsonify({
        'path': path,
        'files': files
    })

@files_api.route('', methods=['POST'])
def create_file_or_directory():
    """Create a new file or directory"""
    data = request.json
    path = data.get('path', '').lstrip('/')
    content = data.get('content', '')
    is_directory = data.get('is_directory', False)
    
    abs_path = os.path.join(USER_FILES_DIR, path)
    
    # Security check to prevent directory traversal
    if not os.path.abspath(abs_path).startswith(os.path.abspath(USER_FILES_DIR)):
        return jsonify({'error': 'Invalid path'}), 400
    
    # Create parent directories if they don't exist
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    
    if is_directory:
        if os.path.exists(abs_path):
            return jsonify({'error': 'Directory already exists'}), 400
        os.makedirs(abs_path, exist_ok=True)
        return jsonify({'message': f'Directory {path} created successfully'})
    else:
        if os.path.exists(abs_path):
            return jsonify({'error': 'File already exists'}), 400
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'message': f'File {path} created successfully'})

@files_api.route('', methods=['PUT'])
def update_file():
    """Update a file's content"""
    data = request.json
    path = data.get('path', '').lstrip('/')
    content = data.get('content', '')
    
    abs_path = os.path.join(USER_FILES_DIR, path)
    
    # Security check to prevent directory traversal
    if not os.path.abspath(abs_path).startswith(os.path.abspath(USER_FILES_DIR)):
        return jsonify({'error': 'Invalid path'}), 400
    
    if not os.path.exists(abs_path):
        return jsonify({'error': 'File does not exist'}), 404
    
    if os.path.isdir(abs_path):
        return jsonify({'error': 'Cannot update directory content'}), 400
    
    with open(abs_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return jsonify({'message': f'File {path} updated successfully'})

@files_api.route('', methods=['DELETE'])
def delete_file_or_directory():
    """Delete a file or directory"""
    path = request.args.get('path', '').lstrip('/')
    recursive = request.args.get('recursive', 'false').lower() == 'true'
    
    abs_path = os.path.join(USER_FILES_DIR, path)
    
    # Security check to prevent directory traversal
    if not os.path.abspath(abs_path).startswith(os.path.abspath(USER_FILES_DIR)):
        return jsonify({'error': 'Invalid path'}), 400
    
    if not os.path.exists(abs_path):
        return jsonify({'error': 'Path does not exist'}), 404
    
    try:
        if os.path.isdir(abs_path):
            if recursive:
                shutil.rmtree(abs_path)
            else:
                os.rmdir(abs_path)  # Will fail if directory is not empty
        else:
            os.remove(abs_path)
        
        return jsonify({'message': f'{path} deleted successfully'})
    except OSError as e:
        return jsonify({'error': str(e)}), 400

@files_api.route('/read', methods=['GET'])
def read_file():
    """Read the content of a file"""
    path = request.args.get('path', '').lstrip('/')
    abs_path = os.path.join(USER_FILES_DIR, path)
    
    # Security check to prevent directory traversal
    if not os.path.abspath(abs_path).startswith(os.path.abspath(USER_FILES_DIR)):
        return jsonify({'error': 'Invalid path'}), 400
    
    if not os.path.exists(abs_path):
        return jsonify({'error': 'File does not exist'}), 404
    
    if os.path.isdir(abs_path):
        return jsonify({'error': 'Cannot read directory content'}), 400
    
    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'path': path,
            'content': content
        })
    except UnicodeDecodeError:
        return jsonify({'error': 'File is not a text file'}), 400

@files_api.route('/download', methods=['GET'])
def download_file():
    """Download a file"""
    path = request.args.get('path', '').lstrip('/')
    abs_path = os.path.join(USER_FILES_DIR, path)
    
    # Security check to prevent directory traversal
    if not os.path.abspath(abs_path).startswith(os.path.abspath(USER_FILES_DIR)):
        return jsonify({'error': 'Invalid path'}), 400
    
    if not os.path.exists(abs_path):
        return jsonify({'error': 'File does not exist'}), 404
    
    if os.path.isdir(abs_path):
        return jsonify({'error': 'Cannot download directory'}), 400
    
    filename = os.path.basename(abs_path)
    mimetype = mimetypes.guess_type(abs_path)[0] or 'application/octet-stream'
    
    return send_file(abs_path, mimetype=mimetype, as_attachment=True, 
                    download_name=filename)

@files_api.route('/upload', methods=['POST'])
def upload_file():
    """Upload a file"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    uploaded_file = request.files['file']
    if uploaded_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    path = request.form.get('path', '').lstrip('/')
    filename = secure_filename(uploaded_file.filename)
    
    # Create target directory if it doesn't exist
    target_dir = os.path.join(USER_FILES_DIR, path)
    os.makedirs(target_dir, exist_ok=True)
    
    # Security check to prevent directory traversal
    if not os.path.abspath(target_dir).startswith(os.path.abspath(USER_FILES_DIR)):
        return jsonify({'error': 'Invalid path'}), 400
    
    file_path = os.path.join(target_dir, filename)
    uploaded_file.save(file_path)
    
    return jsonify({
        'message': f'File {filename} uploaded successfully',
        'path': os.path.join(path, filename).replace('\\', '/').lstrip('/')
    })

@files_api.route('/rename', methods=['POST'])
def rename_file():
    """Rename a file or directory"""
    data = request.json
    old_path = data.get('old_path', '').lstrip('/')
    new_name = data.get('new_name', '')
    
    abs_old_path = os.path.join(USER_FILES_DIR, old_path)
    
    # Security check to prevent directory traversal
    if not os.path.abspath(abs_old_path).startswith(os.path.abspath(USER_FILES_DIR)):
        return jsonify({'error': 'Invalid path'}), 400
    
    if not os.path.exists(abs_old_path):
        return jsonify({'error': 'File or directory does not exist'}), 404
    
    if not new_name:
        return jsonify({'error': 'New name is required'}), 400
    
    # Get the directory of the old path
    dir_name = os.path.dirname(abs_old_path)
    abs_new_path = os.path.join(dir_name, secure_filename(new_name))
    
    if os.path.exists(abs_new_path):
        return jsonify({'error': 'A file or directory with this name already exists'}), 400
    
    try:
        os.rename(abs_old_path, abs_new_path)
        new_path = os.path.join(os.path.dirname(old_path), new_name).replace('\\', '/').lstrip('/')
        return jsonify({
            'message': f'Renamed successfully',
            'new_path': new_path
        })
    except OSError as e:
        return jsonify({'error': str(e)}), 400
