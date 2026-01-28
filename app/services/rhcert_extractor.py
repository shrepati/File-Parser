"""
RHCert XML Attachment Extractor
Extracts embedded files from rhcert XML and recursively extracts archives
"""

import xml.etree.ElementTree as ET
import base64
import os
import tarfile
import gzip
import logging
import sys
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

# Check if Python version supports filter parameter
PYTHON_HAS_FILTER = sys.version_info >= (3, 12)


class RHCertAttachmentExtractor:
    """Extract and process attachments from rhcert XML files"""

    def __init__(self, xml_file_path: str, output_base_dir: str):
        """
        Initialize extractor

        Args:
            xml_file_path: Path to rhcert XML file
            output_base_dir: Base directory for extracted files
        """
        self.xml_file_path = xml_file_path
        self.output_base_dir = output_base_dir
        self.extracted_files = []

    def extract_all_attachments(self) -> Dict:
        """
        Extract all attachments from rhcert XML

        Returns:
            dict: Summary of extraction with file list
        """
        try:
            tree = ET.parse(self.xml_file_path)
            root = tree.getroot()

            # Find all attachment tags
            attachments = root.findall('.//attachment')

            logger.info(f"Found {len(attachments)} attachments in rhcert XML")

            # Create extraction directory
            extract_dir = os.path.join(self.output_base_dir, 'rhcert_attachments')
            os.makedirs(extract_dir, exist_ok=True)

            results = {
                'total_attachments': len(attachments),
                'extracted_files': [],
                'extracted_archives': [],
                'errors': []
            }

            for attachment in attachments:
                try:
                    filename = attachment.get('name', 'unknown')
                    encoding = attachment.get('encoding', '')
                    content = attachment.text or ''

                    logger.info(f"Extracting attachment: {filename}")

                    # Decode base64 content (even if encoding is empty, try base64)
                    try:
                        decoded_content = base64.b64decode(content)
                    except Exception as e:
                        logger.warning(f"Base64 decode failed for {filename}, treating as plain text")
                        decoded_content = content.encode('utf-8')

                    # Save file
                    output_path = os.path.join(extract_dir, filename)
                    with open(output_path, 'wb') as f:
                        f.write(decoded_content)

                    file_info = {
                        'name': filename,
                        'path': output_path,
                        'relative_path': f'rhcert_attachments/{filename}',
                        'size': len(decoded_content),
                        'md5sum': attachment.get('md5sum', ''),
                        'extracted_from_archive': False
                    }

                    results['extracted_files'].append(file_info)

                    # Check if it's an archive and extract it
                    if self._is_archive(filename):
                        logger.info(f"Detected archive: {filename}, extracting...")
                        archive_results = self._extract_archive(output_path, extract_dir, filename)
                        if archive_results:
                            results['extracted_archives'].append({
                                'archive': filename,
                                'extracted_files': archive_results
                            })

                except Exception as e:
                    logger.error(f"Error extracting attachment {filename}: {e}")
                    results['errors'].append({
                        'file': filename,
                        'error': str(e)
                    })

            return results

        except Exception as e:
            logger.error(f"Error parsing rhcert XML: {e}")
            raise

    def _is_archive(self, filename: str) -> bool:
        """Check if file is an archive"""
        lower_name = filename.lower()
        return (lower_name.endswith('.tar.gz') or
                lower_name.endswith('.tgz') or
                lower_name.endswith('.tar.xz') or
                lower_name.endswith('.tar.bz2') or
                lower_name.endswith('.tar') or
                lower_name.endswith('.xz') or
                lower_name.endswith('.gz'))

    def _extract_archive(self, archive_path: str, base_dir: str, archive_name: str) -> List[Dict]:
        """
        Extract archive file recursively

        Args:
            archive_path: Path to archive file
            base_dir: Base extraction directory
            archive_name: Name of archive

        Returns:
            list: Extracted file information
        """
        extracted_files = []

        try:
            # Create subdirectory for archive contents
            archive_subdir = os.path.join(base_dir, f"{archive_name}_extracted")
            os.makedirs(archive_subdir, exist_ok=True)

            if archive_name.endswith('.tar.xz'):
                # Extract tar.xz
                with tarfile.open(archive_path, 'r:xz') as tar:
                    members = tar.getmembers()
                    logger.info(f"Extracting {len(members)} files from {archive_name}")

                    for member in members:
                        try:
                            tar.extract(member, archive_subdir)

                            extracted_path = os.path.join(archive_subdir, member.name)
                            if os.path.isfile(extracted_path):
                                extracted_files.append({
                                    'name': member.name,
                                    'path': extracted_path,
                                    'relative_path': f'rhcert_attachments/{archive_name}_extracted/{member.name}',
                                    'size': member.size,
                                    'extracted_from_archive': True,
                                    'parent_archive': archive_name
                                })
                        except Exception as e:
                            logger.warning(f"Failed to extract {member.name}: {e}")

            elif archive_name.endswith('.tar.bz2'):
                # Extract tar.bz2
                with tarfile.open(archive_path, 'r:bz2') as tar:
                    members = tar.getmembers()
                    logger.info(f"Extracting {len(members)} files from {archive_name}")

                    for member in members:
                        try:
                            tar.extract(member, archive_subdir)

                            extracted_path = os.path.join(archive_subdir, member.name)
                            if os.path.isfile(extracted_path):
                                extracted_files.append({
                                    'name': member.name,
                                    'path': extracted_path,
                                    'relative_path': f'rhcert_attachments/{archive_name}_extracted/{member.name}',
                                    'size': member.size,
                                    'extracted_from_archive': True,
                                    'parent_archive': archive_name
                                })
                        except Exception as e:
                            logger.warning(f"Failed to extract {member.name}: {e}")

            elif archive_name.endswith('.tar.gz') or archive_name.endswith('.tgz'):
                # Extract tar.gz
                with tarfile.open(archive_path, 'r:gz') as tar:
                    members = tar.getmembers()
                    logger.info(f"Extracting {len(members)} files from {archive_name}")

                    for member in members:
                        try:
                            tar.extract(member, archive_subdir)

                            extracted_path = os.path.join(archive_subdir, member.name)
                            if os.path.isfile(extracted_path):
                                extracted_files.append({
                                    'name': member.name,
                                    'path': extracted_path,
                                    'relative_path': f'rhcert_attachments/{archive_name}_extracted/{member.name}',
                                    'size': member.size,
                                    'extracted_from_archive': True,
                                    'parent_archive': archive_name
                                })
                        except Exception as e:
                            logger.warning(f"Failed to extract {member.name}: {e}")

            elif archive_name.endswith('.tar'):
                # Extract tar
                with tarfile.open(archive_path, 'r:') as tar:
                    members = tar.getmembers()
                    logger.info(f"Extracting {len(members)} files from {archive_name}")

                    for member in members:
                        try:
                            tar.extract(member, archive_subdir)

                            extracted_path = os.path.join(archive_subdir, member.name)
                            if os.path.isfile(extracted_path):
                                extracted_files.append({
                                    'name': member.name,
                                    'path': extracted_path,
                                    'relative_path': f'rhcert_attachments/{archive_name}_extracted/{member.name}',
                                    'size': member.size,
                                    'extracted_from_archive': True,
                                    'parent_archive': archive_name
                                })
                        except Exception as e:
                            logger.warning(f"Failed to extract {member.name}: {e}")

            elif archive_name.endswith('.gz') and not archive_name.endswith('.tar.gz'):
                # Extract .gz file
                output_filename = archive_name[:-3]  # Remove .gz extension
                output_path = os.path.join(archive_subdir, output_filename)

                with gzip.open(archive_path, 'rb') as f_in:
                    with open(output_path, 'wb') as f_out:
                        f_out.write(f_in.read())

                extracted_files.append({
                    'name': output_filename,
                    'path': output_path,
                    'relative_path': f'rhcert_attachments/{archive_name}_extracted/{output_filename}',
                    'size': os.path.getsize(output_path),
                    'extracted_from_archive': True,
                    'parent_archive': archive_name
                })

            logger.info(f"Extracted {len(extracted_files)} files from {archive_name}")

        except Exception as e:
            logger.error(f"Error extracting archive {archive_name}: {e}")

        return extracted_files
