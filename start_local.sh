#!/bin/bash

# Score Handler Local Development Setup
echo "🔧 Setting up Retrieval Handler for local development..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate
echo python --version
python -m pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

echo "✅ Setup complete!"

# Start the local server
python run_local.py