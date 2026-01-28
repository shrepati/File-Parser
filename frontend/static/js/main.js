// Main Application JavaScript

let currentJobId = null;
let currentPage = 1;
let itemsPerPage = 1000;  // Items per page for test results pagination
let allTestItems = [];    // Combined failures and skipped tests

// Configuration loaded from backend
let appConfig = {
    extractFolder: null,
    analysisServiceUrl: 'http://localhost:8001'
};

// Load configuration from backend
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        if (response.ok) {
            appConfig = await response.json();
            console.log('Loaded configuration:', appConfig);
        }
    } catch (error) {
        console.error('Failed to load configuration:', error);
    }
}

// Initialize app - load config first
loadConfig();

// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const selectBtn = document.getElementById('selectBtn');
const selectedFile = document.getElementById('selectedFile');
const fileName = document.getElementById('fileName');
const uploadBtn = document.getElementById('uploadBtn');
const progressSection = document.getElementById('progressSection');
const resultsSection = document.getElementById('resultsSection');

// Upload handlers
selectBtn.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('click', (e) => {
    if (e.target !== selectBtn) fileInput.click();
});

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.style.background = '#e8eaff';
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.style.background = '';
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.style.background = '';
    if (e.dataTransfer.files.length > 0) {
        fileInput.files = e.dataTransfer.files;
        handleFileSelect();
    }
});

fileInput.addEventListener('change', handleFileSelect);
uploadBtn.addEventListener('click', uploadFile);

function handleFileSelect() {
    if (fileInput.files.length > 0) {
        fileName.textContent = fileInput.files[0].name;
        selectedFile.style.display = 'block';
    }
}

async function uploadFile() {
    if (fileInput.files.length === 0) return;

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    uploadBtn.disabled = true;
    progressSection.classList.add('active');
    document.getElementById('uploadSection').style.display = 'none';
    resultsSection.classList.remove('active');

    updateProgress(5, 'Uploading file...');

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok && data.success) {
            currentJobId = data.job_id;
            updateProgress(10, 'File uploaded, starting extraction...');
            pollProgress();
        } else {
            showError(data.message || data.error || 'Upload failed');
            uploadBtn.disabled = false;
        }
    } catch (error) {
        showError('Upload error: ' + error.message);
        uploadBtn.disabled = false;
    }
}

async function pollProgress() {
    try {
        const response = await fetch(`/api/progress/${currentJobId}`);
        const data = await response.json();

        updateProgress(data.progress, data.message);

        if (data.status === 'completed') {
            setTimeout(() => loadResults(), 500);
        } else if (data.status === 'error') {
            showError(data.message);
            uploadBtn.disabled = false;
        } else {
            setTimeout(pollProgress, 300);
        }
    } catch (error) {
        showError('Progress check error: ' + error.message);
        uploadBtn.disabled = false;
    }
}

function updateProgress(percent, message) {
    const progressBar = document.getElementById('progressBar');
    const statusMessage = document.getElementById('statusMessage');
    progressBar.style.width = percent + '%';
    progressBar.textContent = percent + '%';
    statusMessage.textContent = message;
}

async function loadResults() {
    try {
        const response = await fetch(`/api/summary/${currentJobId}`);
        const data = await response.json();

        // Update total size
        document.getElementById('totalSize').textContent = data.total_size_human;

        // Show RHOSO card if test results found
        if (data.has_rhoso_tests) {
            document.getElementById('rhosoCard').style.display = 'block';
            document.getElementById('rhosoCount').textContent = data.rhoso_folders.length;
            document.getElementById('resultsTabBtn').style.display = 'block';
        }

        progressSection.classList.remove('active');
        resultsSection.classList.add('active');
        uploadBtn.disabled = false;

        // Load tree view by default
        loadTree();

        // Discover RHOSO test folders
        discoverRHOSOFolders();

    } catch (error) {
        showError('Failed to load results: ' + error.message);
        uploadBtn.disabled = false;
    }
}

async function loadFiles(page = 1) {
    try {
        const response = await fetch(`/api/browse/${currentJobId}?page=${page}&per_page=${itemsPerPage}&sort=name&dir=asc`);
        const data = await response.json();

        displayItems(data.items, 'filesList');
        displayPagination(data.pagination, 'filesPagination', loadFiles);

    } catch (error) {
        console.error('Error loading files:', error);
    }
}

async function loadDirectories(page = 1) {
    try {
        const response = await fetch(`/api/browse/${currentJobId}?page=${page}&per_page=${itemsPerPage}&sort=name&dir=asc`);
        const data = await response.json();

        // Filter only directories
        const dirs = data.items.filter(item => !item.size);
        displayItems(dirs, 'dirsList');

    } catch (error) {
        console.error('Error loading directories:', error);
    }
}

function displayItems(items, containerId) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';

    if (items.length === 0) {
        container.innerHTML = '<p style="text-align:center;padding:40px;color:#999;">No items found</p>';
        return;
    }

    items.forEach(item => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'item';

        const isDir = !item.size;
        const icon = isDir ? '📁' : '📄';

        itemDiv.innerHTML = `
            <div class="item-info">
                <div>${icon} <strong>${item.name}</strong></div>
                <div style="font-size:0.9em;color:#666;">${item.path} • ${item.size_human || 'Directory'}</div>
            </div>
            ${!isDir ? `
            <div class="item-actions">
                <button class="item-btn" onclick="viewFile('${item.path}')">View</button>
                <button class="item-btn" onclick="downloadFile('${item.path}')">Download</button>
            </div>
            ` : ''}
        `;

        container.appendChild(itemDiv);
    });
}

function displayPagination(pagination, containerId, loadFunction) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';

    if (pagination.total_pages <= 1) return;

    for (let i = 1; i <= pagination.total_pages; i++) {
        const btn = document.createElement('button');
        btn.className = 'page-btn' + (i === pagination.page ? ' active' : '');
        btn.textContent = i;
        btn.onclick = () => loadFunction(i);
        container.appendChild(btn);
    }
}

let currentViewedFile = null;

