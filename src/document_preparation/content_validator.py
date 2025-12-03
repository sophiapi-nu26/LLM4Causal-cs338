#!/usr/bin/env python3
"""
PDF Content Validator
---------------------
Validates parsed PDF content against quality thresholds.

This module provides validation logic to ensure PDFs meet minimum content
requirements before being stored in GCS and processed by downstream systems.
"""

import logging
from typing import Dict, Tuple, Optional


logger = logging.getLogger(__name__)

# Hardcoded validation thresholds
MIN_TEXT_LENGTH = 2000  # ~400 words, more than just abstract
MIN_SECTIONS = 3        # Should have intro, methods, results at minimum


class ContentValidationError(Exception):
    """Raised when PDF content fails validation thresholds."""
    pass


class ContentValidator:
    """Validates parsed PDF content against quality thresholds."""

    def __init__(self):
        """Initialize validator with hardcoded thresholds."""
        pass

    def validate(self, parsed_data: Dict) -> Tuple[bool, Optional[str]]:
        """
        Validate parsed PDF content.

        Checks:
        1. Text length meets minimum character count (2000 chars)
        2. Section count meets minimum requirement (3 sections)

        Args:
            parsed_data: Dictionary with full_text, sections, metadata

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if validation passed, False otherwise
            - error_message: None if valid, error description if invalid
        """
        # Extract data
        full_text = parsed_data.get('full_text', '')
        sections = parsed_data.get('sections', {})

        # Validate text length
        text_length = len(full_text)
        if text_length < MIN_TEXT_LENGTH:
            error = (
                f"Insufficient text content: {text_length} chars "
                f"(minimum {MIN_TEXT_LENGTH}). "
                f"Paper likely contains only abstract or failed to extract fully."
            )
            logger.warning(error)
            return False, error

        # Validate section count
        section_count = len(sections)
        if section_count < MIN_SECTIONS:
            error = (
                f"Insufficient sections: {section_count} sections "
                f"(minimum {MIN_SECTIONS}). "
                f"Paper may only contain abstract and introduction."
            )
            logger.warning(error)
            return False, error

        logger.info(
            f"Content validation passed: {text_length} chars, "
            f"{section_count} sections"
        )
        return True, None

    def validate_or_raise(self, parsed_data: Dict) -> None:
        """
        Validate and raise exception if invalid.

        Convenience method for use in exception-based workflows.

        Args:
            parsed_data: Dictionary with full_text, sections, metadata

        Raises:
            ContentValidationError: If validation fails
        """
        is_valid, error_message = self.validate(parsed_data)
        if not is_valid:
            raise ContentValidationError(error_message)
