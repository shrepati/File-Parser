#!/usr/bin/env python3
"""
Analysis Service Entry Point
Runs the FastAPI analysis service for AI-powered test failure analysis
"""

import os
import uvicorn

if __name__ == '__main__':
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("Warning: python-dotenv not installed. Using system environment variables.")

    print("=" * 70)
    print("File Extractor - Analysis Service")
    print("AI-Powered Test Failure Analysis")
    print("=" * 70)
    print(f"Gemini API Key: {'✓ Configured' if os.getenv('GEMINI_API_KEY') else '✗ Not set'}")
    print(f"Claude API Key: {'✓ Configured' if os.getenv('CLAUDE_API_KEY') else '✗ Not set'}")
    print(f"MCP Server: {os.getenv('MCP_SERVER_URL', 'Not configured')}")
    print(f"Starting analysis service on http://localhost:8001")
    print("=" * 70)
    print()

    # Run FastAPI with uvicorn
    uvicorn.run(
        "analysis_service.server:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