async function viewFile(filePath) {
    // Store current file for download
    currentViewedFile = filePath;

    // Update UI
    const fileName = filePath.split('/').pop();
    document.getElementById('viewerFileName').textContent = fileName;
    document.getElementById('downloadFileBtn').style.display = 'inline-block';
    document.getElementById('fileViewerTabBtn').style.display = 'block';

    // Show file viewer tab
    showTab('viewer');

    const content = document.getElementById('fileViewerContent');

    // Check if it's a rhcert XML file (before trying to read)
    const ext = fileName.split('.').pop().toLowerCase();
    const isRhcertXML = ext === 'xml' && fileName.includes('rhcert-results');

    // For rhcert XML, show extract interface immediately (don't try to load content)
    if (isRhcertXML) {
        document.getElementById('viewerFileSize').textContent = 'Large XML file';
        renderRHCertXMLInterface(filePath, content);
        return;
    }

    // For other files, try to load content
    content.innerHTML = '<div style="text-align: center; padding: 40px; color: #999;">Loading...</div>';

    try {
        const response = await fetch(`/api/read/${currentJobId}/${filePath}`);
        const data = await response.json();

        if (data.success) {
            // Update file size
            document.getElementById('viewerFileSize').textContent = data.size_human || '';

            // Render based on file type
            renderFileContent(data.content, ext, content);
        } else {
            content.innerHTML = `<div class="error-message">Error: ${data.error}<br>${data.message || ''}</div>`;
        }
    } catch (error) {
        content.innerHTML = `<div class="error-message">Failed to load file: ${error.message}</div>`;
    }
}

// Render rhcert XML interface (without loading full content due to size)
function renderRHCertXMLInterface(filePath, container) {
    container.className = 'file-viewer-content';

    // Create extract button and info area (no file content preview)
    const html = `
        <div style="background: #fff3cd; padding: 20px; border-radius: 8px; border-left: 4px solid #ff9800;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <div>
                    <h3 style="margin: 0 0 8px 0; color: #e65100;">🎓 Red Hat Certification Test Results</h3>
                    <p style="margin: 0; font-size: 0.95em; color: #666; line-height: 1.5;">
                        This XML file contains embedded attachments including:<br>
                        • Test logs (tempest.log, neutron logs, etc.)<br>
                        • Configuration files (tempest.conf)<br>
                        • Validation reports (JSON)<br>
                        • <strong>sosreport archive</strong> (~109 MB with 23,000+ system files)
                    </p>
                </div>
            </div>
            <div style="text-align: center; padding: 20px; background: white; border-radius: 4px;">
                <button class="btn btn-primary" onclick="extractRHCertAttachments('${escapeHtml(filePath)}')"
                        id="extractRhcertBtn" style="padding: 12px 24px; font-size: 1.1em;">
                    📦 Extract All Embedded Files
                </button>
                <div id="extractionStatus" style="margin-top: 15px; display: none;"></div>
            </div>
            <div style="margin-top: 15px; padding: 12px; background: #e3f2fd; border-radius: 4px; font-size: 0.9em; color: #1976d2;">
                <strong>ℹ️ Note:</strong> File is too large (186 MB) to preview. Click the button above to extract embedded files,
                then browse them in the File Browser tree structure.
            </div>
        </div>
    `;

    container.innerHTML = html;
}

// Legacy function kept for compatibility
function renderRHCertXML(fileContent, filePath, container) {
    renderRHCertXMLInterface(filePath, container);
}

// Extract rhcert attachments
async function extractRHCertAttachments(filePath) {
    const btn = document.getElementById('extractRhcertBtn');
    const status = document.getElementById('extractionStatus');

    btn.disabled = true;
    btn.textContent = '⏳ Extracting...';
    status.style.display = 'block';
    status.innerHTML = '<div style="color: #0066cc;">Extracting embedded files from XML...</div>';

    try {
        const response = await fetch(`/api/extract-rhcert/${currentJobId}/${filePath}`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            status.innerHTML = `
                <div style="color: #4caf50;">
                    ✅ <strong>Extraction Complete!</strong><br>
                    • Total Attachments: ${data.total_attachments}<br>
                    • Extracted Files: ${data.extracted_files}<br>
                    • Extracted Archives: ${data.extracted_archives}<br>
                    • Indexed Files: ${data.indexed_files}<br>
                    <br>
                    <strong>Files are now visible in the File Browser tree!</strong>
                    Look for "rhcert_attachments" folder.
                </div>
            `;
            btn.textContent = '✅ Extracted';

            // Reload tree to show new files
            if (typeof loadTree === 'function') {
                setTimeout(() => {
                    loadTree();
                }, 1000);
            }
        } else {
            status.innerHTML = `<div style="color: #f44336;">❌ Extraction failed: ${data.message || data.error}</div>`;
            btn.disabled = false;
            btn.textContent = '📦 Extract Embedded Files';
        }
    } catch (error) {
        status.innerHTML = `<div style="color: #f44336;">❌ Error: ${error.message}</div>`;
        btn.disabled = false;
        btn.textContent = '📦 Extract Embedded Files';
    }
}

function renderFileContent(fileContent, extension, container) {
    // Clear previous classes
    container.className = 'file-viewer-content';

    // HTML files - render as actual HTML
    if (extension === 'html' || extension === 'htm') {
        container.classList.add('html-file');
        // Create iframe to safely render HTML
        const iframe = document.createElement('iframe');
        iframe.style.width = '100%';
        iframe.style.height = '700px';
        iframe.style.border = 'none';
        iframe.style.background = 'white';
        container.innerHTML = '';
        container.appendChild(iframe);

        // Write HTML content to iframe
        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        iframeDoc.open();
        iframeDoc.write(fileContent);
        iframeDoc.close();
        return;
    }

    // Image files
    if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp'].includes(extension)) {
        container.classList.add('image-file');
        container.innerHTML = `<img src="data:image/${extension};base64,${fileContent}" alt="Image preview">`;
        return;
    }

    // Log files - highlight errors, warnings
    if (['log', 'txt'].includes(extension)) {
        container.classList.add('log-file');
        const highlighted = highlightLogFile(fileContent);
        container.innerHTML = `<pre>${highlighted}</pre>`;
        return;
    }

    // XML files - code styling but not HTML rendering
    if (extension === 'xml') {
        container.classList.add('code-file');
        container.innerHTML = `<pre>${escapeHtml(fileContent)}</pre>`;
        return;
    }

    // Code files - different styling
    if (['py', 'js', 'java', 'c', 'cpp', 'h', 'sh', 'bash', 'yaml', 'yml', 'json', 'css', 'sql'].includes(extension)) {
        container.classList.add('code-file');
        container.innerHTML = `<pre>${escapeHtml(fileContent)}</pre>`;
        return;
    }

    // Default: plain text
    container.classList.add('text-file');
    container.innerHTML = `<pre>${escapeHtml(fileContent)}</pre>`;
}

