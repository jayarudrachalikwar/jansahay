"""Seed development sample government welfare schemes (not official live data)."""

import sys

from app.database.session import SessionLocal
from app.models.scheme import GovernmentScheme
from app.models.scheme_eligibility import SchemeEligibilityCriterion

# Development/sample schemes — clearly not official government integrations.
SAMPLE_SCHEMES = [
    {
        "name": "PM-KISAN Financial Assistance (Sample)",
        "short_description": "Sample income support scheme for small and marginal farmers.",
        "detailed_description": (
            "Development sample of a direct income support scheme for eligible farmers. "
            "This record is for testing Phase 4 eligibility and recommendations only."
        ),
        "department": "Ministry of Agriculture (Sample)",
        "state": "All India",
        "scheme_type": "Financial Assistance",
        "benefits": "Sample benefit: periodic financial support for eligible farmers.",
        "application_process": "Sample process: register through local agriculture office or online portal.",
        "official_website": "https://example.dev/pm-kisan-sample",
        "criteria": [
            {
                "criterion_type": "profile",
                "field_name": "land_holding",
                "operator": "less_than_or_equal",
                "expected_value": "5",
                "description": "Land holding must be within small/marginal farmer limits",
            },
            {
                "criterion_type": "profile",
                "field_name": "state",
                "operator": "in",
                "expected_value": "Telangana,Andhra Pradesh,All India",
                "description": "Scheme available in selected states",
            },
        ],
    },
    {
        "name": "Telangana Crop Insurance Support (Sample)",
        "short_description": "Sample crop insurance support for Telangana farmers.",
        "detailed_description": (
            "Development sample crop insurance scheme covering notified crops. "
            "For Phase 4 testing only — not connected to any official insurer."
        ),
        "department": "Telangana Agriculture Department (Sample)",
        "state": "Telangana",
        "scheme_type": "Crop Insurance",
        "benefits": "Sample benefit: subsidized crop insurance premium and claim support.",
        "application_process": "Sample process: apply through authorized bank or online portal.",
        "official_website": "https://example.dev/tg-crop-insurance-sample",
        "criteria": [
            {
                "criterion_type": "profile",
                "field_name": "state",
                "operator": "equals",
                "expected_value": "Telangana",
                "description": "Farmer must reside in Telangana",
            },
            {
                "criterion_type": "profile",
                "field_name": "crop_type",
                "operator": "in",
                "expected_value": "cotton,paddy,rice,maize",
                "description": "Crop must be among notified crops",
            },
        ],
    },
    {
        "name": "Micro Irrigation Subsidy (Sample)",
        "short_description": "Sample subsidy for drip and sprinkler irrigation systems.",
        "detailed_description": (
            "Development sample irrigation support scheme promoting water-efficient farming. "
            "Not an official government program."
        ),
        "department": "Ministry of Jal Shakti (Sample)",
        "state": "All India",
        "scheme_type": "Irrigation Support",
        "benefits": "Sample benefit: subsidy on micro irrigation equipment installation.",
        "application_process": "Sample process: submit application with land records to district office.",
        "official_website": "https://example.dev/micro-irrigation-sample",
        "criteria": [
            {
                "criterion_type": "profile",
                "field_name": "irrigation_status",
                "operator": "in",
                "expected_value": "rainfed,canal,borewell",
                "description": "Farmer must have eligible irrigation status",
            },
            {
                "criterion_type": "profile",
                "field_name": "land_holding",
                "operator": "greater_than",
                "expected_value": "0.5",
                "description": "Minimum land holding required",
            },
        ],
    },
    {
        "name": "Farm Equipment Subsidy (Sample)",
        "short_description": "Sample subsidy for tractors and farm machinery.",
        "detailed_description": (
            "Development sample equipment subsidy for farmers adopting mechanization. "
            "For local testing only."
        ),
        "department": "State Agriculture Department (Sample)",
        "state": "Telangana",
        "scheme_type": "Equipment Subsidy",
        "benefits": "Sample benefit: partial subsidy on approved farm equipment.",
        "application_process": "Sample process: apply through dealer empanelled under the scheme.",
        "official_website": "https://example.dev/equipment-subsidy-sample",
        "criteria": [
            {
                "criterion_type": "profile",
                "field_name": "state",
                "operator": "equals",
                "expected_value": "Telangana",
                "description": "Farmer's state must match scheme coverage",
            },
            {
                "criterion_type": "profile",
                "field_name": "annual_income",
                "operator": "less_than_or_equal",
                "expected_value": "300000",
                "description": "Annual income must be within subsidy limits",
            },
            {
                "criterion_type": "profile",
                "field_name": "farming_type",
                "operator": "in",
                "expected_value": "commercial,subsistence,mixed",
                "description": "Farming type must be eligible",
            },
        ],
    },
    {
        "name": "Soil Health Card Support (Sample)",
        "short_description": "Sample support for soil testing and nutrient management.",
        "detailed_description": (
            "Development sample soil health support scheme. "
            "Provides sample benefits for soil testing and advisory services."
        ),
        "department": "Ministry of Agriculture (Sample)",
        "state": "All India",
        "scheme_type": "Soil & Agriculture Support",
        "benefits": "Sample benefit: subsidized soil testing and crop nutrient advisory.",
        "application_process": "Sample process: register at local Krishi Vigyan Kendra.",
        "official_website": "https://example.dev/soil-health-sample",
        "criteria": [
            {
                "criterion_type": "profile",
                "field_name": "occupation",
                "operator": "in",
                "expected_value": "subsistence,commercial,mixed",
                "description": "Farmer profile must indicate eligible farming occupation",
            },
            {
                "criterion_type": "profile",
                "field_name": "gender",
                "operator": "in",
                "expected_value": "male,female,other",
                "description": "Open to all eligible genders",
            },
        ],
    },
    {
        "name": "Women Farmer Livelihood Grant (Sample)",
        "short_description": "Sample grant for women farmers in Telangana.",
        "detailed_description": (
            "Development sample livelihood grant targeted at women farmers. "
            "Used for Phase 4 eligibility testing only."
        ),
        "department": "Telangana Rural Development (Sample)",
        "state": "Telangana",
        "scheme_type": "Financial Assistance",
        "benefits": "Sample benefit: livelihood grant for eligible women farmers.",
        "application_process": "Sample process: apply through village agriculture coordinator.",
        "official_website": "https://example.dev/women-farmer-grant-sample",
        "criteria": [
            {
                "criterion_type": "profile",
                "field_name": "gender",
                "operator": "equals",
                "expected_value": "female",
                "description": "Scheme is for women farmers",
            },
            {
                "criterion_type": "profile",
                "field_name": "state",
                "operator": "equals",
                "expected_value": "Telangana",
                "description": "Farmer must be from Telangana",
            },
            {
                "criterion_type": "profile",
                "field_name": "age",
                "operator": "greater_than_or_equal",
                "expected_value": "18",
                "description": "Minimum age requirement",
            },
        ],
    },
]


def seed_schemes(db) -> int:
    created = 0
    for entry in SAMPLE_SCHEMES:
        existing = db.query(GovernmentScheme).filter(GovernmentScheme.name == entry["name"]).first()
        if existing is not None:
            continue

        criteria = entry["criteria"]
        scheme_data = {key: value for key, value in entry.items() if key != "criteria"}
        scheme = GovernmentScheme(**scheme_data, is_active=True)
        db.add(scheme)
        db.flush()

        for criterion in criteria:
            db.add(SchemeEligibilityCriterion(scheme_id=scheme.id, **criterion))
        created += 1

    db.commit()
    return created


def main() -> int:
    db = SessionLocal()
    try:
        created = seed_schemes(db)
        total = db.query(GovernmentScheme).count()
        print(
            f"Seed complete. Created {created} new sample scheme(s). "
            f"Total schemes in database: {total}."
        )
        print("Note: These are development sample records, not official government data.")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
