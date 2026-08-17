# GMC Policy Information Extractor

This project was built so that  It reads Group Medical Cover (GMC) insurance policy documents from different insurers and extracts the important information into a structured JSON file.

## 1. Project Overview

GMC policies are not written in one fixed format. Every insurer lays out its policy document differently, room rent may be in a table for one insurer and in a paragraph for another, waiting periods may be on page 3 in one document and inside an endorsement on page 40 in another. A system built on fixed keywords or fixed page numbers breaks as soon as it sees a new insurer's layout.

To avoid that problem, this project uses a Large Language Model (LLM) to do the reading, instead of hardcoded rules or regex. The document text (including tables) is given to the LLM with clear instructions, and it returns the answer in a fixed JSON structure. This approach is not tied to any one insurer's format, so it generalises to new documents.

The system was tested on seven sample policy documents from different insurers. The generated JSON for each one is included in the `outputs/` folder.

## 2. Architecture and Approach

Every PDF goes through four steps:

1. **Text extraction** – `pdfplumber` reads the normal text and tables from each page. If a page has almost no extractable text (a scanned page), it is OCR'd using `pytesseract` instead.
2. **Evidence notes (LLM pass 1)** – One LLM call reads the full document and condenses it into short, topic-wise notes (room rent, maternity, waiting periods, and so on), with page numbers kept for each note. This keeps the next step focused and less likely to miss something.
3. **Field extraction (LLM pass 2)** – The condensed notes are sent back to the LLM with a detailed schema of exactly which fields to fill. The model is told to only use what the document actually says, never guess typical values, and to correctly tell apart "not mentioned" from "explicitly excluded." If the response comes back invalid, the system asks the model once to fix it.
4. **Validation** – The raw JSON is checked against Pydantic models (`app/schemas/policy_schema.py`), so any malformed field falls back to a safe default instead of crashing the run. A small `extraction_summary` (fields found vs. not found) is added before saving.

```
PDF → pdfplumber (+ OCR fallback) → LLM pass 1: evidence notes
    → LLM pass 2: structured extraction → Pydantic validation → outputs/<filename>.json
```

## 3. Technologies Used

- Python 3
- `pdfplumber` – PDF text and table extraction
- `pytesseract` + `Pillow` – OCR for scanned pages
- `openai` SDK – used as a generic client, since most LLM providers now support the OpenAI-style chat API
- `pydantic` – schema definition and validation of the LLM's output
- `python-dotenv` – loads API keys from `.env`
- `pytest` – tests

**Note on the LLM provider:** A single environment variable, `LLM_PROVIDER`, decides which provider is actually called. The `openai` SDK just points at a different `base_url` per provider. Supported providers:

| Provider      | `LLM_PROVIDER` value | Key needed in `.env` |
|---------------|-----------------------|------------------------|
| Google Gemini | `gemini`              | `GEMINI_API_KEY`        |
| Groq          | `groq`                | `GROQ_API_KEY`           |
| OpenAI        | `openai`              | `OPENAI_API_KEY`         |
| OpenRouter    | `openrouter`           | `OPENROUTER_API_KEY`     |
| Cerebras      | `cerebras`             | `CEREBRAS_API_KEY`       |

Only one provider is used per run, there is no automatic fallback between providers. This project was mainly developed and tested using Gemini (`gemini-flash-latest`), which is fast and has a generous free tier, good for repeated testing during development. Normal usage charges from the chosen provider apply if you use a paid key.

## 4. Repository Structure

```
GMC_Extractor_new-master/
├── main.py                  # Entry point
├── requirements.txt
├── .env.example
├── app/
│   ├── pipeline.py           # Orchestrates loading, extraction, validation, saving
│   ├── extraction/
│   │   ├── pdf_loader.py      # pdfplumber text + tables
│   │   ├── ocr.py             # OCR fallback
│   │   └── llm_extractor.py   # Both LLM passes
│   ├── schemas/policy_schema.py   # Pydantic output models
│   ├── tools/                 # Field-group schemas sent to the LLM
│   └── validation/validator.py
├── data/sample_policies/     # Sample GMC policy PDFs
├── outputs/                   # Generated JSON per sample PDF
└── debug_logs/                 # Raw LLM responses, saved only on errors
```

## 5. Setup Instructions

