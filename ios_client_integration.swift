//
//  TerminalService.swift
//  Termux Web Client
//
//  This is an updated Swift client for connecting to the Termux Web backend.
//  It handles terminal sessions via WebSocket and RESTful API as fallback.
//

import Foundation
import UIKit

enum TerminalError: Error {
    case invalidURL
    case networkError(String)
    case responseError(String)
    case sessionError(String)
    case parseError(String)
    case webSocketError(String)
}

typealias TerminalResult<T> = Result<T, TerminalError>

class TerminalService {
    static let shared = TerminalService()
    
    // Set your render.com URL here
    private let baseURL = "https://your-termux-web-api.onrender.com"
    private var sessionId: String?
    private let logger = Debug.shared
    
    // WebSocket properties
    private var webSocketTask: URLSessionWebSocketTask?
    private var isWebSocketConnected = false
    private var useWebSockets = true
    private var reconnectAttempt = 0
    private let maxReconnectAttempts = 5
    private let session = URLSession(configuration: .default)
    
    // Output and command callbacks
    private var outputHandlers: [String: (String) -> Void] = [:]
    private var sessionCallbacks: [String: (TerminalResult<String>) -> Void] = [:]
    
    private init() {
        logger.log(message: "TerminalService initialized")
        setupWebSocketConnection()
    }
    
    // MARK: - WebSocket Setup
    
    private func setupWebSocketConnection() {
        // Convert HTTP URL to WebSocket URL
        var urlString = baseURL
        if urlString.hasPrefix("https://") {
            urlString = "wss://" + urlString.dropFirst(8)
        } else if urlString.hasPrefix("http://") {
            urlString = "ws://" + urlString.dropFirst(7)
        }
        
        guard let url = URL(string: urlString) else {
            logger.log(message: "Invalid WebSocket URL", type: .error)
            useWebSockets = false
            return
        }
        
        var request = URLRequest(url: url)
        
        logger.log(message: "Setting up WebSocket connection to \(url.absoluteString)", type: .info)
        webSocketTask = session.webSocketTask(with: request)
        webSocketTask?.resume()
        
        // Set up message receiving
        receiveMessage()
    }
    
    private func receiveMessage() {
        webSocketTask?.receive { [weak self] result in
            guard let self = self else { return }
            
            switch result {
            case .success(let message):
                switch message {
                case .string(let text):
                    self.logger.log(message: "WebSocket message received", type: .debug)
                    self.handleWebSocketMessage(text)
                case .data(let data):
                    if let text = String(data: data, encoding: .utf8) {
                        self.logger.log(message: "WebSocket binary message received", type: .debug)
                        self.handleWebSocketMessage(text)
                    }
                @unknown default:
                    self.logger.log(message: "Unknown WebSocket message type received", type: .warning)
                }
                
                // Continue receiving messages
                self.receiveMessage()
                
            case .failure(let error):
                self.logger.log(message: "WebSocket receive error: \(error.localizedDescription)", type: .error)
                self.isWebSocketConnected = false
                
                // Try to reconnect
                self.reconnectWebSocket()
            }
        }
    }
    
