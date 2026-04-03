import sys
import os

# Add your project directory to sys.path
path = '/home/yourusername/sc-toolkit'  # ← update with your PythonAnywhere username
if path not in sys.path:
    sys.path.append(path)

from app import app as application
