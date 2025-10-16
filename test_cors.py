#!/usr/bin/env python3
"""
CORS Test Script for SwinSACA

This script tests the CORS configuration to ensure the frontend can communicate with the backend.
"""

import requests
import json

def test_cors():
    """Test CORS configuration"""
    base_url = "http://localhost:5000"
    
    print("Testing CORS configuration...")
    print("=" * 50)
    
    # Test 1: Health endpoint
    try:
        response = requests.get(f"{base_url}/health")
        print(f"✅ Health endpoint: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ Health endpoint failed: {e}")
    
    print()
    
    # Test 2: CORS test endpoint
    try:
        headers = {
            'Origin': 'http://localhost:5173',
            'Content-Type': 'application/json'
        }
        response = requests.get(f"{base_url}/cors-test", headers=headers)
        print(f"✅ CORS test endpoint: {response.status_code}")
        print(f"   Response: {response.json()}")
        print(f"   CORS headers: {dict(response.headers)}")
    except Exception as e:
        print(f"❌ CORS test endpoint failed: {e}")
    
    print()
    
    # Test 3: Chat endpoint (preflight)
    try:
        headers = {
            'Origin': 'http://localhost:5173',
            'Content-Type': 'application/json',
            'X-Language': 'english',
            'X-Mode': 'text'
        }
        response = requests.options(f"{base_url}/api/chat/", headers=headers)
        print(f"✅ Chat endpoint preflight: {response.status_code}")
        print(f"   CORS headers: {dict(response.headers)}")
    except Exception as e:
        print(f"❌ Chat endpoint preflight failed: {e}")
    
    print()
    
    # Test 4: Chat endpoint (actual request)
    try:
        headers = {
            'Origin': 'http://localhost:5173',
            'Content-Type': 'application/json',
            'X-Language': 'english',
            'X-Mode': 'text'
        }
        data = {
            'message': 'Hello, this is a test message',
            'reset': False,
            '_context': {
                'language': 'english',
                'mode': 'text'
            }
        }
        response = requests.post(f"{base_url}/api/chat/", 
                               headers=headers, 
                               json=data)
        print(f"✅ Chat endpoint: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
        else:
            print(f"   Error: {response.text}")
        print(f"   CORS headers: {dict(response.headers)}")
    except Exception as e:
        print(f"❌ Chat endpoint failed: {e}")
    
    print()
    print("CORS test completed!")

if __name__ == "__main__":
    test_cors()
