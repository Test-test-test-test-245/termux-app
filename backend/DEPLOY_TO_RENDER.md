# Deploying to Render.com

This document provides step-by-step instructions for deploying the Termux Web API to [Render.com](https://render.com).

## Option 1: Deploy Using Docker (Recommended)

### 1. Create a Render Account

If you don't have one yet, sign up for a free account at [Render.com](https://dashboard.render.com/register).

### 2. Fork or Push the Repository to GitHub

Make sure your code is in a GitHub repository that Render can access.

### 3. Create a New Web Service

1. From the Render dashboard, click **New** and select **Web Service**.
2. Connect your GitHub account if you haven't already.
3. Select the repository containing your Termux Web API code.
4. Configure the service:
   - **Name**: `termux-web-api` (or your preferred name)
   - **Environment**: `Docker`
   - **Branch**: `main` (or your default branch)
   - **Region**: Choose the region closest to your users
   - **Instance Type**: Start with "Starter" ($7/month) or "Free" for testing

### 4. Configure Environment Variables (Optional)

Click on **Environment** and add these variables if needed:
- `SECRET_KEY`: A secure random string for session security
- `PORT`: Render sets this automatically, but you can override it
- `INACTIVE_TIMEOUT`: Session cleanup timeout in seconds (default: 3600)

### 5. Create Web Service

Click **Create Web Service**. Render will pull your code, build the Docker image, and deploy it.

## Option 2: Deploy as a Python Service

### 1. Create a New Web Service

1. From the Render dashboard, click **New** and select **Web Service**.
2. Connect your GitHub account if you haven't already.
3. Select the repository containing your code.
4. Configure the service:
   - **Name**: `termux-web-api` (or your preferred name)
   - **Environment**: `Python 3`
   - **Branch**: `main` (or your default branch)
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:$PORT app:app`
   - **Region**: Choose the region closest to your users
   - **Instance Type**: Start with "Starter" ($7/month) or "Free" for testing

### 2. Configure Environment Variables

Same as above.

## Verify Deployment

After deployment completes (usually takes a few minutes):

1. Render will provide you with a URL like `https://termux-web-api.onrender.com`
2. Visit this URL in your browser - you should see the API status page
3. Test the API endpoints:
   - `https://termux-web-api.onrender.com/api/terminal/sessions` (POST to create a session)
   - Connect to the WebSocket at `wss://termux-web-api.onrender.com`

## Connecting Your iOS App

Update your iOS app to use the Render.com URL:

```swift
// Replace with your actual Render.com URL
let apiBaseURL = "https://termux-web-api.onrender.com"
let socketURL = "wss://termux-web-api.onrender.com"

// REST API example
func createSession() {
    let url = URL(string: "\(apiBaseURL)/api/terminal/sessions")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.addValue("application/json", forHTTPHeaderField: "Content-Type")
    
    let parameters: [String: Any] = [
        "shell": "/bin/bash",
        "cols": 80,
        "rows": 24
    ]
    
    request.httpBody = try? JSONSerialization.data(withJSONObject: parameters)
    
    URLSession.shared.dataTask(with: request) { data, response, error in
        // Handle response
    }.resume()
}

// WebSocket connection
// Use SocketIO client library for Swift
```

## Troubleshooting

If you encounter issues:

1. **Service won't start**: Check the deployment logs in the Render dashboard
2. **WebSocket connection fails**: Ensure you're using WSS (secure WebSockets)
3. **File system issues**: Remember that Render's filesystem is ephemeral - use persistent disk if needed
4. **Memory issues**: Upgrade to a larger instance type if you need more resources

## Managing Costs

The free tier will work for testing but has limitations:
- Spins down after 15 minutes of inactivity
- Limited bandwidth and compute

For production use, the Starter plan ($7/month) provides:
- Always-on service
- More resources
- Higher bandwidth limits

## Additional Resources

- [Render Documentation](https://render.com/docs)
- [Python on Render](https://render.com/docs/python)
- [Render Persistent Disk](https://render.com/docs/disks) (for persistent storage)
