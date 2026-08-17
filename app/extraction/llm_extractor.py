import os
import json
import re
import time
import copy
from openai import OpenAI, RateLimitError, APIStatusError

DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
DEBUG_LOG_DIR = "debug_logs"

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "").strip().lower()

PROVIDER_SPECS = {
    "groq": {
        "api_key_env": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "model_env": "GROQ_MODEL_NAME",
        "default_model": "llama-3.3-70b-versatile",
    },
    "gemini": {
        "api_key_env": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model_env": "GEMINI_MODEL_NAME",
        "default_model": "gemini-flash-latest",
    },
    "openrouter": {
        "api_key_env": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "model_env": "OPENROUTER_MODEL_NAME",
        "default_model": "meta-llama/llama-3.3-70b-instruct",
    },
    "cerebras": {
        "api_key_env": "CEREBRAS_API_KEY",
        "base_url": "https://api.cerebras.ai/v1",
        "model_env": "CEREBRAS_MODEL_NAME",
        "default_model": "llama3.1-70b",
    },
    "openai": {
        "api_key_env": "OPENAI_API_KEY",
        "base_url": None,
        "model_env": "OPENAI_MODEL_NAME",
        "default_model": "gpt-4o-mini",
    },
}

max_retry = 3


def _build_client(provider: str):
    spec = PROVIDER_SPECS[provider]
    key = os.environ.get(spec["api_key_env"])
    if not key:
        return None
    model = os.environ.get(spec["model_env"]) or spec["default_model"]
    kwargs = {"api_key": key}
    if spec["base_url"]:
        kwargs["base_url"] = spec["base_url"]
    return OpenAI(**kwargs), model


def _get_provider():
    if not LLM_PROVIDER:
        print("LLM_PROVIDER is not set in the environment. Set it to one of: "
              f"{', '.join(PROVIDER_SPECS)}.")
        return None, None, None
    if LLM_PROVIDER not in PROVIDER_SPECS:
        print(f"LLM_PROVIDER='{LLM_PROVIDER}' is not a known provider "
              f"(expected one of: {', '.join(PROVIDER_SPECS)}).")
        return None, None, None
    built = _build_client(LLM_PROVIDER)
    if built is None:
        print(f"LLM_PROVIDER='{LLM_PROVIDER}' is set but "
              f"{PROVIDER_SPECS[LLM_PROVIDER]['api_key_env']} is not configured.")
        return None, None, None
    client, model = built
    return LLM_PROVIDER, client, model


def _is_daily_quota_error(error) -> bool:
    text = str(error)
    return ("PerDay" in text) or ("per day" in text.lower()) or ("requests per day" in text.lower())



