# WSGI entry point for the application
import sys
import os

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Now import the app
from main import app as application

# Make the app available for Gunicorn
app = application 