function highlightLogFile(content) {
    const lines = content.split('\n');
    return lines.map(line => {
        const lowerLine = line.toLowerCase();
        if (lowerLine.includes('error') || lowerLine.includes('fail') || lowerLine.includes('exception')) {
            return `<span class="log-error">${escapeHtml(line)}</span>`;
        } else if (lowerLine.includes('warn')) {
            return `<span class="log-warning">${escapeHtml(line)}</span>`;
        } else if (lowerLine.includes('info')) {
            return `<span class="log-info">${escapeHtml(line)}</span>`;
        } else if (lowerLine.includes('debug')) {
            return `<span class="log-debug">${escapeHtml(line)}</span>`;
        }
        return escapeHtml(line);
    }).join('\n');
}

function downloadFile(filePath) {
    window.open(`/api/download/${currentJobId}/${filePath}`, '_blank');
}

function downloadCurrentFile() {
    if (currentViewedFile) {
        downloadFile(currentViewedFile);
    }
}

function closeViewer() {
    // Legacy modal closer - no longer used
    document.getElementById('fileViewer').classList.remove('active');
}

function closeFileViewer() {
    // Hide the file viewer tab and go back to tree view
    showTab('tree');
    document.getElementById('fileViewerTabBtn').style.display = 'none';
    currentViewedFile = null;
}

async function performSearch() {
    const query = document.getElementById('searchInput').value.trim();
    if (!query) return;

    try {
        const response = await fetch(`/api/search/${currentJobId}?q=${encodeURIComponent(query)}&page=1&per_page=${itemsPerPage}`);
        const data = await response.json();

        displayItems(data.items, 'filesList');
        displayPagination(data.pagination, 'filesPagination', (page) => searchPage(query, page));

    } catch (error) {
        console.error('Search error:', error);
    }
}

async function searchPage(query, page) {
    try {
        const response = await fetch(`/api/search/${currentJobId}?q=${encodeURIComponent(query)}&page=${page}&per_page=${itemsPerPage}`);
        const data = await response.json();

        displayItems(data.items, 'filesList');
        displayPagination(data.pagination, 'filesPagination', (p) => searchPage(query, p));

    } catch (error) {
        console.error('Search error:', error);
    }
}

async function loadTree() {
    try {
        const treeView = document.getElementById('treeView');
        treeView.innerHTML = '<div class="loading">Loading file structure...</div>';

        // Fetch ALL files and directories
        const response = await fetch(`/api/all-files/${currentJobId}`);
        const data = await response.json();

        console.log(`Loading tree with ${data.total} items`);

        // Build tree structure from flat list
        const tree = buildTreeStructure(data.items);

        // Render the tree
        treeView.innerHTML = '<div class="tree-container">' + renderTree(tree, 0) + '</div>';

    } catch (error) {
        console.error('Tree loading error:', error);
        document.getElementById('treeView').innerHTML = '<div class="error-message">Failed to load file structure</div>';
    }
}

function buildTreeStructure(items) {
    const root = { name: 'root', type: 'directory', path: '', children: {} };

    items.forEach(item => {
        const parts = item.relative_path.split('/').filter(p => p);
        let current = root;

        parts.forEach((part, index) => {
            if (!current.children[part]) {
                current.children[part] = {
                    name: part,
                    type: index === parts.length - 1 ? item.type : 'directory',
                    path: parts.slice(0, index + 1).join('/'),
                    size: item.size,
                    children: {}
                };
            }
            current = current.children[part];
        });
    });

    return root;
}

function renderTree(node, level = 0) {
    if (level === 0 && node.name === 'root') {
        // Render root's children
        let html = '';
        Object.values(node.children).forEach(child => {
            html += renderTree(child, 0);
        });
        return html;
    }

    const indent = level * 20; // Use pixels for better control
    let html = '';

    if (node.type === 'directory') {
        const childrenHtml = Object.values(node.children).map(child => renderTree(child, level + 1)).join('');
        const hasChildren = Object.keys(node.children).length > 0;

        html += `
            <div class="tree-item tree-directory" style="padding-left: ${indent}px;">
                <span class="tree-toggle" onclick="toggleDirectory(this)" style="cursor: pointer;">
                    ${hasChildren ? '▶' : ''}
                </span>
                <span class="tree-icon">📁</span>
                <span class="tree-name">${escapeHtml(node.name)}</span>
            </div>
            ${hasChildren ? `<div class="tree-children" style="display: none;">${childrenHtml}</div>` : ''}
        `;
    } else {
        const sizeStr = formatFileSize(node.size || 0);
        html += `
            <div class="tree-item tree-file" style="padding-left: ${indent}px;" onclick="viewFile('${escapeHtml(node.path)}')">
                <span class="tree-toggle"></span>
                <span class="tree-icon">📄</span>
                <span class="tree-name">${escapeHtml(node.name)}</span>
                <span class="tree-size">${sizeStr}</span>
            </div>
        `;
    }

    return html;
}

function toggleDirectory(element) {
    const item = element.parentElement;
    const children = item.nextElementSibling;

    if (children && children.classList.contains('tree-children')) {
        if (children.style.display === 'none') {
            children.style.display = 'block';
            element.textContent = '▼';
        } else {
            children.style.display = 'none';
            element.textContent = '▶';
        }
    }
}

function showTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Deactivate all tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    const tabMap = {
        'tree': 'treeTab',
        'viewer': 'viewerTab',
        'results': 'resultsTab',
        'tableview': 'tableViewTab'
    };

    document.getElementById(tabMap[tabName]).classList.add('active');

    // Activate corresponding button
    const buttonMap = {
        'tree': document.querySelector('.tab-btn'),
        'viewer': document.getElementById('fileViewerTabBtn'),
        'results': document.getElementById('resultsTabBtn'),
        'tableview': document.getElementById('tableViewTabBtn')
    };

    if (buttonMap[tabName]) {
        buttonMap[tabName].classList.add('active');
    }

    // Load content
    if (tabName === 'tree') {
        loadTree();
    } else if (tabName === 'results') {
        loadAvailableBackends();
    }
}

