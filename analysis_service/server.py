"""
Analysis Service - FastAPI Server
Handles tempest test result parsing and AI-powered failure analysis
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, AsyncIterator
import logging
import os
import json

from analysis_service.parsers.tempest_xml import TempestXMLParser
from analysis_service.parsers.rhcert_xml import RHCertXMLParser
from analysis_service.parsers.rhcert_attachment_parser import RHCertAttachmentParser
from analysis_service.parsers.mustgather import MustGatherParser
from analysis_service.plugins.registry import registry
from analysis_service.plugins.base import AnalysisContext

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="File Extractor Analysis Service",
    description="AI-powered test result analysis and failure correlation",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class DiscoverRequest(BaseModel):
    job_id: str
    extract_path: str

class ParseRequest(BaseModel):
    job_id: str
    test_folder: str
    extract_path: str
    formats: List[str] = ["html", "xml"]

class AnalyzeRequest(BaseModel):
    job_id: str
    test_folder: str
    extract_path: str
    backend: str = "gemini"
    stream: bool = False

class ChatRequest(BaseModel):
    job_id: str
    test_folder: str
    extract_path: str
    message: str
    history: List[dict] = []
    backend: str = "gemini"
    stream: bool = False


# Global storage for parsed test results (in production, use database)
test_results_cache = {}


@app.on_event("startup")
async def startup_event():
    """Initialize AI plugins on startup"""
    logger.info("Initializing AI backend plugins...")

    config = {
        'gemini': {
            'api_key': os.getenv('GEMINI_API_KEY', '')
        },
        'claude': {
            'api_key': os.getenv('CLAUDE_API_KEY', '')
        },
        'mcp': {
            'server_url': os.getenv('MCP_SERVER_URL', 'http://localhost:9000')
        }
    }

    try:
        await registry.initialize_all(config)
        available = registry.get_available_plugins()
        logger.info(f"Initialized plugins: {available}")
    except Exception as e:
        logger.error(f"Error initializing plugins: {e}")


@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "service": "File Extractor Analysis Service",
        "status": "running",
        "version": "1.0.0"
    }


@app.post("/api/analysis/discover")
async def discover_rhoso_folders(request: DiscoverRequest):
    """
    Discover RHOSO test folders in extracted archive

    Args:
        request: DiscoverRequest with job_id and extract_path

    Returns:
        List of discovered RHOSO folders with test file information
    """
    extract_path = request.extract_path

    if not os.path.exists(extract_path):
        raise HTTPException(status_code=404, detail="Extraction path not found")

    rhoso_folders = []

    # Walk through extraction directory
    for root, dirs, files in os.walk(extract_path):
        for dir_name in dirs:
            if dir_name.startswith('rhoso'):
                dir_path = os.path.join(root, dir_name)
                rel_path = os.path.relpath(dir_path, extract_path)

                # Check for tempest XML result file (only XML supported)
                has_xml = os.path.exists(os.path.join(dir_path, 'tempest_results.xml'))

                # Check for must-gather folder
                has_mustgather = os.path.exists(os.path.join(dir_path, 'must-gather'))

                if has_xml:
                    rhoso_folders.append({
                        'name': dir_name,
                        'path': rel_path,
                        'has_xml': has_xml,
                        'has_mustgather': has_mustgather
                    })

    logger.info(f"Discovered {len(rhoso_folders)} RHOSO test folders for job {request.job_id}")

    return {
        'job_id': request.job_id,
        'rhoso_folders': rhoso_folders,
        'total_found': len(rhoso_folders)
    }


@app.post("/api/analysis/discover-rhcert")
async def discover_rhcert_files(request: DiscoverRequest):
    """
    Discover Red Hat Certification XML files in extracted archive

    Args:
        request: DiscoverRequest with job_id and extract_path

    Returns:
        List of discovered rhcert XML files
    """
    extract_path = request.extract_path

    if not os.path.exists(extract_path):
        raise HTTPException(status_code=404, detail="Extraction path not found")

    rhcert_files = []

    # Walk through extraction directory
    for root, dirs, files in os.walk(extract_path):
        for file_name in files:
            if file_name.startswith('rhcert-results-') and file_name.endswith('.xml'):
                file_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(file_path, extract_path)

                # Get file size
                file_size = os.path.getsize(file_path)

                rhcert_files.append({
                    'name': file_name,
                    'path': rel_path,
                    'size': file_size,
                    'size_mb': round(file_size / (1024 * 1024), 2)
                })

    logger.info(f"Discovered {len(rhcert_files)} rhcert XML files for job {request.job_id}")

    return {
        'job_id': request.job_id,
        'rhcert_files': rhcert_files,
        'total_found': len(rhcert_files)
    }


@app.post("/api/analysis/parse")
async def parse_tempest_results(request: ParseRequest):
    """
    Parse tempest test results from XML files only

    Args:
        request: ParseRequest with job details

    Returns:
        Parsed test results with failures, errors, skipped tests and statistics
    """
    test_folder_path = os.path.join(request.extract_path, request.test_folder)

    # Check if test_folder is actually a file (rhcert XML case)
    # If it's a rhcert XML file, we don't need the test_folder_path, we'll use extract_path directly
    is_rhcert_xml_file = request.test_folder.lower().endswith('.xml') and 'rhcert' in request.test_folder.lower()

    if not is_rhcert_xml_file and not os.path.exists(test_folder_path):
        raise HTTPException(status_code=404, detail="Test folder not found")

    results = {
        'job_id': request.job_id,
        'test_folder': request.test_folder,
        'total_tests': 0,
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        'errors': 0,
        'duration': 0.0,
        'failures': [],
        'skipped_tests': [],
        'source': None
    }

    # Check for RHOSO format (tempest_results.xml) - only if not a rhcert XML file
    if not is_rhcert_xml_file:
        xml_path = os.path.join(test_folder_path, 'tempest_results.xml')
    else:
        xml_path = None

    if xml_path and os.path.exists(xml_path):
        # RHOSO format - parse tempest XML
        try:
            xml_parser = TempestXMLParser()
            xml_results = xml_parser.parse(xml_path)
            results.update(xml_results)
            results['source'] = 'xml'

            # Separate skipped tests from failures
            all_items = results.get('failures', [])
            failures = [item for item in all_items if item['failure_type'] != 'skip']
            skipped_tests = [item for item in all_items if item['failure_type'] == 'skip']

            results['failures'] = failures
            results['skipped_tests'] = skipped_tests

            logger.info(f"Parsed RHOSO XML: {results['total_tests']} tests, {results['failed']} failures, {results['skipped']} skipped")
        except Exception as e:
            logger.error(f"Error parsing RHOSO XML: {e}")
            raise HTTPException(status_code=500, detail=f"Error parsing XML: {str(e)}")

    else:
        # Check for RHOSP format (rhcert attachments)
        # Look for rhcert_attachments directory in the job's root directory
        rhcert_attachments_path = os.path.join(request.extract_path, 'rhcert_attachments')

        if os.path.exists(rhcert_attachments_path):
            # RHOSP format - parse rhcert attachments
            try:
                logger.info(f"Parsing RHOSP rhcert attachments from {rhcert_attachments_path}")
                # extract_path already includes job_id (e.g., extracted/job-id/)
                # So we pass extract_path directly, and empty string for job_id since it's already in the path
                parser = RHCertAttachmentParser(request.extract_path, '')
                attachment_results = parser.parse()

                # Convert to format expected by AI analysis
                results['total_tests'] = attachment_results['total_tests']
                results['passed'] = attachment_results['passed']
                results['failed'] = attachment_results['failed']
                results['skipped'] = attachment_results['skipped']
                results['errors'] = attachment_results['errors']
                results['failures'] = attachment_results['failures']
                results['skipped_tests'] = attachment_results['skipped_tests']
                results['source'] = 'rhcert-attachments'

                logger.info(f"Parsed RHOSP attachments: {results['total_tests']} tests, {results['failed']} failures, {results['skipped']} skipped")
            except Exception as e:
                logger.error(f"Error parsing RHOSP attachments: {e}")
                raise HTTPException(status_code=500, detail=f"Error parsing RHOSP attachments: {str(e)}")
        else:
            raise HTTPException(status_code=404, detail="No test results found. Looking for tempest_results.xml (RHOSO) or rhcert_attachments (RHOSP)")

    # Parse must-gather logs if available and failures exist
    if results['failed'] > 0 or results['errors'] > 0:
        mustgather_path = os.path.join(test_folder_path, 'must-gather')
        if os.path.exists(mustgather_path):
            try:
                mg_parser = MustGatherParser()
                # Correlate failures with logs (simplified for now)
                for failure in results['failures']:
                    failure['correlated_logs'] = mg_parser.find_related_logs(
                        mustgather_path,
                        failure.get('test_name', ''),
                        failure.get('error_message', '')
                    )
            except Exception as e:
                logger.error(f"Error parsing must-gather: {e}")

    return results


@app.post("/api/analysis/parse-rhcert")
async def parse_rhcert_results(request: ParseRequest):
    """
    Parse Red Hat Certification test results from XML file

    Args:
        request: ParseRequest with job details (test_folder contains the XML file path)

    Returns:
        Parsed certification test results with failures and statistics
    """
    # test_folder contains the relative path to the XML file
    xml_file_path = os.path.join(request.extract_path, request.test_folder)

    if not os.path.exists(xml_file_path):
        raise HTTPException(status_code=404, detail="rhcert XML file not found")

    try:
        rhcert_parser = RHCertXMLParser()
        rhcert_results = rhcert_parser.parse(xml_file_path)

        results = {
            'job_id': request.job_id,
            'test_folder': request.test_folder,
            'total_tests': rhcert_results['total_tests'],
            'passed': rhcert_results['passed'],
            'failed': rhcert_results['failed'],
            'skipped': rhcert_results['skipped'],
            'errors': rhcert_results['errors'],
            'review': rhcert_results.get('review', 0),
            'duration': rhcert_results.get('duration', 0.0),
            'failures': rhcert_results['failures'],
            'skipped_tests': [],
            'source': 'rhcert-xml',
            'certification_info': rhcert_results.get('certification_info', {}),
            'product_info': rhcert_results.get('product_info', {}),
            'platform_info': rhcert_results.get('platform_info', {}),
            'test_components': rhcert_results.get('test_components', [])
        }

        logger.info(f"Parsed rhcert XML: {results['total_tests']} tests, "
                   f"{results['failed']} failures, {results['review']} review")

        return results

    except Exception as e:
        logger.error(f"Error parsing rhcert XML: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error parsing rhcert XML: {str(e)}")


@app.post("/api/analysis/parse-rhcert-attachments")
async def parse_rhcert_attachments(request: DiscoverRequest):
    """
    Parse test results from rhcert XML attachments (neutron, cinder, manila)

    This endpoint looks for extracted attachments from rhcert XML and parses
    validation_report.json files for neutron/cinder/manila components.

    Args:
        request: DiscoverRequest with job_id and extract_path

    Returns:
        Aggregated test results from all neutron/cinder/manila components
    """
    try:
        parser = RHCertAttachmentParser(request.extract_path, request.job_id)
        attachment_results = parser.parse()

        results = {
            'job_id': request.job_id,
            'type': 'rhcert_attachments',
            'components': attachment_results['components'],
            'components_summary': attachment_results['components_summary'],
            'total_tests': attachment_results['total_tests'],
            'passed': attachment_results['passed'],
            'failed': attachment_results['failed'],
            'skipped': attachment_results['skipped'],
            'errors': attachment_results['errors'],
            'review': 0,
            'duration': 0.0,
            'failures': attachment_results['failures'],
            'skipped_tests': attachment_results['skipped_tests'],
            'source': 'rhcert-attachments'
        }

        logger.info(f"Parsed rhcert attachments: {len(attachment_results['components'])} components, "
                   f"{results['total_tests']} tests, {results['failed']} failures, {results['skipped']} skipped")

        return results

    except Exception as e:
        logger.error(f"Error parsing rhcert attachments: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error parsing rhcert attachments: {str(e)}")


@app.get("/api/analysis/backends")
async def list_ai_backends():
    """
    List available AI backend plugins

    Returns:
        List of available AI backends with their capabilities
    """
    # Import registry
    try:
        from analysis_service.plugins.registry import registry
        available = registry.list_available()
    except Exception as e:
        logger.warning(f"Plugin registry not fully initialized: {e}")
        available = []

    return {
        'available': available,
        'total': len(available)
    }


@app.post("/api/analysis/analyze")
async def analyze_failures(request: AnalyzeRequest):
    """
    Analyze test failures using AI backend

    Args:
        request: AnalyzeRequest with analysis details

    Returns:
        AI-generated analysis of failures (streaming or complete)
    """
    # Get the AI backend plugin
    plugin = registry.get(request.backend)
    if not plugin:
        raise HTTPException(
            status_code=400,
            detail=f"Backend '{request.backend}' not available. Available backends: {registry.get_available_plugins()}"
        )

    if not plugin.initialized:
        raise HTTPException(
            status_code=503,
            detail=f"Backend '{request.backend}' not initialized. Check API key configuration."
        )

    # Get or parse test results
    cache_key = f"{request.job_id}:{request.test_folder}"
    if cache_key not in test_results_cache:
        # Parse test results
        parse_req = ParseRequest(
            job_id=request.job_id,
            test_folder=request.test_folder,
            extract_path=request.extract_path
        )
        parsed_results = await parse_tempest_results(parse_req)
        test_results_cache[cache_key] = parsed_results

    results = test_results_cache[cache_key]

    # Build analysis context
    context = AnalysisContext(
        test_failures=results.get('failures', []),
        test_summary={
            'total_tests': results.get('total_tests', 0),
            'passed': results.get('passed', 0),
            'failed': results.get('failed', 0),
            'skipped': results.get('skipped', 0),
            'errors': results.get('errors', 0),
            'duration': results.get('duration', 0.0)
        },
        log_excerpts=[]  # Will be enhanced with must-gather correlation
    )

    try:
        if request.stream and plugin.supports_streaming:
            # Return SSE stream
            async def event_stream() -> AsyncIterator[str]:
                try:
                    # Get the async generator from the plugin (no await - it's already a generator)
                    generator = plugin.analyze_failures(context, stream=True)
                    async for chunk in generator:
                        # Format as Server-Sent Event
                        yield f"data: {json.dumps({'text': chunk})}\n\n"
                except Exception as e:
                    logger.error(f"Streaming error: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                finally:
                    yield "data: [DONE]\n\n"

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        else:
            # Return complete analysis (await the coroutine)
            analysis_result = await plugin.analyze_failures(context, stream=False)
            return {
                'job_id': request.job_id,
                'test_folder': request.test_folder,
                'backend': request.backend,
                'analysis': analysis_result.to_dict()
            }

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/api/analysis/chat")
async def chat_about_failures(request: ChatRequest):
    """
    Interactive chat about test failures

    Args:
        request: ChatRequest with message and context

    Returns:
        AI response (streaming or complete)
    """
    # Get the AI backend plugin
    plugin = registry.get(request.backend)
    if not plugin:
        raise HTTPException(
            status_code=400,
            detail=f"Backend '{request.backend}' not available"
        )

    if not plugin.initialized:
        raise HTTPException(
            status_code=503,
            detail=f"Backend '{request.backend}' not initialized"
        )

    # Get or parse test results for context
    cache_key = f"{request.job_id}:{request.test_folder}"
    if cache_key not in test_results_cache:
        parse_req = ParseRequest(
            job_id=request.job_id,
            test_folder=request.test_folder,
            extract_path=request.extract_path
        )
        parsed_results = await parse_tempest_results(parse_req)
        test_results_cache[cache_key] = parsed_results

    results = test_results_cache[cache_key]

    # Build analysis context
    context = AnalysisContext(
        test_failures=results.get('failures', []),
        test_summary={
            'total_tests': results.get('total_tests', 0),
            'passed': results.get('passed', 0),
            'failed': results.get('failed', 0),
            'skipped': results.get('skipped', 0),
            'errors': results.get('errors', 0)
        },
        log_excerpts=[]
    )

    try:
        if request.stream and plugin.supports_streaming:
            # Return SSE stream
            async def event_stream() -> AsyncIterator[str]:
                try:
                    # Get async generator directly (no await - it's already a generator)
                    generator = plugin.chat(
                        request.message,
                        request.history,
                        context,
                        stream=True
                    )
                    async for chunk in generator:
                        yield f"data: {json.dumps({'text': chunk})}\n\n"
                except Exception as e:
                    logger.error(f"Chat streaming error: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                finally:
                    yield "data: [DONE]\n\n"

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        else:
            # Return complete response (await the coroutine)
            response_text = await plugin.chat(
                request.message,
                request.history,
                context,
                stream=False
            )

            return {
                'job_id': request.job_id,
                'backend': request.backend,
                'role': 'assistant',
                'content': response_text
            }

    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check for monitoring"""
    return {
        'status': 'healthy',
        'service': 'analysis-service',
        'version': '1.0.0'
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "analysis_service.server:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
