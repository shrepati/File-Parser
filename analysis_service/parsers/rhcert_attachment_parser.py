"""
RHCert Attachment Parser
Parses test results from extracted rhcert XML attachments
Specifically targets neutron, cinder, manila validation_report.json files
"""

import os
import json
import logging
from typing import Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)


class RHCertAttachmentParser:
    """Parser for test results in rhcert XML attachments"""

    def __init__(self, extraction_dir: str, job_id: str):
        """
        Initialize parser

        Args:
            extraction_dir: Base extraction directory (already includes job_id)
            job_id: Job UUID
        """
        self.extraction_dir = extraction_dir
        self.job_id = job_id
        # extraction_dir already includes job_id, so just append rhcert_attachments
        self.attachments_dir = os.path.join(extraction_dir, 'rhcert_attachments')

    def parse(self) -> Dict:
        """
        Parse all neutron/cinder/manila test result files from attachments

        Returns:
            dict: Aggregated test results from all components
        """
        results = {
            'type': 'rhcert_attachments',
            'components': [],
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': 0,
            'failures': [],
            'skipped_tests': [],
            'components_summary': {}
        }

        try:
            if not os.path.exists(self.attachments_dir):
                logger.warning(f"Attachments directory not found: {self.attachments_dir}")
                return results

            # Find all validation_report.json files for neutron/cinder/manila
            validation_files = self._find_validation_files()

            logger.info(f"Found {len(validation_files)} validation report files")

            for validation_file in validation_files:
                component_name = self._extract_component_name(validation_file)
                logger.info(f"Parsing {component_name} validation report")

                component_results = self._parse_validation_file(validation_file, component_name)

                if component_results:
                    results['components'].append(component_results)

                    # Aggregate totals
                    results['total_tests'] += component_results['total_tests']
                    results['passed'] += component_results['passed']
                    results['failed'] += component_results['failed']
                    results['skipped'] += component_results['skipped']
                    results['errors'] += component_results['errors']
                    results['failures'].extend(component_results['failures'])
                    results['skipped_tests'].extend(component_results['skipped_tests'])

                    # Component summary
                    results['components_summary'][component_name] = {
                        'total': component_results['total_tests'],
                        'passed': component_results['passed'],
                        'failed': component_results['failed'],
                        'skipped': component_results['skipped']
                    }

            logger.info(f"Total parsed: {results['total_tests']} tests, "
                       f"{results['passed']} passed, {results['failed']} failed, "
                       f"{results['skipped']} skipped")

            return results

        except Exception as e:
            logger.error(f"Error parsing rhcert attachments: {e}")
            raise

    def _find_validation_files(self) -> List[str]:
        """
        Find all validation_report.json files for neutron/cinder/manila

        Returns:
            list: Paths to validation report files
        """
        validation_files = []

        # Target components
        target_components = ['neutron', 'cinder', 'manila']

        try:
            # Search for validation_report.json files
            for root, dirs, files in os.walk(self.attachments_dir):
                for file in files:
                    # Check if it's a validation report file
                    if file.endswith('-validation_report.json'):
                        file_lower = file.lower()
                        # Check if it starts with any target component
                        for component in target_components:
                            if file_lower.startswith(component):
                                full_path = os.path.join(root, file)
                                validation_files.append(full_path)
                                logger.info(f"Found validation file: {file}")
                                break

        except Exception as e:
            logger.error(f"Error finding validation files: {e}")

        return validation_files

    def _extract_component_name(self, file_path: str) -> str:
        """
        Extract component name from file path

        Args:
            file_path: Path to validation report file

        Returns:
            str: Component name (e.g., 'neutron_ipv4', 'cinder_volumes')
        """
        filename = os.path.basename(file_path)
        # Remove '-validation_report.json' suffix
        component_name = filename.replace('-validation_report.json', '')
        return component_name

    def _parse_validation_file(self, file_path: str, component_name: str) -> Dict:
        """
        Parse a single validation_report.json file

        Args:
            file_path: Path to validation report JSON
            component_name: Component name

        Returns:
            dict: Parsed test results for this component
        """
        component_results = {
            'component_name': component_name,
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': 0,
            'failures': [],
            'skipped_tests': []
        }

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            # Extract totals
            if 'total' in data:
                totals = data['total']
                component_results['total_tests'] = totals.get('tests', 0)
                component_results['passed'] = totals.get('success', 0)
                component_results['failed'] = totals.get('failures', 0)
                component_results['skipped'] = totals.get('skipped', 0)
                component_results['errors'] = totals.get('errors', 0)

            # Extract individual test cases
            if 'test_cases' in data:
                test_cases = data['test_cases']

                for test_name, test_data in test_cases.items():
                    status = test_data.get('status', 'UNKNOWN')

                    # Extract class name and short name (used for both failures and skipped)
                    class_name = self._extract_class_name(test_name)
                    short_name = self._extract_short_test_name(test_name)

                    # Collect failures with tracebacks
                    if status == 'FAIL' and 'failure' in test_data:
                        failure_info = test_data['failure']

                        component_results['failures'].append({
                            'test_name': short_name,
                            'full_test_name': test_name,
                            'class_name': class_name,
                            'component': component_name,
                            'error_message': failure_info.get('type', 'Test failed'),
                            'traceback': failure_info.get('log', ''),
                            'failure_type': 'failure',
                            'duration': 0.0
                        })

                    # Collect skipped tests
                    elif status == 'SKIP':
                        skip_reason = test_data.get('output', 'Test skipped')

                        component_results['skipped_tests'].append({
                            'test_name': short_name,
                            'full_test_name': test_name,
                            'class_name': class_name,
                            'component': component_name,
                            'skip_reason': skip_reason,
                            'failure_type': 'skipped',
                            'duration': 0.0
                        })

            logger.info(f"Parsed {component_name}: {component_results['total_tests']} tests, "
                       f"{component_results['failed']} failures")

        except Exception as e:
            logger.error(f"Error parsing validation file {file_path}: {e}")

        return component_results

    def _extract_class_name(self, test_name: str) -> str:
        """
        Extract class/module name from full test name

        Args:
            test_name: Full test name (e.g., 'tempest.api.network.admin.test_ports.PortsTestJSON.test_create_port')

        Returns:
            str: Class name (e.g., 'tempest.api.network.admin.test_ports.PortsTestJSON')
        """
        # Remove test ID suffix if present (e.g., [id-xxx-yyy-zzz])
        if '[' in test_name:
            test_name = test_name.split('[')[0]

        # Split by '.' and take all but the last part (which is the test method)
        parts = test_name.split('.')
        if len(parts) > 1:
            return '.'.join(parts[:-1])

        return test_name

    def _extract_short_test_name(self, test_name: str) -> str:
        """
        Extract short test name from full test name

        Args:
            test_name: Full test name

        Returns:
            str: Short test name (last part)
        """
        # Remove test ID suffix if present
        if '[' in test_name:
            base_name = test_name.split('[')[0]
            test_id = test_name.split('[')[1].rstrip(']')
        else:
            base_name = test_name
            test_id = ''

        # Get last part (test method name)
        parts = base_name.split('.')
        short_name = parts[-1] if parts else base_name

        if test_id:
            short_name = f"{short_name} [{test_id}]"

        return short_name