rule = """
You are extracting information from an Indian Group Medical Cover (GMC) insurance policy document.
Rules you must always follow:
1. Only use information that is actually written in the document text given to you.
2. Do NOT guess, assume, or fill in typical/average values.
3. If a field is not mentioned anywhere in the document, set "status": "not_found", "value": null, and "source_page": null.
4. If you find a field, set "status": "found" and put the exact value (numbers, percentages, conditions) in "value".
5. Whenever you can tell which page a value came from (the text has [PAGE X] markers), put that page number in "source_page". If unsure, use null.
6. IMPORTANT - explicit exclusions are FOUND, not not_found: if the document explicitly states a topic is excluded, "outside the scope of the policy", "not covered", or similar, that is a real answer you found - set "status": "found" and "value" to something like "Excluded" or "Not covered" (quote the document's own wording where possible). Reserve "not_found" ONLY for topics the document never mentions at all. Marking an explicit exclusion as not_found is treated as a wrong answer.

   Do NOT flip this the other way. Being unable to find a benefit mentioned
   anywhere is NOT the same as the document excluding it - it is simply
   not_found. Before you set status "found" with value "Not covered" or
   "Excluded" for any benefit, you must be able to point to the actual
   sentence or clause that says so. If you cannot quote or closely
   paraphrase that sentence, the correct answer is not_found, not "found:
   Not covered".
   WRONG example: the document never mentions OPD Benefit anywhere ->
     {"status": "found", "value": "Not covered"}. This is WRONG - absence
     of a benefit from the document is not_found.
   RIGHT example: the document says "Domiciliary Hospitalization is
     specifically excluded" -> {"status": "found", "value": "Excluded -
     specifically excluded per policy terms"}. This is RIGHT because you
     can point to the actual excluding sentence.
   Treat "not_found" and "found: Not covered" as two genuinely different
   claims about two different situations - do not use the second one as a
   default guess for benefits a coverage-focused document simply didn't
   happen to bring up.
7. IMPORTANT - never fabricate granularity the document does not provide: if a field asks for a more specific breakdown than the document gives (for example separate metro/non-metro figures) and the document only states one undifferentiated figure, DO NOT invent a split by copying the same number into every related field as if they were independently confirmed. Instead, put the single figure into whichever fields it clearly applies to and explicitly note in "value" that the document does not differentiate (for example: "Rs. 75,000 (document does not distinguish metro/non-metro)").
8. IMPORTANT - watch for table-header numbers being mistaken for data: insurance tables sometimes have a row or column labelled with a Sum Insured tier/band (e.g. "Sum Insured: Rs. 200,000") as context for the row, separate from the actual limit value in that row (e.g. "No Limit"). Do not report the tier/band label as if it were the limit itself - read which column a number is actually under before extracting it.
9. IMPORTANT - an override does not have to give a new number, it can REMOVE a cap entirely: watch for a "Special Conditions" / endorsement / scheme-specific section that says something like "no separate cap", "not applicable", "no limit", or "this clause does not apply" about a general rule (e.g. room rent %, ICU %, a waiting period, a sub-limit table). That kind of override is just as real as one that gives a replacement number, and it must win over the general clause it cancels - do not report the general clause's number as if it still applies once you've seen it explicitly cancelled.
10. IMPORTANT - only mark a field "found" if the document states an actual value for that specific question, not just a definition of the concept or a description of who/what the policy generally covers. For example, a sentence explaining what "policy tenure" or "family structure" means in general, or that coverage applies to "employees and their eligible family members", is NOT itself a tenure duration or a family composition - it does not answer the field. If you cannot point to an actual value (a duration, a composition like "Self + Spouse + 2 Children", a number, a date), the field is not_found even if the topic is discussed nearby.

Some fields have both a general/default rule AND a policy-specific override or
exception written elsewhere in the document (for example, a standard room
rent percentage that a later clause overrides for this particular policy or
employee category). Always report the policy-specific override value, not
the general default, when both are present in the document.

For waiver_conditions specifically: only report waivers that relate to
waiting periods or benefit eligibility (e.g. a waiting period being waived
for this group). Do not report claim-notification or claim-submission
waivers - those are a different topic and should be left out.
"""


def _fields_prompt_block(tools: list) -> str:

    lines = []
    example_lines = ["{"]
    for tool in tools:
        fn = tool["function"]
        lines.append(f"From \"{fn['name']}\" - {fn['description']}")
        props = fn["parameters"]["properties"]
        for field_name, field_schema in props.items():
            if field_schema.get("type") == "array":
                # Plain-array fields (e.g. sum_insured_tiers) are NOT
                # wrapped in status/value/source_page - just a bare list.
                lines.append(f'  - "{field_name}": a plain JSON list of strings, e.g. [] or ["500000", "700000"]')
                example_lines.append(f'  "{field_name}": ["500000", "700000"],')
            else:
                lines.append(f'  - "{field_name}"')
                example_lines.append(
                    f'  "{field_name}": {{"status": "found/not_found", "value": "...", "source_page": 1}},'
                )
    example_lines.append("}")
    fields_text = "\n".join(lines)
    example_text = "\n".join(example_lines)
    return f"""Extract these fields:
{fields_text}

Return ONLY a single JSON object, no other text, no markdown code fences,
in exactly this shape (one entry per field above, using null for value/
source_page when status is "not_found"):
{example_text}"""


def _extract_json_object(raw_text: str) -> dict:
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _validate_group_shape(parsed: dict, tools: list) -> list:

    problems = []
    for tool in tools:
        props = tool["function"]["parameters"]["properties"]
        for field_name, field_schema in props.items():
            if field_name not in parsed:
                problems.append(f"missing field '{field_name}'")
                continue
            value = parsed[field_name]
            if field_schema.get("type") == "array":
                if not isinstance(value, list):
                    problems.append(f"'{field_name}' should be a JSON list, got {type(value).__name__}")
            else:
                if not isinstance(value, dict) or "status" not in value:
                    problems.append(f"'{field_name}' should be an object with a 'status' key")
    return problems


