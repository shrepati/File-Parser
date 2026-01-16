#!/bin/bash
# Setup script for File Extractor

echo "====================================="
echo "File Extractor - Setup"
echo "====================================="
echo ""

# Install base requirements
echo "Installing Python dependencies..."
python3 -m pip install --user -r requirements/base.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env and add your API keys if using AI features"
fi

# Create data directory
mkdir -p data

# Initialize database
echo "Initializing database..."
python3 -c "from app.database import init_db; init_db(); print('Database initialized successfully!')"

echo ""
echo "====================================="
echo "Setup complete!"
echo "====================================="
echo ""
echo "To start the application:"
echo "  python3 run_main.py"
echo ""
echo "Or use the old server (will be replaced):"
echo "  python3 server.py"
echo ""
