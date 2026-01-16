"""
Tempest HTML Parser
Parses tempest_results.html files to extract test results
"""

from bs4 import BeautifulSoup
from typing import Dict, List
import re
import logging

logger = logging.getLogger(__name__)


class TempestHTMLParser:
    """Parser for tempest HTML result files"""

    def parse(self, html_file_path: str) -> Dict:
        """
        Parse tempest HTML results file

        Args:
            html_file_path: Path to tempest_results.html

        Returns:
            dict: Parsed test results with statistics and failures
        """
        try:
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, 'lxml')

            results = {
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0,
                'errors': 0,
                'duration': 0.0,
                'failures': []
            }

            # Try to find summary statistics
            self._parse_summary(soup, results)

            # Parse individual test results
            self._parse_test_results(soup, results)

            logger.info(f"Parsed HTML: {results['total_tests']} total, {results['failed']} failed")

            return results

        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            raise

    def _parse_summary(self, soup: BeautifulSoup, results: Dict):
        """Parse summary statistics from HTML"""

        # Look for common patterns in tempest HTML output
        # Pattern 1: Summary table
        summary_table = soup.find('table', class_='summary')
        if summary_table:
            rows = summary_table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value_text = cells[1].get_text(strip=True)
                    value = self._extract_number(value_text)

                    if 'total' in label:
                        results['total_tests'] = value
                    elif 'pass' in label:
                        results['passed'] = value
                    elif 'fail' in label:
                        results['failed'] = value
                    elif 'skip' in label:
                        results['skipped'] = value
                    elif 'error' in label:
                        results['errors'] = value
                    elif 'time' in label or 'duration' in label:
                        results['duration'] = float(value_text.replace('s', '').strip() if 's' in value_text else value)

        # Pattern 2: Metadata/stats divs
        stats_div = soup.find('div', class_='statistics') or soup.find('div', id='stats')
        if stats_div and not summary_table:
            text = stats_div.get_text()
            # Extract numbers from text
            matches = re.findall(r'(\d+)\s*(test|pass|fail|error|skip)', text, re.IGNORECASE)
            for value, label in matches:
                value = int(value)
                label = label.lower()
                if 'test' in label:
                    results['total_tests'] = value
                elif 'pass' in label:
                    results['passed'] = value
                elif 'fail' in label:
                    results['failed'] = value
                elif 'error' in label:
                    results['errors'] = value
                elif 'skip' in label:
                    results['skipped'] = value

    def _parse_test_results(self, soup: BeautifulSoup, results: Dict):
        """Parse individual test case results"""

        # Look for test result tables or divs
        test_rows = []

        # Pattern 1: Table with test results
        results_table = soup.find('table', class_='results') or soup.find('table', id='results-table')
        if results_table:
            test_rows = results_table.find_all('tr', class_=['failed', 'error', 'failure'])

        # Pattern 2: Divs with test results
        if not test_rows:
            test_rows = soup.find_all('div', class_=['test-failure', 'test-error', 'failure'])

        for row in test_rows:
            failure = self._parse_failure_row(row)
            if failure:
                results['failures'].append(failure)

        # If we didn't find failures via tables/divs, try plain text parsing
        if not results['failures'] and (results['failed'] > 0 or results['errors'] > 0):
            self._parse_failures_from_text(soup, results)

    def _parse_failure_row(self, element) -> Dict:
        """Parse a single failure row/div"""

        failure = {
            'test_name': 'Unknown',
            'class_name': 'Unknown',
            'error_message': '',
            'traceback': '',
            'failure_type': 'failure',
            'duration': 0.0
        }

        # Try to extract test name
        name_elem = element.find(class_='test-name') or element.find('td', class_='name')
        if name_elem:
            failure['test_name'] = name_elem.get_text(strip=True)

        # Try to extract class name
        class_elem = element.find(class_='test-class') or element.find('td', class_='class')
        if class_elem:
            failure['class_name'] = class_elem.get_text(strip=True)

        # Try to extract error message
        error_elem = element.find(class_='error-message') or element.find('td', class_='message')
        if error_elem:
            failure['error_message'] = error_elem.get_text(strip=True)

        # Try to extract traceback
        tb_elem = element.find(class_='traceback') or element.find('pre')
        if tb_elem:
            failure['traceback'] = tb_elem.get_text(strip=True)

        # Determine failure type from class
        classes = element.get('class', [])
        if 'error' in classes:
            failure['failure_type'] = 'error'
        elif 'skip' in classes:
            failure['failure_type'] = 'skip'

        return failure if failure['test_name'] != 'Unknown' else None

    def _parse_failures_from_text(self, soup: BeautifulSoup, results: Dict):
        """Fallback: parse failures from plain text content"""

        # Look for sections marked as failures
        text = soup.get_text()
        lines = text.split('\n')

        current_failure = None
        in_traceback = False

        for line in lines:
            line = line.strip()

            # Detect test failure markers
            if 'FAILED' in line or 'ERROR' in line:
                if current_failure:
                    results['failures'].append(current_failure)

                # Extract test name
                match = re.search(r'(test_\w+)', line)
                test_name = match.group(1) if match else 'Unknown'

                current_failure = {
                    'test_name': test_name,
                    'class_name': 'Unknown',
                    'error_message': line,
                    'traceback': '',
                    'failure_type': 'error' if 'ERROR' in line else 'failure',
                    'duration': 0.0
                }
                in_traceback = False

            elif current_failure and ('Traceback' in line or in_traceback):
                in_traceback = True
                current_failure['traceback'] += line + '\n'

        # Add last failure
        if current_failure:
            results['failures'].append(current_failure)

    def _extract_number(self, text: str) -> int:
        """Extract first number from text"""
        match = re.search(r'\d+', text)
        return int(match.group()) if match else 0
