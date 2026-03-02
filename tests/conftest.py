"""Shared test fixtures for docx_builder tests."""
from __future__ import annotations

import pytest

from dev.sample_data import get_sample_data
from engine.schema_loader import Schema, load_schema


@pytest.fixture
def rfq_schema() -> Schema:
    """Load the RFQ electric utility schema."""
    return load_schema("schemas/rfq_electric_utility.yaml")


@pytest.fixture
def sample_data() -> dict:
    """Realistic sample data with all required fields filled."""
    return get_sample_data()
