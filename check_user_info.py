#!/usr/bin/env python3
"""
Check what user information the Bitbucket API returns
"""

import os
import requests
import base64
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_user_info():
    """Check user information from Bitbucket API"""
    
    print("🔍 Checking Bitbucket User Information")
    print("=" * 50)
    
    # Get credentials from environment
    BITBUCKET_TOKEN = os.getenv("BITBUCKET_TOKEN", "")
    BITBUCKET_EMAIL = os.getenv("BITBUCKET_EMAIL", "")
    
    print(f"📧 Email from .env: {BITBUCKET_EMAIL}")
    
    # Authenticate
    credentials = f"{BITBUCKET_EMAIL}:{BITBUCKET_TOKEN}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Accept": "application/json"
    }
    
    try:
        # Get user information
        print(f"\n🔐 Calling: https://api.bitbucket.org/2.0/user")
        response = requests.get(
            "https://api.bitbucket.org/2.0/user",
            headers=headers,
            timeout=10
        )
        
        print(f"📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"\n✅ Full API Response:")
            print(json.dumps(user_data, indent=2))
            
            print(f"\n📋 Key Information:")
            print(f"👤 Username: {user_data.get('username', 'N/A')}")
            print(f"📛 Display Name: {user_data.get('display_name', 'N/A')}")
            print(f"🆔 Account ID: {user_data.get('account_id', 'N/A')}")
            print(f"🔗 UUID: {user_data.get('uuid', 'N/A')}")
            
            print(f"\n💡 This username '{user_data.get('username')}' is what your Bitbucket account is registered as.")
            
        else:
            print(f"❌ Failed to get user info: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    check_user_info()
