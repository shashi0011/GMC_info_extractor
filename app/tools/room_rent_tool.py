from app.tools.fields import field_schema

room_rent_tool = {
    "type": "function",
    "function": {
        "name": "extract_room_rent",
        "description": "Room rent percentage and max limit, ICU percentage and max limit, pre-hospitalization days, post-hospitalization days. WARNING 1: room rent tables often list a 'Sum Insured' figure as a row/column label purely to identify which SI tier the row's limits apply to - that Sum Insured number is NOT the room rent limit, and it is NOT the ICU limit either. A typical row has THREE separate columns - Sum Insured, [Normal/Room Rent] limit, and [ICU] limit - read each one from its own column; do not let the Sum Insured column leak into either of the other two, and do not assume that because you got ICU right from its column, Room Rent must be the same number from a different column. Check room_rent_max_limit and icu_max_limit independently, each against its own column header. WARNING 2: many policies have a base/general room rent and ICU percentage cap, but then a scheme-specific 'Special Conditions' section that says there is 'no separate cap' for room rent/ICU for THIS particular scheme - if you see such a special-conditions section anywhere in the document, that override wins and the correct answer is 'no cap', NOT the general percentage. Search the whole document for a special/endorsement section before settling on the general clause's number.",
        "parameters": {
            "type": "object",
            "properties": {
                "room_rent_percentage": field_schema,
                "room_rent_max_limit": field_schema,
                "icu_percentage": field_schema,
                "icu_max_limit": field_schema,
                "pre_hospitalization_days": field_schema,
                "post_hospitalization_days": field_schema,
            },
            "required": ["room_rent_percentage", "room_rent_max_limit","icu_percentage", "icu_max_limit","pre_hospitalization_days", "post_hospitalization_days",],
        },
    },
}