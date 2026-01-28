#!/bin/bash

# File Extractor - Stop Script
# Stops all running services

PID_FILE="data/.service_pids"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Stopping File Extractor Services"
echo "=========================================="
echo ""

if [ ! -f "$PID_FILE" ]; then
    echo -e "${YELLOW}⚠️  No PID file found${NC}"
    echo "   Services may not be running or were started manually"
    echo ""
    echo "Attempting to stop any running instances..."
    pkill -f "run_analysis.py" 2>/dev/null
    pkill -f "run_main.py" 2>/dev/null
    echo -e "${GREEN}✓${NC} Cleanup complete"
    exit 0
fi

# Read PIDs
ANALYSIS_PID=$(head -n 1 "$PID_FILE" 2>/dev/null)
MAIN_PID=$(tail -n 1 "$PID_FILE" 2>/dev/null)

# Stop Analysis Service
if [ ! -z "$ANALYSIS_PID" ] && kill -0 "$ANALYSIS_PID" 2>/dev/null; then
    echo "Stopping Analysis Service (PID: $ANALYSIS_PID)..."
    kill "$ANALYSIS_PID" 2>/dev/null
    sleep 1

    # Force kill if still running
    if kill -0 "$ANALYSIS_PID" 2>/dev/null; then
        kill -9 "$ANALYSIS_PID" 2>/dev/null
    fi
    echo -e "${GREEN}✓${NC} Analysis service stopped"
else
    echo -e "${YELLOW}⚠${NC} Analysis service not running"
fi

# Stop Main Application
if [ ! -z "$MAIN_PID" ] && kill -0 "$MAIN_PID" 2>/dev/null; then
    echo "Stopping Main Application (PID: $MAIN_PID)..."
    kill "$MAIN_PID" 2>/dev/null
    sleep 1

    # Force kill if still running
    if kill -0 "$MAIN_PID" 2>/dev/null; then
        kill -9 "$MAIN_PID" 2>/dev/null
    fi
    echo -e "${GREEN}✓${NC} Main application stopped"
else
    echo -e "${YELLOW}⚠${NC} Main application not running"
fi

# Cleanup any remaining processes
pkill -f "run_analysis.py" 2>/dev/null
pkill -f "run_main.py" 2>/dev/null

# Remove PID file
rm -f "$PID_FILE"

echo ""
echo -e "${GREEN}✅ All services stopped${NC}"
echo ""
