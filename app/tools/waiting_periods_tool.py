from app.tools.fields import field_schema

waiting_periods_tool = {
    "type": "function",
    "function": {
        "name": "extract_waiting_periods",
        "description": "30-day initial waiting period, first/second year disease exclusion waiting period, and pre-existing disease waiting period.",
        "parameters": {
            "type": "object",
            "properties": {
                "thirty_day_waiting_period": field_schema,
                "first_second_year_waiting_period": field_schema,
                "pre_existing_disease_waiting_period": field_schema,
            },
            "required": [
                "thirty_day_waiting_period",
                "first_second_year_waiting_period",
                "pre_existing_disease_waiting_period",
            ],
        },
    },
}