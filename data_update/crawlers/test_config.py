import sys
import os

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
from config.config import WebsiteKey

print(WebsiteKey.WINDOWS_MESSAGE_CENTER)
