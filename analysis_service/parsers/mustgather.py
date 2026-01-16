"""
Must-Gather Parser
Parses must-gather logs and correlates with test failures
"""

import os
import re
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class MustGatherParser:
    """Parser for must-gather log directories"""

    def __init__(self):
        self.log_extensions = ['.log', '.txt', '.out', '.err']

    def find_related_logs(self, mustgather_path: str, test_name: str, error_message: str, max_results: int = 5) -> List[str]:
        """
        Find log files related to a test failure

        Args:
            mustgather_path: Path to must-gather directory
            test_name: Name of the failed test
            error_message: Error message from test failure
            max_results: Maximum number of log files to return

        Returns:
            List of relative paths to potentially related log files
        """
        if not os.path.exists(mustgather_path):
            logger.warning(f"Must-gather path does not exist: {mustgather_path}")
            return []

        # Extract keywords from test name and error
        keywords = self._extract_keywords(test_name, error_message)

        if not keywords:
            return []

        logger.info(f"Searching for logs with keywords: {keywords}")

        # Search for relevant log files
        related_logs = []

        for root, dirs, files in os.walk(mustgather_path):
            for file in files:
                if not any(file.endswith(ext) for ext in self.log_extensions):
                    continue

                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, mustgather_path)

                # Check if filename matches keywords
                filename_score = self._calculate_relevance_score(file.lower(), keywords)

                if filename_score > 0:
                    # Quick content check for smaller files
                    content_score = 0
                    try:
                        file_size = os.path.getsize(file_path)
                        if file_size < 10 * 1024 * 1024:  # Only scan files < 10MB
                            content_score = self._scan_log_content(file_path, keywords, max_lines=500)
                    except Exception as e:
                        logger.warning(f"Error scanning {file_path}: {e}")

                    total_score = filename_score + content_score

                    if total_score > 0:
                        related_logs.append({
                            'path': rel_path,
                            'score': total_score,
                            'filename_score': filename_score,
                            'content_score': content_score
                        })

        # Sort by relevance score and return top results
        related_logs.sort(key=lambda x: x['score'], reverse=True)
        return [log['path'] for log in related_logs[:max_results]]

    def _extract_keywords(self, test_name: str, error_message: str) -> List[str]:
        """
        Extract relevant keywords from test name and error message

        Args:
            test_name: Test name
            error_message: Error message

        Returns:
            List of keywords to search for
        """
        keywords = set()

        # Extract from test name
        # Example: test_volume_create_delete -> ['volume', 'create', 'delete']
        test_parts = re.findall(r'[a-z]+', test_name.lower())
        keywords.update([part for part in test_parts if len(part) > 3])

        # Extract from error message
        # Look for common OpenStack service names
        services = ['nova', 'cinder', 'neutron', 'glance', 'keystone', 'heat', 'swift']
        for service in services:
            if service in error_message.lower():
                keywords.add(service)

        # Extract resource types
        resources = ['volume', 'instance', 'network', 'port', 'router', 'image', 'server', 'snapshot']
        for resource in resources:
            if resource in error_message.lower() or resource in test_name.lower():
                keywords.add(resource)

        # Extract error types
        error_types = ['timeout', 'error', 'failure', 'exception', 'denied', 'not found', 'conflict']
        for error_type in error_types:
            if error_type in error_message.lower():
                keywords.add(error_type.replace(' ', '_'))

        # Extract UUIDs and IDs (potential resource identifiers)
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        uuids = re.findall(uuid_pattern, error_message.lower())
        keywords.update(uuids[:3])  # Limit to first 3 UUIDs

        return list(keywords)

    def _calculate_relevance_score(self, filename: str, keywords: List[str]) -> int:
        """
        Calculate relevance score based on keyword matches in filename

        Args:
            filename: Filename to check
            keywords: List of keywords

        Returns:
            Relevance score (higher is more relevant)
        """
        score = 0
        for keyword in keywords:
            if keyword in filename:
                # Higher score for exact matches
                if keyword == filename.split('.')[0]:
                    score += 5
                else:
                    score += 2

        return score

    def _scan_log_content(self, file_path: str, keywords: List[str], max_lines: int = 500) -> int:
        """
        Scan log file content for keyword matches

        Args:
            file_path: Path to log file
            keywords: Keywords to search for
            max_lines: Maximum lines to scan

        Returns:
            Content relevance score
        """
        score = 0

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break

                    line_lower = line.lower()
                    for keyword in keywords:
                        if keyword in line_lower:
                            # Higher score for ERROR/WARN lines
                            if 'error' in line_lower or 'warn' in line_lower or 'fail' in line_lower:
                                score += 3
                            else:
                                score += 1

        except Exception as e:
            logger.debug(f"Error scanning {file_path}: {e}")

        return score

    def extract_log_excerpt(self, log_path: str, keywords: List[str], context_lines: int = 5) -> List[Dict]:
        """
        Extract relevant excerpts from a log file

        Args:
            log_path: Path to log file
            keywords: Keywords to look for
            context_lines: Number of lines before/after match to include

        Returns:
            List of log excerpts with context
        """
        excerpts = []

        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in keywords):
                    # Get context
                    start = max(0, i - context_lines)
                    end = min(len(lines), i + context_lines + 1)

                    excerpts.append({
                        'line_number': i + 1,
                        'matched_line': line.strip(),
                        'context': ''.join(lines[start:end])
                    })

                    # Limit number of excerpts
                    if len(excerpts) >= 10:
                        break

        except Exception as e:
            logger.error(f"Error extracting from {log_path}: {e}")

        return excerpts
