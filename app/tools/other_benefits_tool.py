from app.tools.fields import field_schema

other_benefits_tool = {
    "type": "function",
    "function": {
        "name": "extract_other_benefits",
        "description": "Day care expenses, OPD benefit, teleconsultation, pharmacy discount, domiciliary hospitalization, annual health checkup, modern/bariatric/psychiatric treatment, AYUSH treatment, LGBTQ coverage, live-in partner coverage, and organ donor expenses.",
        "parameters": {
            "type": "object",
            "properties": {
                "day_care_expenses": field_schema,
                "opd_benefit": field_schema,
                "teleconsultation": field_schema,
                "pharmacy_discount": field_schema,
                "domiciliary_hospitalization": field_schema,
                "annual_health_checkup": field_schema,
                "modern_treatment": field_schema,
                "bariatric_treatment": field_schema,
                "psychiatric_treatment": field_schema,
                "ayush_treatment": field_schema,
                "lgbtq_coverage": field_schema,
                "live_in_partner_coverage": field_schema,
                "organ_donor_expenses": field_schema,
            },
            "required": [
                "day_care_expenses", "opd_benefit", "teleconsultation", "pharmacy_discount",
                "domiciliary_hospitalization", "annual_health_checkup", "modern_treatment",
                "bariatric_treatment", "psychiatric_treatment", "ayush_treatment",
                "lgbtq_coverage", "live_in_partner_coverage", "organ_donor_expenses",
            ],
        },
    },
}