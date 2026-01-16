"""
Tempest XML Parser
Parses tempest_results.xml files to extract test results
"""

import xml.etree.ElementTree as ET
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class TempestXMLParser:
    """Parser for tempest XML result files"""

    def parse(self, xml_file_path: str) -> Dict:
        """
        Parse tempest XML results file

        Args:
            xml_file_path: Path to tempest_results.xml

        Returns:
            dict: Parsed test results with statistics and failures
        """
        try:
            tree = ET.parse(xml_file_path)
            root = tree.getroot()

            results = {
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0,
                'errors': 0,
                'duration': 0.0,
                'failures': []
            }

            # Parse testsuite element (JUnit XML format)
            if root.tag == 'testsuites':
                # Multiple test suites
                for testsuite in root.findall('testsuite'):
                    self._parse_testsuite(testsuite, results)
            elif root.tag == 'testsuite':
                # Single test suite
                self._parse_testsuite(root, results)

            # Calculate passed count (tests that didn't fail, error, or get skipped)
            results['passed'] = results['total_tests'] - results['failed'] - results['skipped'] - results['errors']

            # Ensure passed count is not negative
            if results['passed'] < 0:
                logger.warning(f"Negative passed count detected! total={results['total_tests']}, failed={results['failed']}, skipped={results['skipped']}, errors={results['errors']}")
                results['passed'] = 0

            logger.info(f"Parsed XML: total={results['total_tests']}, passed={results['passed']}, failed={results['failed']}, skipped={results['skipped']}, errors={results['errors']}")

            return results

        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error parsing XML: {e}")
            raise

    def _parse_testsuite(self, testsuite: ET.Element, results: Dict):
        """Parse a single testsuite element"""

        # Get duration from testsuite
        time = float(testsuite.get('time', 0.0))
        results['duration'] += time

        # Count actual test cases (more accurate than testsuite attributes)
        # Parse individual test cases and count them
        for testcase in testsuite.findall('testcase'):
            self._parse_testcase(testcase, results)
            # Total tests is the count of all testcases found
            results['total_tests'] += 1

    def _parse_testcase(self, testcase: ET.Element, results: Dict):
        """Parse a single testcase element"""

        test_name = testcase.get('name', 'Unknown')
        class_name = testcase.get('classname', 'Unknown')
        time = float(testcase.get('time', 0.0))

        # Check for failure
        failure = testcase.find('failure')
        if failure is not None:
            results['failed'] += 1
            error_message = failure.get('message', '')
            traceback = failure.text or ''
            failure_type = failure.get('type', 'failure')

            results['failures'].append({
                'test_name': test_name,
                'class_name': class_name,
                'error_message': error_message,
                'traceback': traceback,
                'failure_type': 'failure',
                'duration': time
            })
            return  # Don't count as passed

        # Check for error
        error = testcase.find('error')
        if error is not None:
            results['errors'] += 1
            error_message = error.get('message', '')
            traceback = error.text or ''
            error_type = error.get('type', 'error')

            results['failures'].append({
                'test_name': test_name,
                'class_name': class_name,
                'error_message': error_message,
                'traceback': traceback,
                'failure_type': 'error',
                'duration': time
            })
            return  # Don't count as passed

        # Check for skip
        skipped = testcase.find('skipped')
        if skipped is not None:
            results['skipped'] += 1
            # Skip reason can be in 'message' attribute OR in the text content
            skip_message = skipped.get('message', '')

            # If no message attribute, get text content between <skipped></skipped> tags
            if not skip_message and skipped.text:
                skip_message = skipped.text.strip()

            # If still no message, provide a default
            if not skip_message:
                skip_message = 'Test skipped (no reason provided)'

            results['failures'].append({
                'test_name': test_name,
                'class_name': class_name,
                'error_message': skip_message,
                'traceback': '',
                'failure_type': 'skip',
                'duration': time
            })
            return  # Don't count as passed

        # If we get here, the test passed (no failure, error, or skip)