function showError(message) {
    const statusMessage = document.getElementById('statusMessage');
    statusMessage.innerHTML = `<div style="background:#ff4757;color:white;padding:15px;border-radius:8px;">${message}</div>`;
}

function resetApp() {
    currentJobId = null;
    currentPage = 1;

    progressSection.classList.remove('active');
    resultsSection.classList.remove('active');
    document.getElementById('uploadSection').style.display = 'block';
    document.getElementById('fileViewer').classList.remove('active');

    fileInput.value = '';
    selectedFile.style.display = 'none';
    document.getElementById('rhosoCard').style.display = 'none';
    document.getElementById('resultsTabBtn').style.display = 'none';

    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Search on Enter key
document.getElementById('searchInput')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') performSearch();
});

// ============================================
// RHOSO Test Results Tab Functionality
// ============================================

let rhosoFolders = [];
let rhcertFiles = [];
let currentTestFolder = null;
let currentTestResults = null;
let chatHistory = [];

// Discover RHOSO test folders
async function discoverRHOSOFolders() {
    if (!currentJobId) return;

    const extractPath = `${appConfig.extractFolder}/${currentJobId}`;

    try {
        const response = await fetch(`${appConfig.analysisServiceUrl}/api/analysis/discover`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                job_id: currentJobId,
                extract_path: extractPath
            })
        });

        if (!response.ok) throw new Error('Failed to discover RHOSO folders');

        const data = await response.json();
        rhosoFolders = data.rhoso_folders || [];

        // Also discover rhcert files
        await discoverRHCertFiles();

        displayRHOSOFolders();

        // Show RHOSO card if folders or rhcert files found
        const totalTests = rhosoFolders.length + rhcertFiles.length;
        if (totalTests > 0) {
            document.getElementById('rhosoCard').style.display = 'block';
            document.getElementById('rhosoCount').textContent = totalTests;
            document.getElementById('resultsTabBtn').style.display = 'block';
        }

    } catch (error) {
        console.error('Error discovering RHOSO folders:', error);
        document.getElementById('rhosoFoldersList').innerHTML =
            `<div class="error-message">Error discovering RHOSO test folders: ${error.message}</div>`;
    }
}

// Discover Red Hat Certification XML files
async function discoverRHCertFiles() {
    if (!currentJobId) return;

    const extractPath = `${appConfig.extractFolder}/${currentJobId}`;

    try {
        const response = await fetch(`${appConfig.analysisServiceUrl}/api/analysis/discover-rhcert`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                job_id: currentJobId,
                extract_path: extractPath
            })
        });

        if (!response.ok) throw new Error('Failed to discover rhcert files');

        const data = await response.json();
        rhcertFiles = data.rhcert_files || [];

        console.log(`Discovered ${rhcertFiles.length} rhcert files`);

    } catch (error) {
        console.error('Error discovering rhcert files:', error);
        rhcertFiles = [];
    }
}

// Display RHOSO folder cards and rhcert files
function displayRHOSOFolders() {
    const container = document.getElementById('rhosoFoldersList');

    if (rhosoFolders.length === 0 && rhcertFiles.length === 0) {
        container.innerHTML = '<div class="loading">No RHOSO test folders or rhcert files found in this archive.</div>';
        return;
    }

    let html = '';

    // Display RHOSO folders
    if (rhosoFolders.length > 0) {
        html += '<h4 style="margin: 20px 0 10px 0;">RHOSO Tempest Test Results</h4>';
        rhosoFolders.forEach(folder => {
            const icon = folder.has_xml ? '📊' : '📁';
            const formatInfo = [];
            if (folder.has_xml) formatInfo.push('XML Results');
            if (folder.has_mustgather) formatInfo.push('Must-Gather');

            html += `
                <div class="rhoso-folder-card" onclick="loadTestResults('${folder.path}', '${folder.name}', 'tempest')">
                    <div class="rhoso-folder-icon">${icon}</div>
                    <div class="rhoso-folder-name">${folder.name}</div>
                    <div class="rhoso-folder-info">${formatInfo.join(' • ')}</div>
                </div>
            `;
        });
    }

    // Display rhcert files
    if (rhcertFiles.length > 0) {
        html += '<h4 style="margin: 20px 0 10px 0;">Red Hat Certification Test Results</h4>';
        rhcertFiles.forEach(file => {
            html += `
                <div class="rhoso-folder-card" onclick="loadRHCertResults('${file.path}', '${file.name}')">
                    <div class="rhoso-folder-icon">🎓</div>
                    <div class="rhoso-folder-name">${file.name}</div>
                    <div class="rhoso-folder-info">${file.size_mb} MB • Certification XML</div>
                </div>
            `;
        });
    }

    container.innerHTML = html;
}

// Load and parse test results for a folder
async function loadTestResults(folderPath, folderName) {
    currentTestFolder = folderPath;

    // Hide folders list, show results container
    document.getElementById('rhosoFoldersList').style.display = 'none';
    document.getElementById('testResultsContainer').style.display = 'block';
    document.getElementById('currentTestFolder').textContent = folderName;

    // Reset state
    document.getElementById('aiAnalysisResult').style.display = 'none';
    document.getElementById('aiChatSection').style.display = 'none';
    chatHistory = [];

    const extractPath = `${appConfig.extractFolder}/${currentJobId}`;

    try {
        const response = await fetch(`${appConfig.analysisServiceUrl}/api/analysis/parse`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                job_id: currentJobId,
                test_folder: folderPath,
                extract_path: extractPath,
                formats: ['xml']  // Only XML format supported
            })
        });

        if (!response.ok) throw new Error('Failed to parse test results');

        currentTestResults = await response.json();
        displayTestResults(currentTestResults);

    } catch (error) {
        console.error('Error loading test results:', error);
        document.getElementById('testSummaryCards').innerHTML =
            `<div class="error-message">Error loading test results: ${error.message}</div>`;
    }
}

