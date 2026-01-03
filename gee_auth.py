#!/usr/bin/env python3
"""
Google Earth Engine Authentication Helper
==========================================

Handles GEE authentication with multiple fallback methods:
1. Service account (if SERVICE_ACCOUNT_KEY env var or file exists)
2. Existing credentials (from previous `earthengine authenticate`)
3. Application Default Credentials (from gcloud)

Service Account Setup:
1. Go to https://console.cloud.google.com/iam-admin/serviceaccounts
2. Create a service account in your GEE-enabled project
3. Grant it "Earth Engine Resource Viewer" role
4. Create a JSON key and save as `service_account.json` in this directory
   OR set SERVICE_ACCOUNT_KEY environment variable to the JSON content
5. Register the service account email at https://signup.earthengine.google.com/

Usage:
    from gee_auth import init_ee
    init_ee()  # Handles all auth automatically
"""

import ee
import os
import json
from pathlib import Path

PROJECT_ID = 'gen-lang-client-0866285082'
SERVICE_ACCOUNT_FILE = 'service_account.json'


def init_ee(project_id=None):
    """Initialize Earth Engine with automatic credential handling.
    
    Tries in order:
    1. Service account from file or environment
    2. Existing persistent credentials
    3. Application Default Credentials
    """
    project = project_id or PROJECT_ID
    
    # Method 1: Service account from environment variable
    sa_key_env = os.environ.get('SERVICE_ACCOUNT_KEY')
    if sa_key_env:
        try:
            key_data = json.loads(sa_key_env)
            credentials = ee.ServiceAccountCredentials(
                key_data['client_email'],
                key_data=sa_key_env
            )
            ee.Initialize(credentials=credentials, project=project)
            print(f"GEE initialized with service account: {key_data['client_email']}")
            return True
        except Exception as e:
            print(f"Service account from env failed: {e}")
    
    # Method 2: Service account from file
    sa_file = Path(__file__).parent / SERVICE_ACCOUNT_FILE
    if sa_file.exists():
        try:
            with open(sa_file) as f:
                key_data = json.load(f)
            credentials = ee.ServiceAccountCredentials(
                key_data['client_email'],
                key_file=str(sa_file)
            )
            ee.Initialize(credentials=credentials, project=project)
            print(f"GEE initialized with service account: {key_data['client_email']}")
            return True
        except Exception as e:
            print(f"Service account from file failed: {e}")
    
    # Method 3: Existing credentials or ADC
    try:
        ee.Initialize(project=project)
        print("GEE initialized with existing credentials")
        return True
    except ee.EEException as e:
        if "Please authorize" in str(e):
            print("\nNo valid credentials found. Options:")
            print("1. Run: python3 -c \"import ee; ee.Authenticate()\"")
            print("2. Add service_account.json to this directory")
            print("3. Set SERVICE_ACCOUNT_KEY environment variable")
            raise
        raise


def test_connection():
    """Test that GEE connection is working."""
    try:
        # Simple test query
        image = ee.Image('USGS/SRTMGL1_003')
        info = image.getInfo()
        print(f"GEE connection test: OK (SRTM bands: {len(info['bands'])})")
        return True
    except Exception as e:
        print(f"GEE connection test failed: {e}")
        return False


if __name__ == '__main__':
    print("Testing GEE authentication...")
    init_ee()
    test_connection()