    private func handleWebSocketMessage(_ messageText: String) {
        guard let data = messageText.data(using: .utf8) else {
            logger.log(message: "Could not convert WebSocket message to data", type: .error)
            return
        }
        
        do {
            guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                logger.log(message: "Invalid WebSocket message format", type: .error)
                return
            }
            
            // Handle different message types from our backend
            if let event = json["event"] as? String {
                switch event {
                case "connected":
                    isWebSocketConnected = true
                    reconnectAttempt = 0
                    logger.log(message: "WebSocket connected successfully", type: .info)
                    
                    // If we have a session ID, join that session
                    if let sessionId = sessionId {
                        joinSession(sessionId)
                    }
                    
                case "joined":
                    if let sessionData = json["session"] as? [String: Any],
                       let joinedSessionId = json["session_id"] as? String {
                        logger.log(message: "Joined session: \(joinedSessionId)", type: .info)
                        
                        // Call any pending session callbacks
                        if let callback = sessionCallbacks[joinedSessionId] {
                            callback(.success(joinedSessionId))
                            sessionCallbacks.removeValue(forKey: joinedSessionId)
                        }
                    }
                    
                case "output":
                    if let sessionId = json["session_id"] as? String,
                       let output = json["data"] as? String {
                        
                        // If we have a handler for this session, call it
                        if let handler = outputHandlers[sessionId] {
                            handler(output)
                        }
                        
                        logger.log(message: "Received output for session \(sessionId)", type: .debug)
                    }
                    
                case "terminated":
                    if let terminatedSessionId = json["session_id"] as? String {
                        logger.log(message: "Session terminated: \(terminatedSessionId)", type: .info)
                        
                        // If this is our current session, clear it
                        if sessionId == terminatedSessionId {
                            sessionId = nil
                        }
                        
                        // Clear any handlers for this session
                        outputHandlers.removeValue(forKey: terminatedSessionId)
                    }
                    
                case "error":
                    if let errorMessage = json["message"] as? String {
                        logger.log(message: "WebSocket error: \(errorMessage)", type: .error)
                        
                        // If an error occurs for a specific session, notify the callback
                        if let sessionId = json["session_id"] as? String,
                           let callback = sessionCallbacks[sessionId] {
                            callback(.failure(TerminalError.webSocketError(errorMessage)))
                            sessionCallbacks.removeValue(forKey: sessionId)
                        }
                    }
                    
                default:
                    logger.log(message: "Unknown WebSocket event: \(event)", type: .warning)
                }
            }
        } catch {
            logger.log(message: "Error parsing WebSocket message: \(error.localizedDescription)", type: .error)
        }
    }
    
    private func sendWebSocketMessage(_ message: [String: Any]) {
        guard isWebSocketConnected, let webSocketTask = webSocketTask else { 
            logger.log(message: "Cannot send WebSocket message: not connected", type: .warning)
            return 
        }
        
        do {
            let data = try JSONSerialization.data(withJSONObject: message)
            if let messageString = String(data: data, encoding: .utf8) {
                logger.log(message: "Sending WebSocket message", type: .debug)
                let message = URLSessionWebSocketTask.Message.string(messageString)
                webSocketTask.send(message) { [weak self] error in
                    guard let self = self else { return }
                    
                    if let error = error {
                        self.logger.log(message: "WebSocket send error: \(error.localizedDescription)", type: .error)
                        self.isWebSocketConnected = false
                        self.reconnectWebSocket()
                    }
                }
            }
        } catch {
            logger.log(message: "Failed to serialize WebSocket message: \(error.localizedDescription)", type: .error)
        }
    }
    
    private func reconnectWebSocket() {
        guard reconnectAttempt < maxReconnectAttempts else {
            logger.log(message: "Max WebSocket reconnection attempts reached, falling back to HTTP", type: .warning)
            useWebSockets = false
            return
        }
        
        reconnectAttempt += 1
        let delay = pow(2.0, Double(reconnectAttempt - 1))
        
        logger.log(message: "Will attempt to reconnect WebSocket in \(delay) seconds (attempt \(reconnectAttempt))", type: .info)
        
        DispatchQueue.main.asyncAfter(deadline: .now() + delay) { [weak self] in
            guard let self = self, !self.isWebSocketConnected else { return }
            self.logger.log(message: "Attempting to reconnect WebSocket (attempt \(self.reconnectAttempt))", type: .info)
            
            // Close existing connection
            self.webSocketTask?.cancel(with: .goingAway, reason: nil)
            
            // Create new connection
            self.setupWebSocketConnection()
        }
    }
    
    // MARK: - Session Management
    
    /// Creates a new terminal session via API
    func createSession(completion: @escaping (TerminalResult<String>) -> Void) {
        guard let url = URL(string: "\(baseURL)/api/terminal/sessions") else {
            logger.log(message: "Invalid URL for terminal session creation", type: .error)
            completion(.failure(TerminalError.invalidURL))
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        
        // Create session with appropriate size for device
        let body: [String: Any] = [
            "shell": "/bin/bash",
            "cols": 80,
            "rows": 24,
            "env": ["TERM": "xterm-256color"]
        ]
        
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        logger.log(message: "Creating new terminal session", type: .info)
        
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            guard let self = self else { return }
            
            if let error = error {
                self.logger.log(message: "Network error creating terminal session: \(error.localizedDescription)", type: .error)
                completion(.failure(TerminalError.networkError(error.localizedDescription)))
                return
            }
            
            guard let data = data else {
                self.logger.log(message: "No data received from terminal session creation", type: .error)
                completion(.failure(TerminalError.responseError("No data received")))
                return
            }
            
            do {
                if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    if let errorMessage = json["error"] as? String {
                        self.logger.log(message: "Terminal session creation error: \(errorMessage)", type: .error)
                        completion(.failure(TerminalError.responseError(errorMessage)))
                        return
                    }
                    
                    if let newSessionId = json["id"] as? String {
                        self.sessionId = newSessionId
                        
                        // If WebSocket is connected, join the session
                        if self.isWebSocketConnected {
                            self.joinSession(newSessionId)
                        }
                        
                        self.logger.log(message: "Terminal session created successfully: \(newSessionId)", type: .info)
                        completion(.success(newSessionId))
                    } else {
                        self.logger.log(message: "Invalid terminal session response format", type: .error)
                        completion(.failure(TerminalError.responseError("Invalid response format")))
                    }
                } else {
                    self.logger.log(message: "Could not parse terminal session response", type: .error)
                    completion(.failure(TerminalError.responseError("Could not parse response")))
                }
            } catch {
                self.logger.log(message: "JSON parsing error in terminal session response: \(error.localizedDescription)", type: .error)
                completion(.failure(TerminalError.parseError("JSON parsing error: \(error.localizedDescription)")))
            }
        }.resume()
    }
    
    /// Joins a terminal session via WebSocket
    private func joinSession(_ sessionId: String) {
        // Join via WebSocket
        sendWebSocketMessage([
            "event": "join",
            "session_id": sessionId
        ])
        
        // Store this as our current session
        self.sessionId = sessionId
    }
    
    /// Executes a command in the current session
    func executeCommand(
        _ command: String,
        outputHandler: @escaping (String) -> Void,
        completion: @escaping (TerminalResult<Void>) -> Void
    ) {
        // Make sure we have a session
        if sessionId == nil {
            createSession { [weak self] result in
                guard let self = self else { return }
                
                switch result {
                case .success(let newSessionId):
                    self.sessionId = newSessionId
                    self.executeCommandInSession(command, outputHandler: outputHandler, completion: completion)
                case .failure(let error):
                    completion(.failure(error))
                }
            }
        } else {
            executeCommandInSession(command, outputHandler: outputHandler, completion: completion)
        }
    }
    
    /// Executes a command in a specific session
    private func executeCommandInSession(
        _ command: String,
        outputHandler: @escaping (String) -> Void,
        completion: @escaping (TerminalResult<Void>) -> Void
    ) {
        guard let sessionId = sessionId else {
            completion(.failure(TerminalError.sessionError("No active session")))
            return
        }
        
        // Register output handler for this session
        outputHandlers[sessionId] = outputHandler
        
        if isWebSocketConnected {
            // Send command via WebSocket
            sendWebSocketMessage([
                "event": "input",
                "session_id": sessionId,
                "data": command + "\n"
            ])
            
            // Command is sent - consider it successful immediately
            // Output will come through the WebSocket channel
            completion(.success(()))
        } else {
            // Fall back to HTTP API if WebSocket isn't available
            executeCommandViaHTTP(command, sessionId: sessionId, outputHandler: outputHandler, completion: completion)
        }
    }
    
    /// Executes a command via HTTP API as fallback
    private func executeCommandViaHTTP(
        _ command: String,
        sessionId: String,
        outputHandler: @escaping (String) -> Void,
        completion: @escaping (TerminalResult<Void>) -> Void
    ) {
        guard let url = URL(string: "\(baseURL)/api/terminal/sessions/\(sessionId)") else {
            completion(.failure(TerminalError.invalidURL))
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = [
            "command": command + "\n"
        ]
        
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(TerminalError.networkError(error.localizedDescription)))
                return
            }
            
            guard let data = data else {
                completion(.failure(TerminalError.responseError("No data received")))
                return
            }
            
            do {
                if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    if let errorMessage = json["error"] as? String {
                        completion(.failure(TerminalError.responseError(errorMessage)))
                        return
                    }
                    
                    if let output = json["output"] as? String {
                        // Call the output handler with the response
                        outputHandler(output)
                        completion(.success(()))
                    } else {
                        completion(.failure(TerminalError.responseError("No output received")))
                    }
                } else {
                    completion(.failure(TerminalError.parseError("Invalid response format")))
                }
            } catch {
                completion(.failure(TerminalError.parseError("JSON parsing error: \(error.localizedDescription)")))
            }
        }.resume()
    }
    
    /// Resizes the terminal session
    func resizeSession(cols: Int, rows: Int, completion: @escaping (TerminalResult<Void>) -> Void) {
        guard let sessionId = sessionId else {
            completion(.failure(TerminalError.sessionError("No active session")))
            return
        }
        
        if isWebSocketConnected {
            // Resize via WebSocket
            sendWebSocketMessage([
                "event": "resize",
                "session_id": sessionId,
                "cols": cols,
                "rows": rows
            ])
            
            completion(.success(()))
        } else {
            // Fall back to HTTP API
            guard let url = URL(string: "\(baseURL)/api/terminal/sessions/\(sessionId)/size") else {
                completion(.failure(TerminalError.invalidURL))
                return
            }
            
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.addValue("application/json", forHTTPHeaderField: "Content-Type")
            
            let body: [String: Any] = [
                "cols": cols,
                "rows": rows
            ]
            
            request.httpBody = try? JSONSerialization.data(withJSONObject: body)
            
            URLSession.shared.dataTask(with: request) { data, response, error in
                if let error = error {
                    completion(.failure(TerminalError.networkError(error.localizedDescription)))
                    return
                }
                
                if let httpResponse = response as? HTTPURLResponse {
                    if httpResponse.statusCode >= 200 && httpResponse.statusCode < 300 {
                        completion(.success(()))
                    } else {
                        completion(.failure(TerminalError.responseError("HTTP error: \(httpResponse.statusCode)")))
                    }
                } else {
                    completion(.success(()))
                }
            }.resume()
        }
    }
    
    /// Terminates the current session
    func terminateSession(completion: @escaping (TerminalResult<Void>) -> Void) {
        guard let sessionId = sessionId else {
            // No session to terminate
            completion(.success(()))
            return
        }
        
        if isWebSocketConnected {
            // Terminate via WebSocket
            sendWebSocketMessage([
                "event": "terminate",
                "session_id": sessionId
            ])
            
            // Clear session
            self.sessionId = nil
            outputHandlers.removeValue(forKey: sessionId)
            
            completion(.success(()))
        } else {
            // Fall back to HTTP API
            guard let url = URL(string: "\(baseURL)/api/terminal/sessions/\(sessionId)") else {
                completion(.failure(TerminalError.invalidURL))
                return
            }
            
            var request = URLRequest(url: url)
            request.httpMethod = "DELETE"
            
            URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
                guard let self = self else { return }
                
                if let error = error {
                    completion(.failure(TerminalError.networkError(error.localizedDescription)))
                    return
                }
                
                // Clear session regardless of response
                self.sessionId = nil
                self.outputHandlers.removeValue(forKey: sessionId)
                
                completion(.success(()))
            }.resume()
        }
    }
}

