#!/bin/bash

# File Extractor - Improved Startup Script
# Runs both services in the background with proper logging

PID_FILE="data/.service_pids"
LOG_DIR="logs"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "File Extractor - AI-Powered Platform"
echo "=========================================="
echo ""

# Check if services are already running
if [ -f "$PID_FILE" ]; then
    echo -e "${YELLOW}⚠️  Services may already be running${NC}"
    echo "   Run './status.sh' to check or './stop.sh' to stop them first"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
    echo ""
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  Warning: .env file not found!${NC}"
    echo "   Run './setup.sh' first to configure the application"
    echo ""
    read -p "Continue without AI features? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
    echo ""
fi

# Create log directory
mkdir -p "$LOG_DIR"

# Start Analysis Service
echo -e "${BLUE}Starting AI Analysis Service...${NC}"
nohup python3 run_analysis.py > "$LOG_DIR/analysis.log" 2>&1 &
ANALYSIS_PID=$!
sleep 2

# Check if analysis service started
if ! kill -0 $ANALYSIS_PID 2>/dev/null; then
    echo -e "${RED}❌ Failed to start analysis service${NC}"
    echo "   Check $LOG_DIR/analysis.log for errors"
    exit 1
fi

echo -e "${GREEN}✓${NC} Analysis service started (PID: $ANALYSIS_PID, Port: 8001)"

# Start Main Application
echo -e "${BLUE}Starting Main Application...${NC}"
nohup python3 run_main.py > "$LOG_DIR/main.log" 2>&1 &
MAIN_PID=$!
sleep 3

# Check if main app started
if ! kill -0 $MAIN_PID 2>/dev/null; then
    echo -e "${RED}❌ Failed to start main application${NC}"
    echo "   Stopping analysis service..."
    kill $ANALYSIS_PID 2>/dev/null
    echo "   Check $LOG_DIR/main.log for errors"
    exit 1
fi

echo -e "${GREEN}✓${NC} Main application started (PID: $MAIN_PID, Port: 5000)"

# Save PIDs
echo "$ANALYSIS_PID" > "$PID_FILE"
echo "$MAIN_PID" >> "$PID_FILE"

echo ""
echo "=========================================="
echo -e "${GREEN}✅ All services started successfully!${NC}"
echo "=========================================="
echo ""
echo -e "🌐 ${BLUE}Access the application at:${NC}"
echo "   http://localhost:5000"
echo ""
echo -e "📋 ${BLUE}Available features:${NC}"
echo "   • File upload & extraction"
echo "   • RHOSO test analysis"
echo "   • AI-powered failure insights"
echo ""
echo -e "📊 ${BLUE}Management commands:${NC}"
echo "   ./status.sh  - Check service status"
echo "   ./stop.sh    - Stop all services"
echo "   ./logs.sh    - View service logs"
echo ""
echo -e "📝 ${BLUE}Log files:${NC}"
echo "   $LOG_DIR/main.log      - Main application"
echo "   $LOG_DIR/analysis.log  - Analysis service"
echo ""
echo "=========================================="
