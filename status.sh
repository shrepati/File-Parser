#!/bin/bash

# File Extractor - Status Script
# Check if services are running

PID_FILE="data/.service_pids"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "File Extractor - Service Status"
echo "=========================================="
echo ""

ANALYSIS_RUNNING=false
MAIN_RUNNING=false

# Check using PID file
if [ -f "$PID_FILE" ]; then
    ANALYSIS_PID=$(head -n 1 "$PID_FILE" 2>/dev/null)
    MAIN_PID=$(tail -n 1 "$PID_FILE" 2>/dev/null)

    # Check Analysis Service
    if [ ! -z "$ANALYSIS_PID" ] && kill -0 "$ANALYSIS_PID" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Analysis Service: ${GREEN}Running${NC} (PID: $ANALYSIS_PID)"
        ANALYSIS_RUNNING=true
    else
        echo -e "${RED}✗${NC} Analysis Service: ${RED}Stopped${NC}"
    fi

    # Check Main Application
    if [ ! -z "$MAIN_PID" ] && kill -0 "$MAIN_PID" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Main Application: ${GREEN}Running${NC} (PID: $MAIN_PID)"
        MAIN_RUNNING=true
    else
        echo -e "${RED}✗${NC} Main Application: ${RED}Stopped${NC}"
    fi
else
    echo -e "${YELLOW}⚠${NC} No PID file found - checking processes..."
    echo ""

    # Check by process name
    if pgrep -f "run_analysis.py" > /dev/null; then
        PID=$(pgrep -f "run_analysis.py" | head -n 1)
        echo -e "${GREEN}✓${NC} Analysis Service: ${GREEN}Running${NC} (PID: $PID)"
        ANALYSIS_RUNNING=true
    else
        echo -e "${RED}✗${NC} Analysis Service: ${RED}Stopped${NC}"
    fi

    if pgrep -f "run_main.py" > /dev/null; then
        PID=$(pgrep -f "run_main.py" | head -n 1)
        echo -e "${GREEN}✓${NC} Main Application: ${GREEN}Running${NC} (PID: $PID)"
        MAIN_RUNNING=true
    else
        echo -e "${RED}✗${NC} Main Application: ${RED}Stopped${NC}"
    fi
fi

echo ""

# Check ports
echo -e "${BLUE}Port Status:${NC}"
if ss -tuln 2>/dev/null | grep -q ":5000 "; then
    echo -e "${GREEN}✓${NC} Port 5000: In use (Main App)"
else
    echo -e "${RED}✗${NC} Port 5000: Free"
fi

if ss -tuln 2>/dev/null | grep -q ":8001 "; then
    echo -e "${GREEN}✓${NC} Port 8001: In use (Analysis Service)"
else
    echo -e "${RED}✗${NC} Port 8001: Free"
fi

echo ""

# Overall status
if [ "$ANALYSIS_RUNNING" = true ] && [ "$MAIN_RUNNING" = true ]; then
    echo -e "${GREEN}✅ All services are running${NC}"
    echo ""
    echo "Access the application at: http://localhost:5000"
elif [ "$ANALYSIS_RUNNING" = false ] && [ "$MAIN_RUNNING" = false ]; then
    echo -e "${RED}❌ All services are stopped${NC}"
    echo ""
    echo "Run './start.sh' to start services"
else
    echo -e "${YELLOW}⚠️  Partial service status${NC}"
    echo ""
    echo "Some services are not running. Run './stop.sh' then './start.sh'"
fi

echo ""
echo "=========================================="
