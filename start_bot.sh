#!/bin/bash

# Apple Notes Research Bot - Quick Start Script
# This script starts the bot with proper environment setup

echo "🪸 CoralCollective Apple Notes Research Bot"
echo "========================================="
echo ""

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Loaded environment variables from .env"
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    ./venv/bin/pip install -r apple_notes_research_bot/requirements.txt
    echo "✅ Virtual environment created and dependencies installed"
fi

# Start the bot
echo ""
echo "🚀 Starting Apple Notes Research Bot..."
echo "   - Monitoring your Apple Notes for research opportunities"
echo "   - Press Ctrl+C to stop the bot"
echo ""

./venv/bin/python -m apple_notes_research_bot