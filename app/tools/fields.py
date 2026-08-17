field_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["found", "not_found"]},
        "value": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "source_page": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
    },
    "required": ["status", "value", "source_page"],
}