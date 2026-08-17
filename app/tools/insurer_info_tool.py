from app.tools.fields import field_schema

insurer_info_tool = {
    "type": "function",
    "function": {
        "name": "extract_insurer_info",
        "description": "Basic insurer identification, usually on the first few pages. tpa_name must be an actual company explicitly labeled as a Third Party Administrator / TPA in the document - not the generic words 'Third Party Administrator', and NOT a name from an 'Intermediary Details', 'Broker', or 'Agent' section (those are a different role from a TPA, even though they're often on the same page). If no TPA is explicitly named anywhere, set status to not_found - do not substitute the broker/intermediary name.",
        "parameters": {
            "type": "object",
            "properties": {"insurer_name": field_schema,"tpa_name": field_schema,"is_gmc_policy": field_schema,},
            "required": ["insurer_name", "tpa_name", "is_gmc_policy"]
            },
    },
}