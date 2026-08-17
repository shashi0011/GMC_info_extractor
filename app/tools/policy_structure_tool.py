from app.tools.fields import field_schema

sum_insured = {
    "type": "array",
    "items": {"type": "string"},
}
policy_structure_tool = {
    "type": "function",
    "function": {
        "name": "extract_policy_structure",
        "description": "Policy dates/tenure/premium (an actual duration/date, not a general statement about how tenure works), family structure (an actual composition like 'Self + Spouse + 2 Children', not a general statement that the policy covers employees and family members), sum insured tiers, and headcount demographics (employees, spouses, children, parents, total lives covered). IMPORTANT for sum_insured_tiers: this means the per-person/per-employee sum insured amount(s) offered under the policy (sometimes shown as an 'Age Band/SI' or per-life premium table, or a plan/tier table with several SI options) - NOT the single aggregate 'Total Sum Insured' figure for the whole group, which is just total_employees/lives multiplied by the per-person tier and is not itself a tier.",
        "parameters": {
            "type": "object",
            "properties": {
                "inception_date": field_schema,
                "renewal_date": field_schema,
                "policy_tenure": field_schema,
                "inception_premium": field_schema,
                "family_structure": field_schema,
                "sum_insured_tiers": sum_insured,
                "total_employees": field_schema,
                "total_spouses": field_schema,
                "total_children": field_schema,
                "total_parents": field_schema,
                "total_lives_covered": field_schema,
            },
            "required": [
                "inception_date", "renewal_date", "policy_tenure", "inception_premium","family_structure", "sum_insured_tiers",
                "total_employees", "total_spouses", "total_children","total_parents", "total_lives_covered",
            ],
        },
    },
}