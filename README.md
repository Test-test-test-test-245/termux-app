# Termux Web Terminal

A Flask-based web terminal backend that provides terminal functionality via WebSockets. This server allows clients (like iOS apps) to connect to and interact with terminal sessions running on the server.

## Features

- Create and manage multiple terminal sessions
- Real-time terminal interaction via WebSockets
- Terminal state persistence
- Full terminal emulation using PTY (Pseudo Terminal) and terminal emulator
- Session resize capability to match client display
- RESTful API for terminal session management
- File management API for working with files
- In-terminal editing with multiple editors (vim, nano, emacs, joe)
- Python development capabilities with pip package management
- Automatic cleanup of inactive sessions

## Architecture

The system is designed with the following components:

### Core Components

1. **Terminal Session Model** - Represents a terminal session with a PTY process and terminal emulator
2. **Terminal Service** - Manages terminal sessions and handles input/output routing
3. **Web API** - REST endpoints for terminal session and file management
4. **WebSocket API** - Real-time communication for terminal input/output

### Technology Stack

- **Flask** - Web framework
- **Flask-SocketIO** - WebSocket support
- **Eventlet** - Async WSGI server
- **PTYProcess** - Pseudo-terminal management
- **Pyte** - Terminal emulator
- **Terminal Editors** - vim, nano, emacs, joe for in-terminal file editing

## Quick Start

### Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/termux-web-terminal.git
cd termux-web-terminal

# Run the development server
./run_local.sh
```

### Testing the API

After starting the server, you can run the test script to verify everything is working:

```bash
./test_api.py
```

### Docker Deployment

```bash
docker build -t termux-web-terminal .
docker run -p 5000:5000 termux-web-terminal
```

## Deploying to Render.com

This project includes a `render.yaml` file for easy deployment to Render.com. See [DEPLOY_TO_RENDER.md](DEPLOY_TO_RENDER.md) for detailed instructions.

## API Documentation

### RESTful API Endpoints

- **GET** `/api/terminal/sessions` - List all terminal sessions
- **POST** `/api/terminal/sessions` - Create a new terminal session
- **GET** `/api/terminal/sessions/{session_id}` - Get session details
- **POST** `/api/terminal/sessions/{session_id}/size` - Resize a session
- **DELETE** `/api/terminal/sessions/{session_id}` - Terminate a session
- **GET** `/api/files` - List files in a directory
- **POST** `/api/files` - Create a file or directory
- **PUT** `/api/files` - Update a file's content
- **DELETE** `/api/files` - Delete a file or directory
- **GET** `/api/files/read` - Read file content
- **GET** `/api/files/download` - Download a file
- **POST** `/api/files/upload` - Upload a file
- **POST** `/api/files/rename` - Rename a file or directory
- **GET** `/api/python/packages` - List installed packages
- **POST** `/api/python/packages` - Install a package
- **DELETE** `/api/python/packages` - Uninstall a package
- **GET** `/api/python/packages/search` - Search for packages
- **GET** `/api/python/packages/info` - Get package info
- **GET** `/api/python/venvs` - List virtual environments
- **POST** `/api/python/venvs` - Create a virtual environment
- **DELETE** `/api/python/venvs` - Delete a virtual environment
- **POST** `/api/python/run` - Run Python code

### WebSocket Events

See [client-example.html](client-example.html) for a complete example of using the WebSocket API.

## iOS Client Integration

The [ios_client_integration.swift](ios_client_integration.swift) file provides a Swift client implementation for iOS apps to connect to this backend.

## Terminal Usage Guide

For details on using the terminal interface, see [TERMINAL_USAGE.md](TERMINAL_USAGE.md).

## License

This project is open-source and available under the MIT License.