**Requirements**
- Python 3.10+
- Tesseract OCR (only needed for scanned PDFs): `brew install tesseract` (Mac), `sudo apt-get install tesseract-ocr` (Ubuntu), or the [Windows installer](https://github.com/UB-Mannheim/tesseract/wiki)
- An API key from at least one supported provider (Gemini's free tier is enough)

**Install**

```bash
git clone <this-repository-url>
cd GMC_Extractor_new-master
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env` and set:

```
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
```

Only fill in the key for the one provider you choose. Model name variables are optional, a sensible default is used if left blank.

## 6. How to Run

Process every PDF in `data/sample_policies/`:

```bash
python main.py
```

Process a single PDF:

```bash
python main.py "data/sample_policies/GHI Policy.pdf"
```

Output JSON files are saved to `outputs/`, one per input PDF, using the same file name. Progress prints to the terminal as it runs.

## 7. Extraction Methodology

The LLM is treated as the reader, not a rule engine, but it is constrained carefully so it does not guess:

- Only uses information actually present in the document, never assumes typical values.
- Every field carries a `status` of `found` or `not_found`, so it's always clear whether an answer came from the document.
- "Not mentioned anywhere" (`not_found`) is kept strictly separate from "explicitly excluded" (`found`, value like "Excluded") — the prompt gives worked examples of both so these aren't confused.
- When a document has both a general rule and a policy-specific override (e.g. a standard room rent % vs. an endorsement that removes it), the override is reported, not the default.
- If the document gives one combined figure instead of a metro/non-metro split, the model says so explicitly rather than inventing a split.
- Page numbers are tracked via `[PAGE X]` markers added during loading, so each value can be traced to its source.

Extraction happens in two passes (see Architecture above) to keep answers focused and manage document size. An optional `EXTRACTION_MODE=split` in `.env` sends each field group to the LLM as its own smaller call instead of one combined call, useful for unusually dense documents at the cost of more LLM calls. Default mode uses one combined call.

## 8. JSON Schema and Mapping Logic

Defined in `app/schemas/policy_schema.py`. Top-level sections: `insurer`, `previous_policy`, `policy_structure`, `demographics`, `room_rent_hospitalization`, `maternity`, `waiting_periods`, `other_benefits`, `infertility_ambulance`, `buffer_waiver`, plus `extraction_summary`.

Except for `sum_insured_tiers` (a plain list of strings) and `extraction_summary`, every field uses the same repeating shape:

```json
{ "status": "found", "value": "the extracted value as text", "source_page": 12 }
```
or
```json
{ "status": "not_found", "value": null, "source_page": null }
```

One consistent shape means a downstream system (like an internal QMS) can loop over the JSON the same way for all ~40 data points, without separate parsing logic per field.

## 9. Assumptions Made

- The sample PDFs are genuine GMC/group health policies, and the assignment's field list is the complete set needed by the QMS.
- Values with multiple parts or conditions are kept as human-readable text rather than force-split into separate numeric fields, since insurance wording often can't be split without changing its meaning.
- All values are stored as strings, since limits often carry conditions (e.g. "up to 2% of SI or actuals, whichever is lower") that a plain number would lose.
- If several provider keys exist in `.env` at once, only the one named in `LLM_PROVIDER` is used.
- OCR only runs on pages with very little extractable text, on the assumption this reliably flags scanned pages without OCR-ing every page.

## 10. Known Limitations

- Extraction quality depends on the LLM used; smaller/free-tier models can occasionally miss values spread across a table and a footnote.
- No automatic fallback to another provider if the chosen one fails or returns an unusable response after one repair retry — that document is simply skipped with an error.
- Free-tier providers apply rate limits, so large batches may need short waits between calls; handled with basic retry-and-wait, but big batches still take time.
- OCR accuracy depends on scan quality; a poor or skewed scan can still produce imperfect text.
- This is a working prototype, not hardened for production (no queue system, no cross-provider retry, no persistent database).

## 11. Sample Output

The `outputs/` folder already contains JSON generated by actually running `python main.py` against `data/sample_policies/`. Nothing in that folder was hand-written or edited.

## 12. Future Improvements

- Automatic fallback to a second LLM provider if the primary one hits its quota.
- A lightweight confidence score per field.
- A simple web interface to upload a PDF and view the extracted JSON side by side with it.
- An automated evaluation script comparing output against a manually verified answer set, to track accuracy as prompts or models change.
