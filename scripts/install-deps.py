#!/usr/bin/env python3
import subprocess
import sys

print("Installing Python dependencies...")
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "Flask==3.0.3", "requests>=2.31.0", "python-dotenv"])
print("Dependencies installed successfully!")
