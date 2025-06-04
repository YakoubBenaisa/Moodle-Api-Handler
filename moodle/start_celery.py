#!/usr/bin/env python
"""
Script to start Celery worker with the correct configuration.
Run this script from the Django project root directory:

python moodle/start_celery.py

"""
import os
import sys
import subprocess

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moodle.settings')

# Start the Celery worker
print("Starting Celery worker...")
subprocess.call(['celery', '-A', 'moodle', 'worker', '-l', 'info'])
