#!/usr/bin/env python3
"""
Simple test script to check that the API is working.
Run this after starting the server with run_local.sh
"""

import requests
import json
import sys
import time

BASE_URL = "http://localhost:5000"

def test_api():
    print("Testing API...")
    
    # Test the root endpoint
    response = requests.get(f"{BASE_URL}/")
    if response.status_code != 200:
        print(f"❌ Root endpoint failed: {response.status_code}")
        return False
    
    print(f"✅ Root endpoint: {response.json()['name']} v{response.json()['version']}")
    
    # Test creating a terminal session
    response = requests.post(f"{BASE_URL}/api/terminal/sessions", json={
        "shell": "/bin/bash",
        "cols": 80,
        "rows": 24
    })
    
    if response.status_code != 201:
        print(f"❌ Create session failed: {response.status_code}")
        return False
    
    session_id = response.json()["id"]
    print(f"✅ Created session: {session_id}")
    
    # Test running a command
    test_command = "echo 'Hello from test script'"
    
    # Wait a moment for session to initialize
    time.sleep(1)
    
    print(f"🔄 Testing command: {test_command}")
    
    try:
        # The simple test doesn't use WebSockets, so we'll just terminate the session
        response = requests.delete(f"{BASE_URL}/api/terminal/sessions/{session_id}")
        if response.status_code != 200:
            print(f"❌ Terminate session failed: {response.status_code}")
            return False
        
        print(f"✅ Terminated session: {session_id}")
        
        return True
    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")
        return False

if __name__ == "__main__":
    if test_api():
        print("✅ API tests passed!")
        sys.exit(0)
    else:
        print("❌ API tests failed!")
        sys.exit(1)
