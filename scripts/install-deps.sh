#!/bin/bash
set -e

echo "Installing Python dependencies..."
pip install -q Flask==3.0.3 requests>=2.31.0 python-dotenv

echo "Dependencies installed successfully!"
