//
//  TerminalServiceWebDAV.swift
//  iOS client update with WebDAV support
//

import Foundation
import UIKit

// MARK: - WebDAV Extensions for TerminalService

extension TerminalService {
    
    // MARK: - WebDAV Models
    
    struct WebDAVCredentials: Codable {
        let url: String
        let username: String
        let password: String
        let protocol: String
    }
    
    struct WebDAVResponse: Codable {
        let credentials: WebDAVCredentials
        let instructions: [String]
        let clients: WebDAVClients?
    }
    
    struct WebDAVClients: Codable {
        let ios: [String]?
        let macos: [String]?
        let windows: [String]?
        let android: [String]?
    }
    
    // MARK: - WebDAV Methods
    
    /// Fetches WebDAV credentials for the current session
    /// - Parameter completion: Called with the WebDAV credentials or an error
    func getWebDAVCredentials(completion: @escaping (TerminalResult<WebDAVCredentials>) -> Void) {
        logger.log(message: "Fetching WebDAV credentials", type: .info)
        
        // First ensure we have a valid session
        createSession { [weak self] result in
            guard let self = self else { return }
            
            switch result {
            case .success(let sessionId):
                // We have a valid session, now get the WebDAV credentials
                self.fetchWebDAVCredentials(sessionId: sessionId, completion: completion)
            case .failure(let error):
                self.logger.log(message: "Failed to get session for WebDAV credentials", type: .error)
                completion(.failure(error))
            }
        }
    }
    
    private func fetchWebDAVCredentials(sessionId: String, completion: @escaping (TerminalResult<WebDAVCredentials>) -> Void) {
        guard let url = URL(string: "\(baseURL)/api/webdav/credentials?session_id=\(sessionId)") else {
            logger.log(message: "Invalid URL for WebDAV credentials", type: .error)
            completion(.failure(TerminalError.invalidURL))
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            guard let self = self else { return }
            
            if let error = error {
                self.logger.log(message: "Network error fetching WebDAV credentials: \(error.localizedDescription)", type: .error)
                completion(.failure(TerminalError.networkError(error.localizedDescription)))
                return
            }
            
            guard let data = data else {
                self.logger.log(message: "No data received for WebDAV credentials", type: .error)
                completion(.failure(TerminalError.responseError("No data received")))
                return
            }
            
            do {
                let webDAVResponse = try JSONDecoder().decode(WebDAVResponse.self, from: data)
                self.logger.log(message: "WebDAV credentials received successfully", type: .info)
                completion(.success(webDAVResponse.credentials))
            } catch {
                self.logger.log(message: "Error parsing WebDAV credentials: \(error.localizedDescription)", type: .error)
                completion(.failure(TerminalError.parseError("Could not parse WebDAV credentials")))
            }
        }.resume()
    }
    
    /// Opens the Files app or appropriate WebDAV client with the session files
    /// - Parameter viewController: The view controller to present from
    /// - Parameter completion: Called when the operation completes
    func openTerminalFiles(from viewController: UIViewController, completion: @escaping (TerminalResult<Void>) -> Void) {
        getWebDAVCredentials { result in
            switch result {
            case .success(let credentials):
                self.openWebDAVLocation(credentials: credentials, from: viewController, completion: completion)
            case .failure(let error):
                completion(.failure(error))
            }
        }
    }
    
    /// Opens the WebDAV location in the appropriate app
    /// - Parameters:
    ///   - credentials: The WebDAV credentials
    ///   - viewController: The view controller to present from
    ///   - completion: Called when the operation completes
    private func openWebDAVLocation(credentials: WebDAVCredentials, from viewController: UIViewController, completion: @escaping (TerminalResult<Void>) -> Void) {
        
        // Create WebDAV URL - need to encode credentials in the URL for auto-login
        guard var urlComponents = URLComponents(string: credentials.url) else {
            completion(.failure(TerminalError.invalidURL))
            return
        }
        
        // Add the username and password to the URL for auto-login
        urlComponents.user = credentials.username
        urlComponents.password = credentials.password
        
        guard let webdavURL = urlComponents.url else {
            completion(.failure(TerminalError.invalidURL))
            return
        }
        
        // Create a temporary bookmark file to help iOS discover this is a WebDAV URL
        createTemporaryWebDAVBookmark(for: webdavURL) { result in
            switch result {
            case .success(let fileURL):
                // Open the bookmark file - iOS will recognize it and open Files app
                DispatchQueue.main.async {
                    if UIApplication.shared.canOpenURL(fileURL) {
                        UIApplication.shared.open(fileURL, options: [:]) { success in
                            if success {
                                self.logger.log(message: "Opened WebDAV bookmark successfully", type: .info)
                                completion(.success(()))
                            } else {
                                self.logger.log(message: "Failed to open WebDAV bookmark", type: .error)
                                completion(.failure(TerminalError.responseError("Failed to open WebDAV location")))
                            }
                        }
                    } else {
                        // Fallback: Try to open the Files app directly
                        let filesAppURL = URL(string: "shareddocuments://")!
                        if UIApplication.shared.canOpenURL(filesAppURL) {
                            UIApplication.shared.open(filesAppURL, options: [:]) { _ in
                                // Show alert with instructions
                                self.showWebDAVInstructions(credentials: credentials, on: viewController)
                                completion(.success(()))
                            }
                        } else {
                            self.showWebDAVInstructions(credentials: credentials, on: viewController)
                            completion(.success(()))
                        }
                    }
                }
            case .failure(let error):
                completion(.failure(error))
            }
        }
    }
    
