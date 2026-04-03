import sys
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.expanduser('~'), 'sc-toolkit', '.env'))

# Add your project directory to sys.path
path = '/home/brfrancis/sc-toolkit'
if path not in sys.path:
    sys.path.append(path)

from app import app as application
