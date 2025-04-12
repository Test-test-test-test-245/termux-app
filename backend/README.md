# Termux Web - Terminal Backend

This is a Flask-based backend implementation that provides terminal functionality via WebSockets, similar to Termux for Android. This server allows iOS clients to connect to and interact with terminal sessions running on the server.

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

## Python Development Features

### Terminal-Based File Editing

The backend includes multiple terminal-based editors that can be used directly within the terminal interface:

- **nano** - Simple, user-friendly editor (default)
- **vim** - Advanced text editor with syntax highlighting
- **emacs** - Powerful, extensible text editor
- **joe** - Simple editor with intuitive keybindings

To edit a file, simply use one of these editors in the terminal:

```bash
# Create or edit a Python script with nano (easiest for beginners)
nano my_script.py

# Or use vim for more advanced editing
vim my_script.py

# Or use emacs
emacs my_script.py
```

### Python Package Management

Users can install Python packages directly from the terminal using pip:

```bash
# Install a package
pip install numpy

# Upgrade a package
pip install --upgrade pandas

# Install specific version
pip install requests==2.25.1

# List installed packages
pip list
```

## Setup and Installation

### Local Development

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the development server:
   ```
   python app.py
   ```
   
### Environment Variables

The following environment variables can be configured:

- `PORT` - Port to run the server on (default: 5000)
- `SECRET_KEY` - Secret key for Flask session security
- `INACTIVE_TIMEOUT` - Seconds after which inactive terminal sessions are cleaned up (default: 3600)
- `HOME_DIR` - Directory for user home files (default: /app/storage/home)

## API Documentation

### RESTful API Endpoints

#### Terminal API

- **GET** `/api/terminal/sessions` - List all active terminal sessions
- **POST** `/api/terminal/sessions` - Create a new terminal session
- **GET** `/api/terminal/sessions/{session_id}` - Get session details
- **POST** `/api/terminal/sessions/{session_id}/size` - Resize a session
- **DELETE** `/api/terminal/sessions/{session_id}` - Terminate a session

#### File Management API

- **GET** `/api/files` - List files in a directory
- **POST** `/api/files` - Create a file or directory
- **PUT** `/api/files` - Update a file's content
- **DELETE** `/api/files` - Delete a file or directory
- **GET** `/api/files/read` - Read file content
- **GET** `/api/files/download` - Download a file
- **POST** `/api/files/upload` - Upload a file
- **POST** `/api/files/rename` - Rename a file or directory

#### Python Package API

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

#### Client → Server Events

- **connect** - Connect to the WebSocket server
- **join** - Join a terminal session
- **leave** - Leave a terminal session
- **input** - Send input to a terminal session
- **resize** - Resize a terminal session
- **terminate** - Terminate a terminal session

#### Server → Client Events

- **connected** - Connection established
- **joined** - Successfully joined a terminal session
- **left** - Successfully left a terminal session
- **output** - Terminal output received
- **resized** - Terminal session resized
- **terminated** - Terminal session terminated
- **error** - Error occurred

## Deployment to Render.com

See [DEPLOY_TO_RENDER.md](./DEPLOY_TO_RENDER.md) for detailed instructions on deploying to Render.com.

## iOS App Integration

To integrate with your iOS app:

1. Use a WebSocket client library like Starscream or Socket.IO-Client-Swift
2. Connect to the server WebSocket endpoint
3. Handle the WebSocket events to send and receive terminal data
4. Implement a terminal emulator UI component or use an existing library like SwiftTerm

### Example Integration Code

```swift
// Using Socket.IO-Client-Swift
let socket = SocketManager(socketURL: URL(string: "https://your-backend-url.com")!, config: [.log(true)])
let terminalSocket = socket.defaultSocket

// Connect event
terminalSocket.on(clientEvent: .connect) { _, _ in
    print("Connected to terminal server")
}

// Join a session
func joinSession(sessionId: String) {
    terminalSocket.emit("join", ["session_id": sessionId])
}

// Send input
func sendInput(sessionId: String, data: String) {
    terminalSocket.emit("input", ["session_id": sessionId, "data": data])
}

// Receive output
terminalSocket.on("output") { data, _ in
    if let response = data[0] as? [String: Any],
       let sessionId = response["session_id"] as? String,
       let outputData = response["data"] as? String {
        // Process and display terminal output
    }
}

// Connect to server
terminalSocket.connect()
```

## Security Considerations

- WebSocket connections should be secured with TLS (HTTPS)
- Consider implementing authentication and authorization
- Limit access to terminal commands based on user permissions
- Sanitize user input to prevent command injection
- Set appropriate timeouts for inactive sessions

## Comparison with Termux

This implementation is inspired by the Termux Android app, but adapted for a client-server architecture:

- **Termux**: Local Android app running terminals directly on the device
- **Termux Web**: Client-server architecture with terminals running on the server and accessed via WebSockets

The key differences:

1. **Architecture**: Client-server vs. local app
2. **Terminal Emulation**: Server-side PTY + emulator vs. Android's native PTY
3. **Interface**: WebSockets for I/O vs. direct process interaction
4. **Deployment**: Hosted server vs. installed app

## Monitoring and Maintenance

To ensure the application runs smoothly:

1. Monitor server resource usage (CPU, memory)
2. Check logs for errors or unexpected behavior
3. Set up alerts for service disruptions
4. Periodically check for inactive sessions that weren't properly cleaned up

## License

This project is open-source and available under the MIT License.