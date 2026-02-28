"""Shared test fixtures for docx_builder tests."""
from __future__ import annotations

import pytest

from engine.schema_loader import Schema, load_schema


@pytest.fixture
def rfq_schema() -> Schema:
    """Load the RFQ electric utility schema."""
    return load_schema("schemas/rfq_electric_utility.yaml")


@pytest.fixture
def sample_data() -> dict:
    """Realistic sample data with all required fields filled."""
    return {
        # Issuing Organization
        "issuer_name": "Ozark Electric Cooperative",
        "issuer_address": "516 E Hwy 76\nBranson, MO 65616",
        "issuer_contact_name": "John Smith",
        "issuer_contact_title": "Procurement Manager",
        "issuer_contact_email": "jsmith@ozarkelectric.com",
        "issuer_contact_phone": "(417) 555-0100",
        # RFQ Details
        "rfq_number": "RFQ-2026-042",
        "rfq_title": "Distribution Line Reconstruction - Hwy 65 Corridor",
        "rfq_issue_date": "2026-03-01",
        "rfq_due_date": "2026-03-28",
        "rfq_due_time": "2:00 PM CST",
        # Project Information
        "project_description": "Reconstruct 3.2 miles of 12.47kV distribution line.",
        "project_location": "Taney County, MO",
        "work_category": "Distribution Line Construction",
        "estimated_duration": "90 calendar days",
        # Scope of Work
        "scope_summary": "Replace 45 wooden poles with steel, restring conductor.",
        "work_items": [
            {
                "item_number": "1",
                "description": "Set 45' Class 2 steel poles",
                "quantity": 45,
                "unit": "EA",
                "unit_price": 4200,
                "extended_price": 189000,
            },
            {
                "item_number": "2",
                "description": "String 477 ACSR conductor",
                "quantity": 3.2,
                "unit": "MI",
                "unit_price": 28000,
                "extended_price": 89600,
            },
        ],
        "specifications": "All work per NESC and RUS standards.",
        # Submission Requirements
        "submission_method": "Email Only",
        "submission_address": "rfq@ozarkelectric.com",
        "required_documents": [
            {"document_name": "Completed Bid Form", "required": True, "notes": ""},
            {"document_name": "Proof of Insurance", "required": True, "notes": "Min $1M GL"},
        ],
        # Terms & Conditions
        "payment_terms": "Net 30",
        "insurance_requirements": "GL: $1M/$2M, Auto: $1M, WC: Statutory",
        "prevailing_wage": False,
        "bonding_required": True,
        "bonding_amount": "100% of contract value",
        # Optional — Safety Requirements (compound)
        "safety_requirements": {
            "general": "All crew must have OSHA 10-hr Construction.\nDaily toolbox talks required.",
            "hot_work_permits": "Required for all welding and cutting operations.",
            "lockout_tagout": "LOTO per OSHA 1910.147 and utility-specific procedures.",
            "confined_space": "",
            "ppe": "FR clothing, hard hat, safety glasses, rubber gloves for energized work.",
            "training_certifications": "Pole top rescue, First Aid/CPR, CDL Class A.",
            "incident_reporting": "Immediate notification for any recordable incident.",
        },
        # Flexible fields
        "_flexible_fields": [
            {"field_label": "Drug Testing Policy", "field_value": "Random testing required"},
        ],
    }
