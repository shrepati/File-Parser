#!/bin/bash
# Setup script for File Extractor - AI-Powered Test Analysis Platform

echo "====================================="
echo "File Extractor - Setup"
echo "AI-Powered Test Analysis Platform"
echo "====================================="
echo ""

# Install base requirements
echo "Installing base dependencies..."
python3 -m pip install --user -r requirements/base.txt

# Install analysis service dependencies
echo "Installing AI analysis dependencies..."
python3 -m pip install --user -r requirements/analysis.txt

echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your API keys for AI features:"
    echo "   - GEMINI_API_KEY (get from: https://makersuite.google.com/app/apikey)"
    echo "   - CLAUDE_API_KEY (get from: https://console.anthropic.com/)"
    echo ""
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p data logs uploads extracted

# Initialize database
echo "Initializing database..."
python3 -c "from app.database import init_db; init_db(); print('Database initialized successfully!')"

echo ""
echo "====================================="
echo "✅ Setup complete!"
echo "====================================="
echo ""
echo "To start the application:"
echo "  ./start.sh"
echo ""
echo "Or manually start both services:"
echo "  Terminal 1: python3 run_main.py"
echo "  Terminal 2: python3 run_analysis.py"
echo ""
echo "Then open: http://localhost:5000"
echo ""