def _normalize_group_results(results: dict) -> dict:

    def normalize_node(node):
        if isinstance(node, dict):
            if "status" in node and ("value" in node or "source_page" in node):
                if node.get("status") != "found":
                    if "value" in node:
                        node["value"] = None
                    if "source_page" in node:
                        node["source_page"] = None
                else:
                    if node.get("value") == "":
                        node["value"] = None
                    if node.get("source_page") == 0:
                        node["source_page"] = None
            else:
                for key, value in node.items():
                    node[key] = normalize_node(value)
        elif isinstance(node, list):
            return [normalize_node(item) for item in node]
        return node

    for tool_name, arguments in results.items():
        results[tool_name] = normalize_node(arguments)
    return results


def _dump_debug_file(label: str, raw: str) -> str:
    os.makedirs(DEBUG_LOG_DIR, exist_ok=True)
    filename = f"{DEBUG_LOG_DIR}/{label}_{int(time.time())}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(raw if raw else "(empty response)")
    return filename


from app.tools.insurer_info_tool import insurer_info_tool
from app.tools.policy_structure_tool import policy_structure_tool
from app.tools.room_rent_tool import room_rent_tool
from app.tools.waiting_periods_tool import waiting_periods_tool
from app.tools.maternity_tool import maternity_tool
from app.tools.other_benefits_tool import other_benefits_tool
from app.tools.infertility_buffer_tool import infertility_buffer_tool
TOOL_GROUPS = [
    ("insurer_info", [insurer_info_tool]),
    ("policy_structure", [policy_structure_tool]),
    ("room_rent_and_waiting", [room_rent_tool, waiting_periods_tool]),
    ("maternity", [maternity_tool]),
    ("other_benefits", [other_benefits_tool]),
    ("infertility_and_buffer", [infertility_buffer_tool]),
]

GROUP_NOTES_TOPICS = {
    "insurer_info": ["insurer_and_tpa"],
    "policy_structure": ["policy_dates_and_demographics"],
    "room_rent_and_waiting": ["room_rent_and_icu", "waiting_periods"],
    "maternity": ["maternity"],
    "other_benefits": ["other_benefits"],
    "infertility_and_buffer": ["infertility_and_buffer", "waiting_periods"],
}

EVIDENCE_TOPICS = {
    "insurer_and_tpa": "Insurer name, TPA name, whether this is a GMC/group health policy",
    "policy_dates_and_demographics": "Policy start/end dates, policy tenure (an actual duration, e.g. '1 year' - not a general statement about how tenure works), previous year premium, family structure (an actual composition, e.g. 'Self + Spouse + 2 Children' - not a general statement that the policy covers employees and family members), sum insured tiers, total employees/spouses/children/parents/lives covered",
    "room_rent_and_icu": "Room rent percentage/limit, ICU percentage/limit, pre and post hospitalization days - watch for Sum Insured tier labels in tables being mistaken for the actual limit, AND check specifically for a 'Special Conditions'/endorsement section stating there is no separate cap for room rent/ICU under this scheme, which overrides any general percentage cap found elsewhere",
    "waiting_periods": "30-day initial waiting period, first/second year disease exclusion waiting period, pre-existing disease waiting period",
    "maternity": "9-month maternity waiting period, baby day-one cover, vaccination coverage, normal delivery limits, C-section/LSCS limits - note explicitly if the document does NOT distinguish metro/non-metro",
    "other_benefits": "Day care expenses, OPD benefit, teleconsultation, pharmacy discount, domiciliary hospitalization, annual health checkup, modern/bariatric/psychiatric treatment, AYUSH treatment, LGBTQ coverage, live-in partner coverage, organ donor expenses",
    "infertility_and_buffer": "Infertility treatment, surrogacy, ambulance charges, air ambulance charges, corporate buffer limit, disease-wise capping, waiver conditions for waiting periods (check the waiting-period clauses too - if any waiting period is waived, that IS a waiver condition and must be reported here, not just 'no waiver conditions')",
}


