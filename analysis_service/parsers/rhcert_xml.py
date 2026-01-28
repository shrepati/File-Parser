"""
Red Hat Certification XML Parser
Parses rhcert-results-*.xml files to extract test results
"""

import xml.etree.ElementTree as ET
from typing import Dict, List
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class RHCertXMLParser:
    """Parser for Red Hat Certification XML result files"""

    def parse(self, xml_file_path: str) -> Dict:
        """
        Parse rhcert XML results file

        Args:
            xml_file_path: Path to rhcert-results-*.xml

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
                'review': 0,
                'duration': 0.0,
                'failures': [],
                'certification_info': {},
                'product_info': {},
                'test_components': []
            }

            # Extract certification metadata
            cert = root.find('.//certification')
            if cert is not None:
                results['certification_info'] = {
                    'id': cert.get('id', 'Unknown'),
                    'name': cert.get('name', 'Unknown'),
                    'type': cert.get('type', 'Unknown'),
                    'status': cert.get('test-plan-status', 'Unknown'),
                    'created': cert.get('created', 'Unknown'),
                    'updated': cert.get('updated', 'Unknown')
                }

            # Extract product information
            vendor = root.find('.//vendor[@id="569359"]') or root.find('.//vendor')
            if vendor is not None:
                product = vendor.find('product')
                results['product_info'] = {
                    'vendor': vendor.get('name', 'Unknown'),
                    'product': product.get('name', 'Unknown') if product is not None else 'Unknown',
                    'category': product.get('category', 'Unknown') if product is not None else 'Unknown'
                }

            # Get Red Hat platform info
            rh_vendor = root.find('.//vendor[@name="Red Hat, Inc."]')
            if rh_vendor is not None:
                rh_product = rh_vendor.find('.//product')
                version = rh_product.find('version') if rh_product is not None else None
                if rh_product is not None:
                    results['platform_info'] = {
                        'product': rh_product.get('name', 'Unknown'),
                        'version': version.get('version', 'Unknown') if version is not None else 'Unknown',
                        'platform': version.get('platform', 'Unknown') if version is not None else 'Unknown'
                    }

            # Parse all test components
            components = root.findall('.//plan-component')
            for comp in components:
                results['test_components'].append({
                    'id': comp.get('id', ''),
                    'name': comp.get('name', ''),
                    'bits': comp.get('bits', '')
                })

            # Parse all test executions
            tests = root.findall('.//test')
            for test in tests:
                test_name = test.get('name', 'Unknown')
                test_path = test.get('path', '')
                component_id = test.get('component-id', '')

                # Find test run
                runs = test.findall('.//run')
                for run in runs:
                    results['total_tests'] += 1

                    summary = run.find('summary')
                    if summary is not None:
                        result_status = summary.get('data-value', 'UNKNOWN').upper()
                        summary_text = summary.text.strip() if summary.text else ''

                        run_time = run.get('run-time', 'N/A')
                        end_time = run.get('end-time', 'N/A')
                        return_value = run.get('return-value', '')

                        # Categorize result
                        if result_status == 'PASS':
                            results['passed'] += 1
                        elif result_status == 'FAIL':
                            results['failed'] += 1
                            # Extract failure details
                            self._parse_failure(test, test_name, test_path, run, run_time, end_time, results)
                        elif result_status == 'REVIEW':
                            results['review'] += 1
                            # Add to failures for visibility
                            results['failures'].append({
                                'test_name': test_name,
                                'class_name': test_path,
                                'error_message': f'Test requires manual review: {summary_text}',
                                'traceback': '',
                                'failure_type': 'review',
                                'duration': 0.0,
                                'run_time': run_time,
                                'end_time': end_time
                            })
                        elif result_status == 'SKIP':
                            results['skipped'] += 1
                        else:
                            results['errors'] += 1

            logger.info(f"Parsed rhcert XML: total={results['total_tests']}, passed={results['passed']}, "
                       f"failed={results['failed']}, review={results['review']}, skipped={results['skipped']}")

            return results

        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error parsing rhcert XML: {e}")
            raise

    def _parse_failure(self, test: ET.Element, test_name: str, test_path: str,
                      run: ET.Element, run_time: str, end_time: str, results: Dict):
        """Extract detailed failure information"""

        error_message = f"Test '{test_name}' failed"
        traceback_lines = []

        # Get output
        output = run.find('.//output')
        if output is not None and output.text:
            output_text = output.text.strip()
            lines = output_text.split('\n')

            # Look for error lines
            for line in lines:
                if any(word in line.lower() for word in ['error', 'fail', 'exception', 'traceback']):
                    traceback_lines.append(line)

            # If no specific errors, use last few lines
            if not traceback_lines:
                traceback_lines = [l for l in lines[-10:] if l.strip()]

            if traceback_lines:
                error_message = traceback_lines[0][:200]

        # Check for failed commands
        commands = run.findall('.//command')
        failed_commands = [cmd for cmd in commands if cmd.get('return-value') != '0']

        if failed_commands:
            cmd_errors = []
            for cmd in failed_commands[:5]:  # Show first 5 failed commands
                cmd_text = cmd.get('command', 'Unknown command')[:100]
                ret_code = cmd.get('return-value', '?')

                stderr = cmd.find('stderr')
                stderr_text = ''
                if stderr is not None and stderr.text:
                    stderr_text = stderr.text.strip()[:200]

                cmd_errors.append(f"Command failed (RC={ret_code}): {cmd_text}")
                if stderr_text:
                    cmd_errors.append(f"  Error: {stderr_text}")

            traceback_lines.extend(cmd_errors)

        results['failures'].append({
            'test_name': test_name,
            'class_name': test_path,
            'error_message': error_message,
            'traceback': '\n'.join(traceback_lines[:50]),  # Limit to 50 lines
            'failure_type': 'failure',
            'duration': 0.0,
            'run_time': run_time,
            'end_time': end_time,
            'failed_commands_count': len(failed_commands)
        })
