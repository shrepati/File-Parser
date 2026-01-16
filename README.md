# 📦 File Extractor - AI-Powered Test Analysis Platform

A modern web application for uploading, extracting, and browsing archive files with **AI-powered RHOSO test failure analysis**. Built with Flask, FastAPI, and multiple AI backends (Gemini, Claude, MCP).

## ✨ Features

### Core File Management
- **📁 File Upload & Extraction**
  - Drag & drop or browse to upload archives (up to 2GB)
  - Support for ZIP, TAR, TAR.GZ, TGZ, BZ2, XZ, RAR, 7Z formats
  - Real-time extraction progress with percentage tracking
  - Secure handling of symlinks and absolute paths

- **🔍 Smart Search**
  - Full-text search across file names and content
  - File type filtering
  - Fast indexed search with pagination

- **🌳 Tree View**
  - Hierarchical directory visualization
  - Collapsible/expandable folders
  - Navigate complex directory structures easily

- **📄 File Viewer**
  - In-browser preview for text files (up to 5MB)
  - Syntax highlighting with monospace font
  - Download any file with one click

### 🤖 AI-Powered Test Analysis (NEW!)

#### RHOSO Test Results Analysis
- **Automatic Discovery**: Finds all `rhoso*` folders in uploaded archives
- **Smart Parsing**: Extracts test results from `tempest_results.html` and `tempest_results.xml`
- **Must-Gather Correlation**: Links test failures to relevant must-gather logs

#### Multi-Backend AI Support
Choose from multiple AI providers:
- **Google Gemini 1.5 Pro** - Fast, high-quality analysis
- **Anthropic Claude 3.5 Sonnet** - Deep reasoning and context understanding
- **MCP Server Integration** - Connect to custom Model Context Protocol servers

#### Interactive Features
- **📊 Test Summary Cards**: Visual breakdown of passed/failed/skipped tests
- **📋 Expandable Failure Boxes**: Click to see detailed error messages, tracebacks, and correlated logs
- **✨ AI Analysis**: Get AI-powered insights on failure patterns and root causes
- **💬 Interactive Chat**: Ask questions about specific failures in real-time
- **🌊 Streaming Responses**: See AI analysis appear in real-time as it's generated

## 🏗️ Architecture

### Microservices Design
```
┌─────────────────────┐         ┌──────────────────────┐
│   Flask Main App    │         │   FastAPI Analysis   │
│   (Port 5000)       │◄────────┤   Service (8001)     │
│                     │         │                      │
│ - File Upload       │         │ - Tempest Parsing    │
│ - Extraction        │         │ - AI Plugin System   │
│ - Search/Browse     │         │ - Gemini/Claude/MCP  │
│ - Tree View         │         │ - Chat Interface     │
└─────────────────────┘         └──────────────────────┘
         │                                │
         ▼                                ▼
    SQLite DB                      Plugin Registry
    (Jobs, Files,                  (AI Backends)
     Metadata)
```

### AI Plugin System
```
┌─────────────────────────────────────────┐
│         Plugin Registry                 │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────┐  ┌──────────┐  ┌───────┐│
│  │ Gemini   │  │ Claude   │  │  MCP  ││
│  │ Plugin   │  │ Plugin   │  │Plugin ││
│  └──────────┘  └──────────┘  └───────┘│
│                                         │
│  All implement AIBackendPlugin interface│
└─────────────────────────────────────────┘
```

## 📋 Prerequisites

- Python 3.8 or higher
- pip package manager
- At least one AI API key (Gemini, Claude, or MCP server)

## 🚀 Installation

### 1. Clone or Download

```bash
cd /path/to/File-Parser
```

### 2. Create Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Main Flask app dependencies
pip install -r requirements/base.txt

# Analysis service dependencies (includes AI SDKs)
pip install -r requirements/analysis.txt
```

### 4. Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit .env and add your AI API keys
nano .env  # or use your favorite editor
```

**Required Configuration:**
```bash
# Get Gemini API key from: https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your-actual-gemini-key

# OR get Claude API key from: https://console.anthropic.com/
CLAUDE_API_KEY=your-actual-claude-key

# OR configure MCP server
MCP_SERVER_URL=http://your-mcp-server:9000
```

### 5. Initialize Database

```bash
# Database tables are auto-created on first run
# Ensure data/ directory exists
mkdir -p data logs uploads extracted
```

## 🎯 Running the Application

### Option 1: Run Both Services (Full Features)

**Terminal 1 - Main Flask App:**
```bash
python run_main.py
```

**Terminal 2 - Analysis Service:**
```bash
python run_analysis.py
```