def _extract_evidence_notes(document_text: str) -> dict:
    """Pass 1: a single plain call (no tool schema) that condenses the full
    document into short quoted evidence + page numbers per topic. Returns
    {topic_key: notes_text}. If this call fails outright, returns an empty
    dict and pass 2 falls back to sending the full document per group
    (slower/more tokens, but still correct) - see _notes_for_group.
    """
    topics_block = "\n".join(f'- "{key}": {desc}' for key, desc in EVIDENCE_TOPICS.items())

    system_instructions = f"""You are pre-processing an Indian Group Medical Cover (GMC) insurance policy
document so a second step can extract structured fields from it. Your job is
NOT to produce the final structured answer - it's to condense the document
down to only the sentences/clauses relevant to each topic below, with page
numbers, so almost nothing relevant gets lost but irrelevant boilerplate is
dropped.

For each topic, pull out the exact relevant sentences or clause text
(paraphrase only if the original is very long-winded), and the page number
(from [PAGE X] markers) each came from. Include BOTH a general/default rule
AND any policy-specific override or exception you find for the same topic -
do not resolve the conflict yourself, just capture both so the next step can
decide which applies. If a topic has nothing relevant anywhere in the
document, say so explicitly rather than leaving it out.

Topics:
{topics_block}

Respond with a single JSON object whose keys are exactly the topic keys
above (in quotes as shown) and whose values are the condensed notes text for
that topic."""

    messages = [
        {"role": "system", "content": system_instructions},
        {"role": "user", "content": f"DOCUMENT TEXT:\n{document_text}"},
    ]

    provider, client, model = _get_provider()
    if provider is not None:
        kwargs = dict(
            model=model,
            temperature=0,
            max_tokens=6000,
            messages=messages,
            response_format={"type": "json_object"},
        )
        if provider in ("gemini", "cerebras"):
            kwargs["extra_body"] = {"reasoning_effort": "none"}

        response = None
        for attempt in range(1, max_retry + 1):
            try:
                response = client.chat.completions.create(**kwargs)
                break
            except RateLimitError as error:
                if _is_daily_quota_error(error):
                    print(f"[{provider}] Hit a DAILY quota limit during evidence "
                          "extraction. LLM_PROVIDER is fixed to this provider, so "
                          "there is no fallback - evidence extraction fails for "
                          "this run until the quota resets.")
                    response = None
                    break
                wait_seconds = 20
                match = re.search(r"retry in ([\d.]+)s", str(error), re.IGNORECASE)
                if match:
                    wait_seconds = float(match.group(1)) + 2
                print(f"[{provider}] Rate limited during evidence extraction "
                      f"(attempt {attempt}/{max_retry}). Waiting {wait_seconds:.0f}s...")
                time.sleep(wait_seconds)
            except APIStatusError as error:
                body_message = None
                try:
                    body_message = error.response.json().get("error", {}).get("message")
                except Exception:
                    body_message = getattr(error, "message", None) or str(error)
                print(f"[{provider}] Evidence extraction request failed "
                      f"({error.status_code}): {body_message}.")
                response = None
                break

        if response is not None:
            raw_text = response.choices[0].message.content
            try:
                notes = json.loads(raw_text)
                if isinstance(notes, dict):
                    print(f"Evidence pre-extraction done via {provider} "
                          f"({len(raw_text)} chars condensed from the full document).")
                    return notes
            except (json.JSONDecodeError, TypeError):
                path = _dump_debug_file("evidence_notes", raw_text or "")
                print(f"Evidence extraction returned invalid JSON (see {path}). "
                      "Falling back to sending the full document per group.")
                return {}

    print("Evidence pre-extraction failed. Falling back to sending the full "
          "document per group (slower, more tokens, but still correct).")
    return {}


def _notes_for_group(group_name: str, evidence_notes: dict, document_text: str) -> str:
    if not evidence_notes:
        return document_text
    topics = GROUP_NOTES_TOPICS.get(group_name, [])
    parts = []
    for topic in topics:
        notes = evidence_notes.get(topic)
        if notes:
            parts.append(f"### {topic}\n{notes}")
    combined = "\n\n".join(parts)
    if len(combined) < 20:
        return document_text
    return combined


def _split_by_tool(parsed: dict, tools: list) -> dict:
    by_tool = {}
    for tool in tools:
        name = tool["function"]["name"]
        props = tool["function"]["parameters"]["properties"]
        by_tool[name] = {}
        for field_name, field_schema in props.items():
            if field_name in parsed:
                by_tool[name][field_name] = parsed[field_name]
            elif field_schema.get("type") == "array":
                by_tool[name][field_name] = []
            else:
                by_tool[name][field_name] = {"status": "not_found", "value": None, "source_page": None}
    return by_tool


