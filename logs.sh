#!/bin/bash

# File Extractor - Log Viewer Script
# View service logs

LOG_DIR="logs"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

show_menu() {
    echo "=========================================="
    echo "File Extractor - Log Viewer"
    echo "=========================================="
    echo ""
    echo "1) View Main Application log"
    echo "2) View Analysis Service log"
    echo "3) Tail Main Application log (live)"
    echo "4) Tail Analysis Service log (live)"
    echo "5) Show last 50 lines of both logs"
    echo "6) Clear all logs"
    echo "7) Exit"
    echo ""
    read -p "Select option (1-7): " choice
}

while true; do
    show_menu

    case $choice in
        1)
            echo ""
            echo -e "${BLUE}=== Main Application Log ===${NC}"
            echo ""
            if [ -f "$LOG_DIR/main.log" ]; then
                less +G "$LOG_DIR/main.log"
            else
                echo "No log file found"
            fi
            echo ""
            ;;
        2)
            echo ""
            echo -e "${BLUE}=== Analysis Service Log ===${NC}"
            echo ""
            if [ -f "$LOG_DIR/analysis.log" ]; then
                less +G "$LOG_DIR/analysis.log"
            else
                echo "No log file found"
            fi
            echo ""
            ;;
        3)
            echo ""
            echo -e "${BLUE}=== Tailing Main Application Log (Ctrl+C to stop) ===${NC}"
            echo ""
            if [ -f "$LOG_DIR/main.log" ]; then
                tail -f "$LOG_DIR/main.log"
            else
                echo "No log file found"
            fi
            echo ""
            ;;
        4)
            echo ""
            echo -e "${BLUE}=== Tailing Analysis Service Log (Ctrl+C to stop) ===${NC}"
            echo ""
            if [ -f "$LOG_DIR/analysis.log" ]; then
                tail -f "$LOG_DIR/analysis.log"
            else
                echo "No log file found"
            fi
            echo ""
            ;;
        5)
            echo ""
            echo -e "${BLUE}=== Last 50 Lines - Main Application ===${NC}"
            if [ -f "$LOG_DIR/main.log" ]; then
                tail -n 50 "$LOG_DIR/main.log"
            else
                echo "No log file found"
            fi
            echo ""
            echo -e "${BLUE}=== Last 50 Lines - Analysis Service ===${NC}"
            if [ -f "$LOG_DIR/analysis.log" ]; then
                tail -n 50 "$LOG_DIR/analysis.log"
            else
                echo "No log file found"
            fi
            echo ""
            read -p "Press Enter to continue..."
            ;;
        6)
            echo ""
            read -p "Clear all log files? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                > "$LOG_DIR/main.log" 2>/dev/null
                > "$LOG_DIR/analysis.log" 2>/dev/null
                > "$LOG_DIR/file-parser.log" 2>/dev/null
                echo -e "${GREEN}✓${NC} All logs cleared"
            else
                echo "Cancelled"
            fi
            echo ""
            ;;
        7)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo -e "${YELLOW}Invalid option${NC}"
            echo ""
            ;;
    esac
done
