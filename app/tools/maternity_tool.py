from app.tools.fields import field_schema

maternity_tool = {
    "type": "function",
    "function": {
        "name": "extract_maternity",
        "description": "Maternity/childbirth benefits: 9-month waiting period (Waived/Applied), baby day-one cover, vaccination coverage, normal delivery limits (metro and non-metro), and C-section limits (metro and non-metro). CAUTION: many policies only state ONE limit for Normal delivery and ONE for C-section/LSCS, with no metro/non-metro distinction at all - if that's the case here, put the same figure in both the metro and non-metro field for that delivery type but say so explicitly in 'value' (e.g. 'Rs. 75,000 (not differentiated by metro/non-metro in this document)'), rather than presenting it as if 4 independently confirmed numbers exist.",
        "parameters": {
            "type": "object",
            "properties": {
                "nine_month_waiting_period": field_schema,
                "baby_day_one_cover": field_schema,
                "vaccination_coverage": field_schema,
                "normal_delivery_metro": field_schema,
                "normal_delivery_non_metro": field_schema,
                "c_section_metro": field_schema,
                "c_section_non_metro": field_schema,
            },
            "required": [
                "nine_month_waiting_period", "baby_day_one_cover", "vaccination_coverage",
                "normal_delivery_metro", "normal_delivery_non_metro",
                "c_section_metro", "c_section_non_metro",
            ],
        },
    },
}