// Legacy wrapper class for compatibility
class ProcessUtility {
    static let shared = ProcessUtility()
    private let logger = Debug.shared
    
    private init() {}
    
    /// Executes a shell command on the backend server and returns the output.
    /// - Parameters:
    ///   - command: The shell command to be executed.
    ///   - completion: A closure to be called with the command's output or an error message.
    func executeShellCommand(_ command: String, completion: @escaping (String?) -> Void) {
        var output = ""
        
        logger.log(message: "ProcessUtility executing command: \(command)", type: .info)
        
        TerminalService.shared.executeCommand(command, outputHandler: { newOutput in
            output += newOutput
        }) { result in
            switch result {
            case .success:
                completion(output)
            case .failure(let error):
                completion("Error: \(error.localizedDescription)")
            }
        }
    }
    
    /// Executes a shell command with real-time output streaming.
    /// - Parameters:
    ///   - command: The shell command to be executed.
    ///   - outputHandler: Real-time handler for command output chunks.
    ///   - completion: A closure to be called when the command completes.
    func executeShellCommandWithStreaming(_ command: String, outputHandler: @escaping (String) -> Void, completion: @escaping (String?) -> Void) {
        var fullOutput = ""
        
        logger.log(message: "ProcessUtility executing streaming command: \(command)", type: .info)
        
        TerminalService.shared.executeCommand(command, outputHandler: { newOutput in
            // Send chunk to handler
            outputHandler(newOutput)
            
            // Accumulate for final output
            fullOutput += newOutput
        }) { result in
            switch result {
            case .success:
                completion(fullOutput)
            case .failure(let error):
                completion("Error: \(error.localizedDescription)")
            }
        }
    }
}