// Load and parse Red Hat Certification test results
async function loadRHCertResults(filePath, fileName) {
    currentTestFolder = filePath;

    // Hide folders list, show results container
    document.getElementById('rhosoFoldersList').style.display = 'none';
    document.getElementById('testResultsContainer').style.display = 'block';
    document.getElementById('currentTestFolder').textContent = fileName;

    // Reset state
    document.getElementById('aiAnalysisResult').style.display = 'none';
    document.getElementById('aiChatSection').style.display = 'none';
    chatHistory = [];

    const extractPath = `${appConfig.extractFolder}/${currentJobId}`;

    try {
        // Parse attachments (neutron, cinder, manila) instead of direct XML parsing
        const response = await fetch(`${appConfig.analysisServiceUrl}/api/analysis/parse-rhcert-attachments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                job_id: currentJobId,
                extract_path: extractPath
            })
        });

        if (!response.ok) throw new Error('Failed to parse rhcert attachment results');

        currentTestResults = await response.json();
        displayRHCertAttachmentResults(currentTestResults);

    } catch (error) {
        console.error('Error loading rhcert results:', error);
        document.getElementById('testSummaryCards').innerHTML =
            `<div class="error-message">Error loading certification results: ${error.message}</div>`;
    }
}

// Display Red Hat Certification test results
function displayRHCertResults(results) {
    // Display summary cards with review count
    const summaryHTML = `
        <div class="test-summary-card">
            <div class="test-card-number">${results.total_tests}</div>
            <div class="test-card-label">Total Tests</div>
        </div>
        <div class="test-summary-card passed">
            <div class="test-card-number">${results.passed}</div>
            <div class="test-card-label">Passed</div>
        </div>
        <div class="test-summary-card failed">
            <div class="test-card-number">${results.failed}</div>
            <div class="test-card-label">Failed</div>
        </div>
        ${results.review > 0 ? `
        <div class="test-summary-card" style="background: #fff3cd;">
            <div class="test-card-number">${results.review}</div>
            <div class="test-card-label">Review</div>
        </div>
        ` : ''}
        <div class="test-summary-card skipped">
            <div class="test-card-number">${results.skipped}</div>
            <div class="test-card-label">Skipped</div>
        </div>
    `;
    document.getElementById('testSummaryCards').innerHTML = summaryHTML;

    // Display certification info if available
    if (results.certification_info && results.product_info) {
        const certInfo = results.certification_info;
        const prodInfo = results.product_info;
        const platInfo = results.platform_info || {};

        const certInfoHTML = `
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <h4 style="margin: 0 0 10px 0;">Certification Details</h4>
                <p style="margin: 5px 0;"><strong>ID:</strong> ${certInfo.id}</p>
                <p style="margin: 5px 0;"><strong>Name:</strong> ${certInfo.name}</p>
                <p style="margin: 5px 0;"><strong>Type:</strong> ${certInfo.type}</p>
                <p style="margin: 5px 0;"><strong>Status:</strong> ${certInfo.status}</p>
                <p style="margin: 5px 0;"><strong>Product:</strong> ${prodInfo.vendor} - ${prodInfo.product}</p>
                ${platInfo.product ? `<p style="margin: 5px 0;"><strong>Platform:</strong> ${platInfo.product} ${platInfo.version}</p>` : ''}
            </div>
        `;
        document.getElementById('testSummaryCards').insertAdjacentHTML('beforebegin', certInfoHTML);
    }

    // Update failures section title
    const failuresSection = document.querySelector('.failures-section h4');
    if (failuresSection) {
        failuresSection.textContent = 'Test Failures';
    }

    // Display failures
    displayFailures(results.failures || []);

    // Populate table view
    populateTestTable(results);
    document.getElementById('tableViewTabBtn').style.display = 'block';
}

// Display Red Hat Certification attachment-based test results (neutron, cinder, manila)
function displayRHCertAttachmentResults(results) {
    // Display summary cards
    const summaryHTML = `
        <div class="test-summary-card">
            <div class="test-card-number">${results.total_tests}</div>
            <div class="test-card-label">Total Tests</div>
        </div>
        <div class="test-summary-card passed">
            <div class="test-card-number">${results.passed}</div>
            <div class="test-card-label">Passed</div>
        </div>
        <div class="test-summary-card failed">
            <div class="test-card-number">${results.failed}</div>
            <div class="test-card-label">Failed</div>
        </div>
        <div class="test-summary-card skipped">
            <div class="test-card-number">${results.skipped}</div>
            <div class="test-card-label">Skipped</div>
        </div>
    `;
    document.getElementById('testSummaryCards').innerHTML = summaryHTML;

    // Display components summary
    if (results.components_summary && Object.keys(results.components_summary).length > 0) {
        let componentsHTML = `
            <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <h4 style="margin: 0 0 10px 0;">📦 Test Components (from Attachments)</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 10px;">
        `;

        for (const [component, stats] of Object.entries(results.components_summary)) {
            const passRate = stats.total > 0 ? Math.round((stats.passed / stats.total) * 100) : 0;
            componentsHTML += `
                <div style="background: white; padding: 10px; border-radius: 5px; border-left: 4px solid ${passRate >= 80 ? '#28a745' : passRate >= 50 ? '#ffc107' : '#dc3545'};">
                    <strong>${component}</strong><br>
                    <small>Total: ${stats.total} | Passed: ${stats.passed} | Failed: ${stats.failed} | Skipped: ${stats.skipped}</small><br>
                    <small>Pass Rate: ${passRate}%</small>
                </div>
            `;
        }

        componentsHTML += `
                </div>
                <p style="margin: 10px 0 0 0; color: #666; font-size: 0.9em;">
                    <em>These results are parsed from neutron/cinder/manila validation_report.json files extracted from rhcert XML attachments.</em>
                </p>
            </div>
        `;

        document.getElementById('testSummaryCards').insertAdjacentHTML('beforebegin', componentsHTML);
    }

    // Update failures section title
    const failuresSection = document.querySelector('.failures-section h4');
    if (failuresSection) {
        failuresSection.textContent = 'Test Failures & Skipped Tests (Neutron, Cinder, Manila)';
    }

    // Display failures and skipped tests with pagination
    displayFailuresAndSkipped(results.failures || [], results.skipped_tests || []);

    // Populate table view
    populateTestTable(results);
    document.getElementById('tableViewTabBtn').style.display = 'block';
}

// Display failures and skipped tests with pagination (1000 items per page)
function displayFailuresAndSkipped(failures, skippedTests) {
    const container = document.getElementById('failuresList');

    // Combine failures and skipped tests
    allTestItems = [
        ...failures.map(f => ({ ...f, itemType: 'failure' })),
        ...skippedTests.map(s => ({ ...s, itemType: 'skipped' }))
    ];

    if (allTestItems.length === 0) {
        container.innerHTML = '<div class="success-message">No test failures or skipped tests! All tests passed. 🎉</div>';
        return;
    }

    // Reset to first page
    currentPage = 1;
    renderTestItemsPage();
}

function renderTestItemsPage() {
    const container = document.getElementById('failuresList');
    const totalPages = Math.ceil(allTestItems.length / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, allTestItems.length);
    const pageItems = allTestItems.slice(startIndex, endIndex);

    let html = `
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong>Total Items: ${allTestItems.length}</strong>
                <span style="margin-left: 20px;">Showing ${startIndex + 1} - ${endIndex} of ${allTestItems.length}</span>
                <span style="margin-left: 20px;">Page ${currentPage} of ${totalPages}</span>
            </div>
            <div>
                <button onclick="changePage(-1)" ${currentPage === 1 ? 'disabled' : ''} style="margin-right: 5px; padding: 5px 15px;">← Previous</button>
                <button onclick="changePage(1)" ${currentPage === totalPages ? 'disabled' : ''} style="padding: 5px 15px;">Next →</button>
            </div>
        </div>
    `;

    pageItems.forEach((item, index) => {
        const globalIndex = startIndex + index;
        const itemId = `test-item-${globalIndex}`;
        const isFailure = item.itemType === 'failure';
        const bgColor = isFailure ? '#fff5f5' : '#fffef0';
        const borderColor = isFailure ? '#dc3545' : '#ffc107';
        const icon = isFailure ? '❌' : '⏭️';

        html += `
            <div class="failure-box" id="${itemId}" style="background: ${bgColor}; border-left: 4px solid ${borderColor};">
                <div class="failure-header" onclick="toggleFailure('${itemId}')">
                    <div class="failure-title">
                        ${icon} <strong>${item.component || 'unknown'}</strong>: ${item.test_name || 'Unknown Test'}
                    </div>
                    <div class="failure-toggle">►</div>
                </div>
                <div class="failure-content">
                    <div class="failure-info">
                        <div class="failure-label">Class:</div>
                        <div>${item.class_name || 'Unknown'}</div>
                    </div>
                    <div class="failure-info">
                        <div class="failure-label">Component:</div>
                        <div>${item.component || 'Unknown'}</div>
                    </div>
                    <div class="failure-info">
                        <div class="failure-label">Type:</div>
                        <div><span style="color: ${isFailure ? '#dc3545' : '#ffc107'}; font-weight: bold;">${isFailure ? 'FAILED' : 'SKIPPED'}</span></div>
                    </div>
                    ${isFailure && item.error_message ? `
                        <div class="failure-error">
                            <div class="failure-label">Error Message:</div>
                            ${escapeHtml(item.error_message)}
                        </div>
                    ` : ''}
                    ${isFailure && item.traceback ? `
                        <div class="failure-info">
                            <div class="failure-label">Traceback:</div>
                            <div class="failure-traceback">${escapeHtml(item.traceback)}</div>
                        </div>
                    ` : ''}
                    ${!isFailure && item.skip_reason ? `
                        <div class="failure-info">
                            <div class="failure-label">Skip Reason:</div>
                            <div style="color: #666;">${escapeHtml(item.skip_reason)}</div>
                        </div>
                    ` : ''}
                    <div class="failure-actions">
                        <button class="btn btn-sm" onclick="askAIAboutFailure(${globalIndex})">💬 Ask AI</button>
                    </div>
                </div>
            </div>
        `;
    });

    // Add pagination controls at bottom too
    html += `
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 15px; display: flex; justify-content: center; align-items: center;">
            <button onclick="changePage(-1)" ${currentPage === 1 ? 'disabled' : ''} style="margin-right: 10px; padding: 8px 20px;">← Previous</button>
            <span style="margin: 0 15px;"><strong>Page ${currentPage} of ${totalPages}</strong></span>
            <button onclick="changePage(1)" ${currentPage === totalPages ? 'disabled' : ''} style="margin-left: 10px; padding: 8px 20px;">Next →</button>
        </div>
    `;

    container.innerHTML = html;
}

function changePage(direction) {
    const totalPages = Math.ceil(allTestItems.length / itemsPerPage);
    currentPage += direction;

    // Ensure page is within bounds
    if (currentPage < 1) currentPage = 1;
    if (currentPage > totalPages) currentPage = totalPages;

    renderTestItemsPage();

    // Scroll to top of failures section
    document.querySelector('.failures-section').scrollIntoView({ behavior: 'smooth' });
}

// Display test summary and failures
function displayTestResults(results) {
    // Display summary cards
    const summaryHTML = `
        <div class="test-summary-card">
            <div class="test-card-number">${results.total_tests}</div>
            <div class="test-card-label">Total Tests</div>
        </div>
        <div class="test-summary-card passed">
            <div class="test-card-number">${results.passed}</div>
            <div class="test-card-label">Passed</div>
        </div>
        <div class="test-summary-card failed">
            <div class="test-card-number">${results.failed}</div>
            <div class="test-card-label">Failed</div>
        </div>
        <div class="test-summary-card skipped">
            <div class="test-card-number">${results.skipped}</div>
            <div class="test-card-label">Skipped</div>
        </div>
        <div class="test-summary-card failed">
            <div class="test-card-number">${results.errors}</div>
            <div class="test-card-label">Errors</div>
        </div>
    `;
    document.getElementById('testSummaryCards').innerHTML = summaryHTML;

    // Update failures section title
    const failuresSection = document.querySelector('.failures-section h4');
    if (failuresSection) {
        failuresSection.textContent = 'Test Failures';
    }

    // Display failures (only failed and error tests)
    displayFailures(results.failures || []);

    // Display skipped tests separately if they exist
    if (results.skipped_tests && results.skipped_tests.length > 0) {
        displaySkippedTests(results.skipped_tests);
    }

    // Populate table view and show tab
    populateTestTable(results);
    document.getElementById('tableViewTabBtn').style.display = 'block';
}

// Display individual test failures
function displayFailures(failures) {
    const container = document.getElementById('failuresList');

    if (failures.length === 0) {
        container.innerHTML = '<div class="success-message">No test failures! All tests passed. 🎉</div>';
        return;
    }

    let html = '';
    failures.forEach((failure, index) => {
        const failureId = `failure-${index}`;
        html += `
            <div class="failure-box" id="${failureId}">
                <div class="failure-header" onclick="toggleFailure('${failureId}')">
                    <div class="failure-title">
                        ${failure.test_name || 'Unknown Test'}
                    </div>
                    <div class="failure-toggle">►</div>
                </div>
                <div class="failure-content">
                    <div class="failure-info">
                        <div class="failure-label">Class:</div>
                        <div>${failure.class_name || 'Unknown'}</div>
                    </div>
                    <div class="failure-info">
                        <div class="failure-label">Type:</div>
                        <div>${failure.failure_type || 'failure'}</div>
                    </div>
                    ${failure.error_message ? `
                        <div class="failure-error">
                            <div class="failure-label">Error Message:</div>
                            ${escapeHtml(failure.error_message)}
                        </div>
                    ` : ''}
                    ${failure.traceback ? `
                        <div class="failure-info">
                            <div class="failure-label">Traceback:</div>
                            <div class="failure-traceback">${escapeHtml(failure.traceback)}</div>
                        </div>
                    ` : ''}
                    ${failure.correlated_logs && failure.correlated_logs.length > 0 ? `
                        <div class="failure-info">
                            <div class="failure-label">Related Must-Gather Logs:</div>
                            <ul>
                                ${failure.correlated_logs.map(log => `<li>${log}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                    <div class="failure-actions">
                        <button class="btn btn-sm" onclick="askAIAboutFailure(${index})">💬 Ask AI</button>
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// Display skipped tests separately
function displaySkippedTests(skippedTests) {
    const container = document.getElementById('skippedTestsList');
    const section = document.getElementById('skippedSection');

    if (skippedTests.length === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';

    let html = '';
    skippedTests.forEach((test, index) => {
        const skipId = `skip-${index}`;
        html += `
            <div class="failure-box skipped-box" id="${skipId}">
                <div class="failure-header" onclick="toggleFailure('${skipId}')">
                    <div class="failure-title">
                        ⏭️ ${test.test_name || 'Unknown Test'}
                    </div>
                    <div class="failure-toggle">►</div>
                </div>
                <div class="failure-content">
                    <div class="failure-info">
                        <div class="failure-label">Class:</div>
                        <div>${test.class_name || 'Unknown'}</div>
                    </div>
                    <div class="failure-info">
                        <div class="failure-label">Status:</div>
                        <div><span style="color: #f39c12; font-weight: bold;">SKIPPED</span></div>
                    </div>
                    ${test.error_message ? `
                        <div class="failure-info">
                            <div class="failure-label">Skip Reason:</div>
                            <div style="padding: 10px; background: #fef5e7; border-left: 3px solid #f39c12; border-radius: 5px;">
                                ${escapeHtml(test.error_message)}
                            </div>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// Toggle failure box expansion
function toggleFailure(failureId) {
    const box = document.getElementById(failureId);
    box.classList.toggle('expanded');
}

// Populate test results table
function populateTestTable(results) {
    console.log('populateTestTable called with results:', results);
    const tbody = document.getElementById('testResultsTableBody');
    const tableTitle = document.getElementById('tableViewTitle');

    if (!tbody) {
        console.error('testResultsTableBody element not found!');
        return;
    }

    // Update title with folder name
    tableTitle.textContent = `Test Results Table - ${currentTestFolder}`;

    // Combine all test results (failures, errors, and skipped)
    const allTests = [];

    // Add failures and errors
    if (results.failures && results.failures.length > 0) {
        results.failures.forEach(test => {
            allTests.push({
                test_name: test.test_name || 'Unknown',
                class_name: test.class_name || 'Unknown',
                status: test.failure_type === 'error' ? 'error' : 'failed',
                error_message: test.error_message || '',
                duration: test.duration || 0
            });
        });
    }

    // Add skipped tests
    if (results.skipped_tests && results.skipped_tests.length > 0) {
        results.skipped_tests.forEach(test => {
            allTests.push({
                test_name: test.test_name || 'Unknown',
                class_name: test.class_name || 'Unknown',
                status: 'skipped',
                error_message: test.error_message || '',
                duration: test.duration || 0
            });
        });
    }

    console.log('Total tests to display in table:', allTests.length);

    if (allTests.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="loading">No failed or skipped tests found</td></tr>';
        console.log('No tests to display - showing empty message');
        return;
    }

    // Build table rows
    let html = '';
    allTests.forEach((test, index) => {
        const statusClass = test.status === 'failed' ? 'status-failed' :
                           test.status === 'skipped' ? 'status-skipped' : 'status-error';
        const statusText = test.status === 'failed' ? 'Failed' :
                          test.status === 'skipped' ? 'Skipped' : 'Error';

        // Remove square bracket content from test name: test_name[params] -> test_name
        const cleanTestName = test.test_name.replace(/\[.*?\]/g, '');

        // Merge class name and test name: class_name.test_name
        const fullTestPath = `${test.class_name}.${cleanTestName}`;

        html += `
            <tr data-status="${test.status}">
                <td>${escapeHtml(fullTestPath)}</td>
                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                <td>${escapeHtml(test.error_message)}</td>
                <td class="duration-cell">${test.duration.toFixed(2)}s</td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
    console.log('Table populated with', allTests.length, 'rows');
}

// Filter table results based on checkboxes
function filterTableResults() {
    const showFailed = document.getElementById('filterFailed').checked;
    const showSkipped = document.getElementById('filterSkipped').checked;
    const showErrors = document.getElementById('filterErrors').checked;

    const rows = document.querySelectorAll('#testResultsTableBody tr[data-status]');

    rows.forEach(row => {
        const status = row.getAttribute('data-status');
        let shouldShow = false;

        if (status === 'failed' && showFailed) shouldShow = true;
        if (status === 'skipped' && showSkipped) shouldShow = true;
        if (status === 'error' && showErrors) shouldShow = true;

        if (shouldShow) {
            row.classList.remove('hidden');
        } else {
            row.classList.add('hidden');
        }
    });
}

// Start AI analysis of all failures
async function startAIAnalysis() {
    console.log('startAIAnalysis called');
    const backend = document.getElementById('aiBackend').value;
    const analyzeBtn = document.getElementById('analyzeBtn');
    const resultDiv = document.getElementById('aiAnalysisResult');

    console.log('Backend:', backend);
    console.log('Current job ID:', currentJobId);
    console.log('Current test folder:', currentTestFolder);

    analyzeBtn.disabled = true;
    analyzeBtn.textContent = '✨ Analyzing...';
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = '<div class="analysis-streaming">Starting AI analysis...</div>';

    const extractPath = `${appConfig.extractFolder}/${currentJobId}`;

    try {
        console.log('Sending analysis request to:', `${appConfig.analysisServiceUrl}/api/analysis/analyze`);
        const response = await fetch(`${appConfig.analysisServiceUrl}/api/analysis/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                job_id: currentJobId,
                test_folder: currentTestFolder,
                extract_path: extractPath,
                backend: backend,
                stream: true
            })
        });

        console.log('Response status:', response.status);
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Analysis request failed:', errorText);
            throw new Error(`Analysis request failed: ${errorText}`);
        }

        // Handle SSE stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let accumulatedText = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') continue;

                    try {
                        const parsed = JSON.parse(data);
                        if (parsed.text) {
                            accumulatedText += parsed.text;
                            resultDiv.innerHTML = `<div class="analysis-streaming markdown-content">${renderMarkdown(accumulatedText)}</div>`;
                        }
                    } catch (e) {
                        console.error('Parse error:', e);
                    }
                }
            }
        }

        resultDiv.innerHTML = `<div class="markdown-content">${renderMarkdown(accumulatedText)}</div>`;
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = '✨ Analyze with AI';

    } catch (error) {
        console.error('AI analysis error:', error);
        resultDiv.innerHTML = `<div class="error-message">Analysis failed: ${error.message}</div>`;
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = '✨ Analyze with AI';
    }
}

// Load available AI backends
async function loadAvailableBackends() {
    try {
        const response = await fetch(`${appConfig.analysisServiceUrl}/api/analysis/backends`);
        const data = await response.json();

        const select = document.getElementById('aiBackend');
        select.innerHTML = '';

        data.available.forEach(backend => {
            const option = document.createElement('option');
            option.value = backend.name;
            option.textContent = backend.display_name;
            if (!backend.initialized) {
                option.textContent += ' (Not Available)';
                option.disabled = true;
            }
            select.appendChild(option);
        });

    } catch (error) {
        console.error('Error loading backends:', error);
    }
}

// Ask AI about specific failure
function askAIAboutFailure(failureIndex) {
    const failure = currentTestResults.failures[failureIndex];
    const question = `Can you explain this test failure and suggest how to fix it?\n\nTest: ${failure.test_name}\nError: ${failure.error_message}`;

    document.getElementById('aiChatSection').style.display = 'block';
    document.getElementById('chatInput').value = question;

    // Scroll to chat
    document.getElementById('aiChatSection').scrollIntoView({ behavior: 'smooth' });
}

// Toggle chat visibility
function toggleChat() {
    const chatSection = document.getElementById('aiChatSection');
    if (chatSection.style.display === 'none') {
        chatSection.style.display = 'block';
    } else {
        chatSection.style.display = 'none';
    }
}

// Send chat message with streaming
async function sendChatMessage() {
    console.log('sendChatMessage called');
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message) {
        console.log('Empty message, returning');
        return;
    }

    const backend = document.getElementById('aiBackend').value;
    const messagesDiv = document.getElementById('chatMessages');

    console.log('Chat message:', message);
    console.log('Backend:', backend);
    console.log('Job ID:', currentJobId);
    console.log('Test folder:', currentTestFolder);

    // Add user message
    addChatMessage(message, 'user');
    chatHistory.push({ role: 'user', content: message });

    input.value = '';
    input.disabled = true;

    // Add streaming assistant message
    const assistantMsgId = `msg-${Date.now()}`;
    const assistantMsg = document.createElement('div');
    assistantMsg.className = 'chat-message assistant streaming';
    assistantMsg.id = assistantMsgId;
    assistantMsg.textContent = '';
    messagesDiv.appendChild(assistantMsg);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    const extractPath = `${appConfig.extractFolder}/${currentJobId}`;

    try {
        console.log('Sending chat request to:', `${appConfig.analysisServiceUrl}/api/analysis/chat`);
        const response = await fetch(`${appConfig.analysisServiceUrl}/api/analysis/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                job_id: currentJobId,
                test_folder: currentTestFolder,
                extract_path: extractPath,
                message: message,
                history: chatHistory,
                backend: backend,
                stream: true
            })
        });

        console.log('Chat response status:', response.status);
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Chat request failed:', errorText);
            throw new Error(`Chat request failed: ${errorText}`);
        }

        // Handle SSE stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let accumulatedText = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') continue;

                    try {
                        const parsed = JSON.parse(data);
                        if (parsed.text) {
                            accumulatedText += parsed.text;
                            assistantMsg.innerHTML = `<div class="markdown-content">${renderMarkdown(accumulatedText)}</div>`;
                            messagesDiv.scrollTop = messagesDiv.scrollHeight;
                        }
                    } catch (e) {
                        console.error('Parse error:', e);
                    }
                }
            }
        }

        assistantMsg.classList.remove('streaming');
        chatHistory.push({ role: 'assistant', content: accumulatedText });

    } catch (error) {
        console.error('Chat error:', error);
        assistantMsg.textContent = `Error: ${error.message}`;
        assistantMsg.classList.remove('streaming');
    } finally {
        input.disabled = false;
        input.focus();
    }
}

// Add chat message to UI
function addChatMessage(content, role) {
    const messagesDiv = document.getElementById('chatMessages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-message ${role}`;

    if (role === 'assistant') {
        // Render markdown for assistant messages
        msgDiv.innerHTML = `<div class="markdown-content">${renderMarkdown(content)}</div>`;
    } else {
        // Plain text for user messages
        msgDiv.textContent = content;
    }

    messagesDiv.appendChild(msgDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Back to folders list
function backToFoldersList() {
    document.getElementById('rhosoFoldersList').style.display = 'block';
    document.getElementById('testResultsContainer').style.display = 'none';
    currentTestFolder = null;
    currentTestResults = null;
}

// HTML escape utility
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Render markdown to HTML
function renderMarkdown(text) {
    if (typeof marked === 'undefined') {
        // Fallback if marked is not loaded
        return escapeHtml(text).replace(/\n/g, '<br>');
    }

    // Configure marked for safe rendering
    marked.setOptions({
        breaks: true,
        gfm: true,
        headerIds: false,
        mangle: false
    });

    return marked.parse(text);
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Chat input Enter key support
document.getElementById('chatInput')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChatMessage();
    }
});