    /// Creates a temporary bookmark file for WebDAV
    private func createTemporaryWebDAVBookmark(for url: URL, completion: @escaping (TerminalResult<URL>) -> Void) {
        let tempDir = FileManager.default.temporaryDirectory
        let bookmarkFile = tempDir.appendingPathComponent("webdav_bookmark.webdavloc")
        
        let bookmarkContent = """
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
        <dict>
            <key>URL</key>
            <string>\(url.absoluteString)</string>
        </dict>
        </plist>
        """
        
        do {
            try bookmarkContent.write(to: bookmarkFile, atomically: true, encoding: .utf8)
            completion(.success(bookmarkFile))
        } catch {
            logger.log(message: "Error creating WebDAV bookmark: \(error.localizedDescription)", type: .error)
            completion(.failure(TerminalError.responseError("Failed to create WebDAV bookmark")))
        }
    }
    
    /// Shows WebDAV instructions in an alert
    private func showWebDAVInstructions(credentials: WebDAVCredentials, on viewController: UIViewController) {
        DispatchQueue.main.async {
            // Create alert with credential details
            let alert = UIAlertController(
                title: "Connect to WebDAV Files",
                message: """
                Use these credentials in the Files app:
                
                URL: \(credentials.url)
                Username: \(credentials.username)
                Password: \(credentials.password)
                
                1. Open the Files app
                2. Tap Browse > Three dots > Connect to Server
                3. Enter the URL and credentials above
                """,
                preferredStyle: .alert
            )
            
            // Add copy buttons for easy copying
            alert.addAction(UIAlertAction(title: "Copy URL", style: .default) { _ in
                UIPasteboard.general.string = credentials.url
            })
            
            alert.addAction(UIAlertAction(title: "Copy Username", style: .default) { _ in
                UIPasteboard.general.string = credentials.username
            })
            
            alert.addAction(UIAlertAction(title: "Copy Password", style: .default) { _ in
                UIPasteboard.general.string = credentials.password
            })
            
            alert.addAction(UIAlertAction(title: "Open Files App", style: .default) { _ in
                let filesAppURL = URL(string: "shareddocuments://")!
                if UIApplication.shared.canOpenURL(filesAppURL) {
                    UIApplication.shared.open(filesAppURL, options: [:], completionHandler: nil)
                }
            })
            
            alert.addAction(UIAlertAction(title: "Close", style: .cancel))
            
            viewController.present(alert, animated: true)
        }
    }
}

// MARK: - Usage Example in Your View Controller

class YourViewController: UIViewController {
    
    @IBOutlet weak var terminalView: UIView!
    @IBOutlet weak var viewFilesButton: UIButton!
    
    override func viewDidLoad() {
        super.viewDidLoad()
        setupUI()
    }
    
    private func setupUI() {
        // Configure the "View Files" button
        viewFilesButton.setTitle("View Terminal Files", for: .normal)
        viewFilesButton.backgroundColor = .systemBlue
        viewFilesButton.layer.cornerRadius = 8
        viewFilesButton.addTarget(self, action: #selector(viewFilesButtonTapped), for: .touchUpInside)
    }
    
    @objc private func viewFilesButtonTapped() {
        // Show loading indicator
        let activityIndicator = UIActivityIndicatorView(style: .medium)
        activityIndicator.center = viewFilesButton.center
        activityIndicator.startAnimating()
        view.addSubview(activityIndicator)
        
        // Open terminal files
        TerminalService.shared.openTerminalFiles(from: self) { [weak self] result in
            guard let self = self else { return }
            
            DispatchQueue.main.async {
                activityIndicator.removeFromSuperview()
                
                switch result {
                case .success:
                    Debug.shared.log(message: "Successfully opened terminal files", type: .info)
                case .failure(let error):
                    Debug.shared.log(message: "Failed to open terminal files: \(error.localizedDescription)", type: .error)
                    
                    // Show error alert
                    let alert = UIAlertController(
                        title: "Error Opening Files",
                        message: "Could not open terminal files. Please try again.",
                        preferredStyle: .alert
                    )
                    alert.addAction(UIAlertAction(title: "OK", style: .default))
                    self.present(alert, animated: true)
                }
            }
        }
    }
}