Then open your browser to: **http://localhost:5000**

### Option 2: Main App Only (No AI Analysis)

```bash
python run_main.py
```

AI analysis features will be disabled, but file extraction and browsing will work.

## 📖 Usage Guide

### Basic File Extraction

1. **Upload Archive**
   - Drag & drop your archive file onto the upload area
   - Or click "Select File" to browse
   - Supports files up to 2GB

2. **Wait for Extraction**
   - Progress bar shows real-time extraction status
   - Can take several minutes for large archives

3. **Browse Results**
   - Click on summary cards to view files or directories
   - Use search bar to find specific files
   - Toggle between Files, Directories, and Tree View tabs

### AI-Powered Test Analysis

1. **Automatic Discovery**
   - After extraction, RHOSO test folders are automatically detected
   - Look for the "RHOSO Tests" card in the summary

2. **View Test Results**
   - Click "Test Results" tab
   - Select a RHOSO folder from the displayed cards
   - View test summary: Total, Passed, Failed, Skipped, Errors

3. **Analyze Failures**
   - Select your preferred AI backend (Gemini/Claude/MCP)
   - Click "✨ Analyze with AI" to get overall failure analysis
   - Or expand individual failure boxes to see details
   - Click "💬 Ask AI" on any failure to start a chat

4. **Interactive Chat**
   - Ask questions like:
     - "Why did this test fail?"
     - "How can I fix this error?"
     - "Are these failures related?"
   - AI responds with context from test results and must-gather logs
   - Chat history is maintained during the session

## 🔧 Configuration

### Main App Settings (Flask)

Edit `config/settings.py` or use environment variables:

```python
# File upload limits
MAX_UPLOAD_SIZE = 2GB

# Extraction paths
UPLOAD_FOLDER = 'uploads'
EXTRACT_FOLDER = 'extracted'

# Database
DATABASE_URL = 'sqlite:///data/app.db'
```

### Analysis Service Settings

Configured via environment variables in `.env`:

```bash
# AI Backend API Keys
GEMINI_API_KEY=your-key
CLAUDE_API_KEY=your-key
MCP_SERVER_URL=http://localhost:9000

# Service URL for main app to connect
ANALYSIS_SERVICE_URL=http://localhost:8001
```

## 🔒 Security Features

All security measures from the original app are **preserved**:

1. ✅ Path Traversal Prevention - Absolute path validation
2. ✅ Secure Filename Handling - `secure_filename()` on uploads
3. ✅ TAR Symlink Filtering - `filter='data'` for safe extraction
4. ✅ File Type Whitelist - Only allowed archive extensions
5. ✅ Size Limits - 2GB upload, 5MB preview
6. ✅ UUID Job Isolation - Prevents enumeration attacks
7. ✅ Binary File Detection - Prevents serving binary as text
8. ✅ SQL Injection Prevention - SQLAlchemy ORM

**New Security Additions:**
- API rate limiting (configurable)
- Search query sanitization
- CORS configuration
- Secure API key storage (environment variables)

## 📂 Project Structure

```
File-Parser/
├── app/                      # Main Flask application
│   ├── __init__.py          # App factory
│   ├── models/              # Database models
│   ├── blueprints/          # API routes
│   ├── services/            # Business logic
│   └── utils/               # Security & helpers
├── analysis_service/         # FastAPI analysis service
│   ├── server.py            # FastAPI app
│   ├── parsers/             # Tempest & must-gather parsers
│   └── plugins/             # AI backend plugins
├── config/                   # Configuration
├── frontend/                 # HTML/CSS/JS
│   ├── templates/
│   └── static/
├── requirements/             # Dependencies
│   ├── base.txt
│   └── analysis.txt
├── run_main.py              # Main app entry point
├── run_analysis.py          # Analysis service entry point
└── README.md
```

## 🐛 Troubleshooting

### "Backend not initialized" Error

**Problem:** AI analysis fails with "Backend not initialized"

**Solution:**
1. Check that you've added API keys to `.env`
2. Restart the analysis service: `python run_analysis.py`
3. Check terminal output for initialization errors

### "Analysis service not reachable" Error

**Problem:** Main app can't connect to analysis service

**Solution:**
1. Ensure analysis service is running on port 8001
2. Check `ANALYSIS_SERVICE_URL` in `.env`
3. Verify no firewall blocking localhost:8001

### Large File Extraction Slow

**Problem:** 2GB file takes very long to extract

**Optimizations already applied:**
- Removed artificial delays
- Batched progress updates (100x reduction)
- Skipped expensive directory size calculations
- Used bulk `extractall()` for small archives

