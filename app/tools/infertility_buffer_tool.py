from app.tools.fields import field_schema

infertility_buffer_tool = {
    "type": "function",
    "function": {
        "name": "extract_infertility_buffer",
        "description": "Infertility treatment, surrogacy, ambulance charges, air ambulance charges, corporate buffer limit, disease-wise capping, and waiver conditions for waiting periods. IMPORTANT for waiver_conditions: if the document waives the 30-day, first/second-year, pre-existing-disease, or maternity waiting period for this group, that IS a waiver condition - report it here (e.g. '30-day and PED waiting periods waived for all insured members'). Only say there are no waiver conditions if none of the waiting periods are waived anywhere in the document.",
        "parameters": {
            "type": "object",
            "properties": {
                "infertility_treatment": field_schema,
                "surrogacy": field_schema,
                "ambulance_charges": field_schema,
                "air_ambulance_charges": field_schema,
                "corporate_buffer_limit": field_schema,
                "disease_wise_capping": field_schema,
                "waiver_conditions": field_schema,
            },
            "required": [
                "infertility_treatment", "surrogacy", "ambulance_charges", "air_ambulance_charges",
                "corporate_buffer_limit", "disease_wise_capping", "waiver_conditions",
            ],
        },
    },
}