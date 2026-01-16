"""
Logging Configuration
"""

import logging
import sys
from pathlib import Path

def setup_logging(app_name='file-parser', level=logging.INFO):
    """Configure logging for the application"""

    # Create logs directory
    log_dir = Path(__file__).resolve().parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)

    # Configure root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / f'{app_name}.log')
        ]
    )

    # Set specific log levels for libraries
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    return logging.getLogger(app_name)
