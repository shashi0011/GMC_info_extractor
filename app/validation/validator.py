from pydantic import ValidationError
def validate_field_group(pydantic_model_class, raw_json: dict):
    try:
        return pydantic_model_class(**raw_json)
    except ValidationError as error:
        print(f"Validation failed for {pydantic_model_class.__name__}: {error}")
        print("Using default empty values for this field group.")
        return pydantic_model_class()
