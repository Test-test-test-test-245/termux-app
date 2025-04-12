# Termux Web - Terminal Backend

This is a Flask-based backend implementation that provides terminal functionality via WebSockets, similar to Termux for Android. This server allows iOS clients to connect to and interact with terminal sessions running on the server.

## Features

- Create and manage multiple terminal sessions
- Real-time terminal interaction via WebSockets
- Terminal state persistence
- Full terminal emulation using PTY (Pseudo Terminal) and terminal emulator
- Session resize capability to match client display
- RESTful API for terminal session management
- Automatic cleanup of inactive sessions

## Architecture

The system is designed with the following components:

### Core Components

1. **Terminal Session Model** - Represents a terminal session with a PTY process and terminal emulator
2. **Terminal Service** - Manages terminal sessions and handles input/output routing
3. **Web API** - REST endpoints for terminal session management
4. **WebSocket API** - Real-time communication for terminal input/output

### Technology Stack

- **Flask** - Web framework
- **Flask-SocketIO** - WebSocket support
- **Eventlet** - Async WSGI server
- **PTYProcess** - Pseudo-terminal management
- **Pyte** - Terminal emulator

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

## API Documentation

### RESTful API Endpoints

#### List Sessions
- **GET** `/api/terminal/sessions`
- Returns a list of all active terminal sessions

#### Create Session
- **POST** `/api/terminal/sessions`
- Create a new terminal session
- Request Body:
  ```json
  {
    "shell": "/bin/bash",
    "cwd": "/home/user",
    "env": {"TERM": "xterm-256color"},
    "cols": 80,
    "rows": 24
  }
  ```

#### Get Session
- **GET** `/api/terminal/sessions/{session_id}`
- Get information about a specific terminal session

#### Resize Session
- **POST** `/api/terminal/sessions/{session_id}/size`
- Resize a terminal session
- Request Body:
  ```json
  {
    "cols": 100,
    "rows": 30
  }
  ```

#### Terminate Session
- **DELETE** `/api/terminal/sessions/{session_id}`
- Terminate a terminal session

### WebSocket Events

#### Client → Server Events

- **connect** - Connect to the WebSocket server
- **join** - Join a terminal session
  ```json
  {
    "session_id": "2b948e4a-32a5-4245-a890-6aa46ef59a4d"
  }
  ```
- **leave** - Leave a terminal session
  ```json
  {
    "session_id": "2b948e4a-32a5-4245-a890-6aa46ef59a4d"
  }
  ```
- **input** - Send input to a terminal session
  ```json
  {
    "session_id": "2b948e4a-32a5-4245-a890-6aa46ef59a4d",
    "data": "ls -la\n"
  }
  ```
- **resize** - Resize a terminal session
  ```json
  {
    "session_id": "2b948e4a-32a5-4245-a890-6aa46ef59a4d",
    "cols": 100,
    "rows": 30
  }
  ```
- **terminate** - Terminate a terminal session
  ```json
  {
    "session_id": "2b948e4a-32a5-4245-a890-6aa46ef59a4d"
  }
  ```

#### Server → Client Events

- **connected** - Connection established
- **joined** - Successfully joined a terminal session
- **left** - Successfully left a terminal session
- **output** - Terminal output received
  ```json
  {
    "session_id": "2b948e4a-32a5-4245-a890-6aa46ef59a4d",
    "data": "user@host:~$ "
  }
  ```
- **resized** - Terminal session resized
- **terminated** - Terminal session terminated
- **error** - Error occurred

## Deployment to Render.com

To deploy this application to Render.com:

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Use the following settings:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:$PORT app:app`
4. Add any necessary environment variables
5. Deploy the application

## iOS App Integration

To integrate with an iOS app:

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