**Further tips:**
- Extract to SSD instead of HDD
- Close other applications
- Expected time: ~2-5 minutes for 2GB

### "Symlink Error" During Extraction

**Problem:** Error about absolute path symlinks

**Solution:** Already fixed! The app uses `filter='data'` which:
- Strips leading slashes from paths
- Makes symlinks relative and safe
- Skips device files

## 🤝 Contributing

This project uses a plugin architecture for AI backends. To add a new AI backend:

1. Create a new plugin in `analysis_service/plugins/`
2. Inherit from `AIBackendPlugin` base class
3. Implement required methods:
   - `initialize()` - Setup with API keys
   - `analyze_failures()` - Analyze test failures
   - `chat()` - Interactive chat
4. Register in `analysis_service/plugins/registry.py`

## 📜 License

[Your License Here]

## 👥 Authors

[Your Name/Team]

## 🙏 Acknowledgments

- Built with Flask, FastAPI, SQLAlchemy
- AI powered by Google Gemini & Anthropic Claude
- UI styled with modern CSS gradients and animations

---

**Need Help?** Open an issue or contact the development team.

**Love this tool?** Star the repository and share with your team! ⭐

3. **Access the Web Interface**:
Open your browser and navigate to:
```
http://localhost:5000
```

## Usage Guide

### Uploading Files

1. **Drag & Drop**: Drag an archive file onto the upload area
2. **Browse**: Click "Select File" to choose a file from your computer
3. **Upload**: Click "Upload & Extract" to begin processing

### Viewing Progress

The application shows real-time progress updates:
- **0-10%**: Uploading file
- **10-90%**: Extracting files (shows individual file progress)
- **90-95%**: Analyzing extracted files
- **95-100%**: Finalizing and completing

### Browsing Extracted Files

1. **View Summary**: After extraction, see total files, directories, and size
2. **Browse Files**: Click the "Files" card to see all extracted files
3. **Browse Directories**: Click the "Directories" card to see all folders
4. **View File Content**: Click "View" on any text file to preview it
5. **Download Files**: Click "Download" to save individual files

### File Viewer

- Supports text files up to 5MB
- Shows binary file warning for non-text files
- Displays file size information
- Scroll through large files
- Close viewer to return to file list

## Project Structure

```
file-extractor-app/
├── server.py              # Flask backend server
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/
│   └── index.html        # Frontend interface
├── uploads/              # Temporary upload storage (auto-created)
└── extracted/            # Extracted files storage (auto-created)
```

## API Endpoints

### POST /upload
Upload an archive file for extraction
- **Body**: multipart/form-data with 'file' field
- **Response**: `{"success": true, "job_id": "...", "filename": "..."}`

### GET /progress/<job_id>
Get extraction progress for a job
- **Response**: `{"status": "extracting", "progress": 45, "message": "..."}`

### GET /browse/<job_id>
Get list of extracted files and directories
- **Response**: JSON with files, directories, and size information

### GET /read/<job_id>/<file_path>
Read content of an extracted file
- **Response**: `{"success": true, "content": "...", "size": 1234}`

### GET /download/<job_id>/<file_path>
Download an extracted file
- **Response**: File download

## Configuration

You can modify these settings in `server.py`:

```python
UPLOAD_FOLDER = 'uploads'                # Upload directory
EXTRACT_FOLDER = 'extracted'             # Extraction directory
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # Max upload: 2GB
ALLOWED_EXTENSIONS = {...}               # Supported formats
```

## Security Features

- File path validation to prevent directory traversal
- Secure filename handling
- File size limits
- Binary file detection
- CORS protection

## Supported Archive Formats

- ZIP (.zip)
- TAR (.tar)
- GZIP (.gz, .tar.gz, .tgz)
- BZIP2 (.bz2, .tar.bz2)
- XZ (.xz, .tar.xz)

## Browser Compatibility

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Opera (latest)

## Troubleshooting

### Upload Fails
- Check file size (must be under 2GB)
- Verify file format is supported
- Ensure sufficient disk space

### Extraction Error
- Archive file may be corrupted
- Check server logs for details
- Try re-uploading the file

### File Preview Not Working
- File must be text-based
- File must be under 5MB
- Binary files cannot be previewed

## Future Enhancements

- Support for RAR and 7Z archives
- Batch file operations
- Search within extracted files
- Archive creation functionality
- User authentication
- Cloud storage integration

## License

MIT License - feel free to use and modify as needed.

## Author

Created with Flask and vanilla JavaScript for simplicity and performance.
