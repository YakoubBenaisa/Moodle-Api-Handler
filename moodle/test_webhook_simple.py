#!/usr/bin/env python
"""
A very simple script to test the webhook functionality.
This script bypasses Django and Celery completely and just sends a direct HTTP request.

Run this script from the command line:
python moodle/test_webhook_simple.py
"""

import requests
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Webhook URL and token
WEBHOOK_URL = "http://127.0.0.1:8001/api/webhook/moodle-notification"
WEBHOOK_TOKEN = "moodle-notification-secret"

def test_webhook():
    """Send a simple test notification to the webhook."""
    logger.info(f"Testing webhook URL: {WEBHOOK_URL}")
    
    # Create a simple test payload
    payload = {
        'notification_id': f"simple-test-{datetime.now().timestamp()}",
        'message': "This is a simple test notification",
        'aria_label': "Simple Test",
        'timestamp': datetime.now().isoformat(),
        'token': WEBHOOK_TOKEN
    }
    
    logger.info(f"Sending payload: {json.dumps(payload, indent=2)}")
    
    try:
        # Send the request
        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            timeout=5
        )
        
        # Log the response
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response content: {response.text[:200]}")
        
        if response.status_code >= 200 and response.status_code < 300:
            logger.info("Webhook test successful!")
            return True
        else:
            logger.error(f"Webhook test failed with status code: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error testing webhook: {e}")
        return False

if __name__ == "__main__":
    success = test_webhook()
    if success:
        print("\n✅ Webhook test successful!")
    else:
        print("\n❌ Webhook test failed. Check the logs for details.")