def _call_one_group(input_text: str, tools: list) -> dict:

    tool_names = [t["function"]["name"] for t in tools]
    fields_block = _fields_prompt_block(tools)

    system_instructions = f"""{rule}

{fields_block}"""

    messages = [
        {"role": "system", "content": system_instructions},
        {"role": "user", "content": f"DOCUMENT TEXT:\n{input_text}"},
    ]

    provider, client, model = _get_provider()
    if provider is None:
        print(f"Returning empty results for tool group {tool_names}.")
        return {name: {} for name in tool_names}

    kwargs = dict(
        model=model,
        temperature=0,
        max_tokens=4000,
        messages=list(messages),
        response_format={"type": "json_object"},
    )
    if provider in ("gemini", "cerebras"):
        kwargs["extra_body"] = {"reasoning_effort": "none"}

    response = None
    last_error = None
    for attempt in range(1, max_retry + 1):
        try:
            response = client.chat.completions.create(**kwargs)
            break
        except RateLimitError as error:
            if _is_daily_quota_error(error):
                print(f"[{provider}] Hit a DAILY quota limit (not a "
                      "per-minute rate limit) - retrying won't help until "
                      "it resets. LLM_PROVIDER is fixed to this provider, "
                      "so there is no fallback.")
                last_error = error
                response = None
                break
            wait_seconds = 20
            match = re.search(r"retry in ([\d.]+)s", str(error), re.IGNORECASE)
            if match:
                wait_seconds = float(match.group(1)) + 2
            print(f"[{provider}] Rate limited (attempt {attempt}/{max_retry}). "
                  f"Waiting {wait_seconds:.0f}s before retrying...")
            time.sleep(wait_seconds)
            last_error = error
        except APIStatusError as error:
            body_message = None
            try:
                body_message = error.response.json().get("error", {}).get("message")
            except Exception:
                body_message = getattr(error, "message", None) or str(error)
            print(f"[{provider}] Request failed ({error.status_code}): {body_message}.")
            last_error = error
            response = None
            break

    if response is not None:
        raw_text = response.choices[0].message.content
        try:
            parsed = _extract_json_object(raw_text)
        except (json.JSONDecodeError, TypeError) as error:
            path = _dump_debug_file("_".join(tool_names), raw_text or "")
            print(f"[{provider}] Response was not valid JSON (see {path}): {error}. "
                  "Attempting one repair retry...")
            parsed = None

        shape_problems = _validate_group_shape(parsed, tools) if parsed is not None else ["invalid JSON"]

        if shape_problems:
            print(f"[{provider}] Shape issues: {shape_problems}. Retrying once with the error fed back...")
            repair_messages = list(messages) + [
                {"role": "assistant", "content": raw_text or "(empty response)"},
                {"role": "user", "content": (
                    "That response had problems: " + "; ".join(shape_problems) +
                    ". Return the corrected JSON object only, same format as instructed, "
                    "nothing else."
                )},
            ]
            try:
                repair_kwargs = dict(kwargs)
                repair_kwargs["messages"] = repair_messages
                repair_response = client.chat.completions.create(**repair_kwargs)
                raw_text = repair_response.choices[0].message.content
                parsed = _extract_json_object(raw_text)
                shape_problems = _validate_group_shape(parsed, tools)
            except Exception as error:
                print(f"[{provider}] Repair retry failed: {error}.")
                parsed = None
                shape_problems = ["repair retry failed"]

        if parsed is not None and not shape_problems:
            if DEBUG:
                usage = getattr(response, "usage", None)
                print(f"provider={provider} model={model} usage={usage} "
                      f"fields_returned={list(parsed.keys())}")
            by_tool = _split_by_tool(parsed, tools)
            return _normalize_group_results(by_tool)

        print(f"[{provider}] Could not get a valid response for this group "
              f"even after a repair retry ({shape_problems}).")

    print(f"[{provider}] Failed for tool group {tool_names}.")
    raise RuntimeError(
    f"LLM extraction failed for tool group {tool_names}. "
    f"Last error: {last_error}"
)


def extract_all_fields(document_text: str) -> dict:
    print("Pass 1: condensing document into per-topic evidence notes...")
    evidence_notes = _extract_evidence_notes(document_text)

    split_mode = os.environ.get("EXTRACTION_MODE", "").strip().lower() == "split"

    if split_mode:
        combined_results = {}
        for group_name, tools in TOOL_GROUPS:
            print(f"Pass 2: extracting group '{group_name}' "
                  f"({', '.join(t['function']['name'] for t in tools)})...")
            group_input = _notes_for_group(group_name, evidence_notes, document_text)
            group_results = _call_one_group(group_input, tools)
            combined_results.update(group_results)
        return combined_results

    print("Pass 2: extracting all fields in a single combined call...")
    all_tools = [tool for _, tools in TOOL_GROUPS for tool in tools]
    if evidence_notes:
        pass2_input = "\n\n".join(
            f"### {topic}\n{notes}" for topic, notes in evidence_notes.items() if notes
        ) or document_text
    else:
        pass2_input = document_text
    return _call_one_group(pass2_input, all_tools)