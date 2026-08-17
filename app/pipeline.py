import os
import json

from app.extraction.pdf_loader import load_pdf
from app.extraction import llm_extractor
from app.validation.validator import validate_field_group
from app.schemas.policy_schema import (
    InsurerInfo, RoomRentHospitalization, Maternity, WaitingPeriods,
    OtherBenefits, InfertilityAmbulance, BufferWaiver,
    PolicyStructure, Demographics, PreviousPolicyInfo, GMCPolicyOutput,
)


def load_document(pdf_path: str) -> dict:
    print(f"Loading document: {pdf_path}")
    return load_pdf(pdf_path)


def extract_fields(full_text: str) -> dict:
    print("Extracting all fields in a single tool-calling LLM call...")
    return llm_extractor.extract_all_fields(full_text)


def _normalize_sum_insured_tiers(raw) -> list:
    if isinstance(raw, list):
        return [str(item) for item in raw]
    if isinstance(raw, str):
        return [piece.strip() for piece in raw.split(",") if piece.strip()]
    return []


def validate_fields(raw_results: dict) -> dict:
    insurer_raw = raw_results.get("extract_insurer_info", {})
    policy_structure_raw = raw_results.get("extract_policy_structure", {})
    room_rent_raw = raw_results.get("extract_room_rent", {})
    waiting_periods_raw = raw_results.get("extract_waiting_periods", {})
    maternity_raw = raw_results.get("extract_maternity", {})
    other_benefits_raw = raw_results.get("extract_other_benefits", {})
    infertility_buffer_raw = raw_results.get("extract_infertility_buffer", {})
    policy_structure_valid = PolicyStructure(
        family_structure=policy_structure_raw.get("family_structure", {}),
        sum_insured_tiers=_normalize_sum_insured_tiers(
            policy_structure_raw.get("sum_insured_tiers", [])),
    )

    return {
        "insurer_info": validate_field_group(InsurerInfo, insurer_raw),
        "previous_policy": validate_field_group(PreviousPolicyInfo, policy_structure_raw),
        "demographics": validate_field_group(Demographics, policy_structure_raw),
        "policy_structure": policy_structure_valid,
        "room_rent": validate_field_group(RoomRentHospitalization, room_rent_raw),
        "maternity": validate_field_group(Maternity, maternity_raw),
        "waiting_periods": validate_field_group(WaitingPeriods, waiting_periods_raw),
        "other_benefits": validate_field_group(OtherBenefits, other_benefits_raw),
        "infertility_ambulance": validate_field_group(InfertilityAmbulance, infertility_buffer_raw),
        "buffer_waiver": validate_field_group(BufferWaiver, infertility_buffer_raw),
    }


def _count_found_fields(pydantic_obj) -> tuple:
    found = 0
    total = 0
    for field_name, field_value in pydantic_obj.dict().items():
        if isinstance(field_value, dict) and "status" in field_value:
            total += 1
            if field_value["status"] == "found":
                found += 1
    return found, total


def save_output(source_file: str, validated: dict) -> str:
    print("Building final JSON output...")

    final_output = GMCPolicyOutput(
        source_file=source_file,
        insurer=validated["insurer_info"],
        previous_policy=validated["previous_policy"],
        policy_structure=validated["policy_structure"],
        demographics=validated["demographics"],
        room_rent_hospitalization=validated["room_rent"],
        maternity=validated["maternity"],
        waiting_periods=validated["waiting_periods"],
        other_benefits=validated["other_benefits"],
        infertility_ambulance=validated["infertility_ambulance"],
        buffer_waiver=validated["buffer_waiver"],
        additional_notable_information=[],
    )

    total_found = 0
    total_fields = 0
    for group in [validated["insurer_info"], validated["previous_policy"],
                  validated["demographics"], validated["room_rent"],
                  validated["maternity"], validated["waiting_periods"],
                  validated["other_benefits"], validated["infertility_ambulance"],
                  validated["buffer_waiver"]]:
        found, total = _count_found_fields(group)
        total_found += found
        total_fields += total

    final_output.extraction_summary = {
        "fields_found": total_found,
        "fields_not_found": total_fields - total_found,
        "total_fields_checked": total_fields,
    }

    os.makedirs("outputs", exist_ok=True)
    output_filename = os.path.splitext(source_file)[0] + ".json"
    output_path = os.path.join("outputs", output_filename)

    with open(output_path, "w") as f:
        json.dump(final_output.dict(), f, indent=2)

    print(f"Saved output to {output_path}")
    return output_path


def process_pdf(pdf_path: str, source_file: str) -> str:
    loaded = load_document(pdf_path)
    raw_results = extract_fields(loaded["full_text"])
    validated = validate_fields(raw_results)
    return save_output(source_file, validated)
