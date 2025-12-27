"""
Vercel serverless function entry point for Flask app
"""
import sys
from pathlib import Path

# Add the parent directory to the Python path so we can import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app import app

# This is the WSGI application Vercel will use
# Vercel expects a variable called 'app' or a function called 'handler'
application = app

# Optional: Vercel handler function
def handler(event, context):
    """
    AWS Lambda-style handler for Vercel
    """
    return application
