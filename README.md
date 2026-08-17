
# GMC Policy Information Extractor

The goal of the assignment was to build a system that can read Group Medical Cover (GMC) insurance policy documents from different insurance companies and pull out the important information into a clean, structured JSON file.

This repository contains the full working solution, along with the sample outputs generated from the sample policy PDFs.

## 1. Project Overview

Group Medical Cover policies are not written in one fixed format. Every insurance company writes its policy document in its own way. Some put the room rent limit in a table, some write it inside a paragraph, some mention waiting periods on page 3, others mention the same thing inside an endorsement on page 40. Because of this, a system that only looks for fixed keywords or fixed page numbers will fail as soon as it sees a document from a new insurer.

To handle this, the extraction in this project is done using a Large Language Model (LLM) instead of hardcoded rules or regex patterns. The document text (including tables) is given to the LLM along with clear extraction instructions, and the LLM reads the document the way a human analyst would and returns the answer in a fixed JSON structure. This approach is not tied to any one insurer's layout, so it can generalise to new policy documents without needing new code for each insurer.

The system was tested on seven different sample policy documents from different insurers, and the generated JSON output for each one is included in the `outputs/` folder of this repository.

## 2. Architecture and Approach

The pipeline has four main stages. Each PDF goes through the same four steps.

**Step 1 – Document Loading and Text Extraction**

The PDF is opened using `pdfplumber`. For every page, the normal text is extracted, and any tables on that page are extracted separately and converted into readable `column | column` text so that table data is not lost. If a page has very little extractable text (this usually happens with scanned or image-based pages), the page is converted into an image and passed through OCR using `pytesseract`, and the OCR text is used instead. This way both digitally generated PDFs and scanned PDFs are supported.

**Step 2 – Evidence Notes (Pass 1 of the LLM)**

The full document text can be quite long, sometimes running into many pages. Sending all of it to the LLM every single time is wasteful and also makes it easier for the model to miss something. So before the actual extraction, the system makes one LLM call that reads the whole document and condenses it down into short topic-wise notes, for example one note block for "room rent and ICU", one for "maternity", one for "waiting periods", and so on. This step also carries page numbers along with each note so the source page is not lost later. This is a summarising step, not the final answer step.

**Step 3 – Field Extraction (Pass 2 of the LLM)**

The condensed notes (or the full text, if the notes step could not run) are sent to the LLM again, this time with a detailed set of instructions and a fixed schema describing exactly which fields to fill and what shape the JSON must be in. The LLM is instructed to only use information that is actually present in the document, to never guess or assume typical values, and to clearly separate "the document does not mention this" (not_found) from "the document mentions this and says it is excluded / not covered" (found, with value "Excluded"). The prompt also contains specific rules to avoid common mistakes, for example not confusing a Sum Insured table heading with an actual benefit limit, and giving priority to a special/endorsement clause over a general clause when both exist for the same topic.

If the LLM response is not valid JSON or does not match the expected shape, the system automatically asks the LLM once more to correct its own output before giving up on that section.

**Step 4 – Validation and Final JSON**

The raw JSON coming back from the LLM is passed through Pydantic models (see `app/schemas/policy_schema.py`). This makes sure every field is present, in the right shape, and that any accidentally malformed response gets replaced with a safe empty default instead of crashing the whole run. After validation, the system also adds a small `extraction_summary` block that counts how many fields were found versus not found, which is useful for a quick sanity check without opening the whole JSON.

The final validated JSON is written to the `outputs/` folder using the original PDF file name.

A simple diagram of the flow:

```
PDF file
   |
   v
pdfplumber (text + tables) --> pytesseract OCR (only if a page has almost no text)
   |
   v
Pass 1: LLM condenses full document into topic-wise evidence notes (with page numbers)
   |
   v
Pass 2: LLM extracts structured fields using the evidence notes and a fixed JSON schema
   |
   v
Pydantic validation (fills in safe defaults for anything malformed)
   |
   v
outputs/<filename>.json
```

## 3. Technologies Used

- Python 3
- `pdfplumber` – for reading PDF text and tables
- `pytesseract` and `Pillow` – for OCR on scanned or image-based pages
- `openai` Python SDK – used as a generic client to talk to the chosen LLM provider (see note below)
- `pydantic` – for defining the output schema and validating the LLM's JSON response
- `python-dotenv` – for loading API keys and settings from a `.env` file
- `pytest` – for running tests

**Note on the LLM provider:** The project does not use OpenAI by default. It is built so that a single environment variable, `LLM_PROVIDER`, decides which LLM provider is actually called. The `openai` SDK is used only because most LLM providers now support the same OpenAI-style chat completion API, so the same SDK can point at different providers by changing the `base_url`. The supported providers are:

| Provider     | Set `LLM_PROVIDER` to | Needs this key in `.env` |
|--------------|------------------------|---------------------------|
| Google Gemini| `gemini`               | `GEMINI_API_KEY`           | 
  Groq         | `groq`                 | `GROQ_API_KEY`             |
| OpenAI       | `openai`               | `OPENAI_API_KEY`           |
| OpenRouter   | `openrouter`            | `OPENROUTER_API_KEY`       |
| Cerebras     | `cerebras`              | `CEREBRAS_API_KEY`         |

Only one provider is used per run, there is no automatic fallback from one provider to another. This assignment was mainly developed and tested using Gemini, since it offers a fast, free-tier LLM and better responce parsing which was good enough for testing this pipeline repeatedly without running into cost issues. If you use a paid API key with any of the above providers, normal usage charges from that provider will apply.

## 4. Repository Structure

```
GMC_Extractor_new-master/
├── main.py                        # Entry point, run this file to process PDFs
├── requirements.txt                # Python dependencies
├── .env.example                    # Example environment file, copy this to .env
├── app/
│   ├── pipeline.py                 # Ties together loading, extraction, validation, saving
│   ├── extraction/
│   │   ├── pdf_loader.py           # Reads PDF text and tables using pdfplumber
│   │   ├── ocr.py                  # OCR fallback for scanned pages
│   │   └── llm_extractor.py        # Both LLM passes (evidence notes + field extraction)
│   ├── schemas/
│   │   └── policy_schema.py        # Pydantic models describing the final JSON shape
│   ├── tools/                      # Field-group definitions (schema sent to the LLM)
│   │   ├── fields.py
│   │   ├── insurer_info_tool.py
│   │   ├── policy_structure_tool.py
│   │   ├── room_rent_tool.py
│   │   ├── waiting_periods_tool.py
│   │   ├── maternity_tool.py
│   │   ├── other_benefits_tool.py
│   │   └── infertility_buffer_tool.py
│   └── validation/
│       └── validator.py            # Validates LLM output against the Pydantic models
├── data/
│   └── sample_policies/            # Sample GMC policy PDFs used to test this project
├── outputs/                         # Generated JSON output for each sample PDF
└── debug_logs/                      # Saved raw LLM responses, only created when something needs debugging
```

## 5. Setup Instructions

**Requirements**

- Python 3.10 or newer
- Tesseract OCR installed on your system (needed only for scanned/image PDFs)
  - On Windows: download and install from the [Tesseract GitHub releases page](https://github.com/UB-Mannheim/tesseract/wiki)
  - On Mac: `brew install tesseract`
  - On Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
- An API key from at least one of the supported LLM providers (gemini's free tier is enough to run this project)

**Installation**

1. Clone this repository and move into the project folder.

```bash
git clone https://github.com/shashi0011/GMC_info_extractor
cd GMC_Extractor_new-master
```

2. (Recommended) Create and activate a virtual environment.

```bash
python -m venv venv
source venv/bin/activate      # on Windows use: venv\Scripts\activate
```

3. Install the Python dependencies.

```bash
pip install -r requirements.txt
```

4. Copy the example environment file and fill in your API key.

```bash
cp .env.example .env
```

Open `.env` in a text editor and set at least these two lines (example using gemini):

```
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
```

You only need to fill in the key for whichever one provider you choose to use. The model name fields (for example `GEMINI_MODEL_NAME`) are optional, a sensible default model is used automatically if left blank.

## 6. How to Run the Project

To process every PDF inside `data/sample_policies/` in one go, simply run:

```bash
python main.py
```

This will loop through every PDF in that folder and save one JSON file per PDF inside the `outputs/` folder, using the same file name as the input PDF.

To process a single specific PDF instead, pass the file path as an argument:

```bash
python main.py "data/sample_policies/GHI Policy.pdf"
```

While it runs, the script prints progress to the terminal so you can follow along, for example which file is being processed, whether the evidence-notes step succeeded, and where the final output was saved.

## 7. Explanation of the Extraction Methodology

The core idea behind the methodology is to treat the LLM as the "reader" instead of writing rules for every possible insurer format. But an LLM left completely free tends to guess or fill in "typical" insurance values when it is not sure, which is not acceptable for this kind of factual extraction task. To reduce that risk, the following safeguards were built into the prompt sent to the LLM:

- The model is told to only use information that is actually written in the document, never to guess or assume typical/average industry values.
- Every extracted field carries a `status` of either `found` or `not_found`, so it is always clear whether an answer came from the document or was simply unavailable in it.
- A clear rule distinguishes "the document never talks about this benefit at all" (`not_found`) from "the document explicitly says this benefit is excluded / not covered" (`found`, with a value like "Excluded"). These are two different real-world situations, and the prompt gives worked examples of both so the model does not confuse them.
- Where a document gives one general rule (for example, a standard room rent percentage) and also gives a policy-specific exception or endorsement that overrides it, the model is told to report the specific override, not the general default.
- The model is told not to invent a metro/non-metro or similar split if the document only gives one combined number, and to instead say clearly that the document does not differentiate.
- Wherever the source page of a value can be identified (using `[PAGE X]` markers added while loading the PDF), that page number is captured and stored alongside the value, so any answer in the final JSON can be traced back to where it came from in the original PDF.

The extraction itself happens in two LLM passes to keep answers accurate and to manage the size of the document text sent to the model. Pass 1 reads the whole document once and produces topic-wise condensed notes (with page numbers preserved). Pass 2 then extracts the actual structured fields, normally from those condensed notes since they are shorter and already organised by topic. There is also a "split mode" (`EXTRACTION_MODE=split` in `.env`) which sends each group of related fields (for example, room rent and waiting periods together, maternity separately, and so on) to the LLM in its own smaller call instead of one large combined call. This is useful for a document that is unusually dense, since smaller, focused prompts tend to get more careful answers, at the cost of needing more LLM calls overall. By default the project runs in the faster single combined call mode.

## 8. JSON Schema and Mapping Logic

Every generated JSON file follows the same top-level shape, defined in `app/schemas/policy_schema.py` using Pydantic. The main sections are:

- `source_file` – the original PDF file name
- `insurer` – insurer name, TPA name, and whether this is confirmed to be a GMC/group health policy
- `previous_policy` – inception date, renewal date, policy tenure, previous year's premium
- `policy_structure` – family structure (for example Self + Spouse + Children) and the list of Sum Insured tiers
- `demographics` – count of employees, spouses, children, parents, and total lives covered
- `room_rent_hospitalization` – room rent percentage/limit, ICU percentage/limit, pre and post hospitalization days
- `maternity` – waiting period, baby day-one cover, vaccination, normal delivery and C-section limits (metro/non-metro)
- `waiting_periods` – 30-day initial wait, 1st/2nd year wait, pre-existing disease wait
- `other_benefits` – day care, OPD, teleconsultation, pharmacy discount, domiciliary hospitalization, health check-up, modern/bariatric/psychiatric/AYUSH treatment, LGBTQ+ coverage, live-in partner coverage, organ donor expenses
- `infertility_ambulance` – infertility treatment, surrogacy, ambulance and air ambulance charges
- `buffer_waiver` – corporate buffer limit, disease-wise capping, waiver conditions
- `extraction_summary` – a small summary object with counts of how many fields were found versus not found for that document

With the exception of `sum_insured_tiers` (which is a plain list of strings, since a policy can have any number of Sum Insured tiers) and `extraction_summary`, almost every individual data point in the JSON follows the same small repeating object shape:

```json
{
  "status": "found",
  "value": "the extracted value as text",
  "source_page": 12
}
```

or, when the document does not mention that field at all:

```json
{
  "status": "not_found",
  "value": null,
  "source_page": null
}
```

This one consistent shape was chosen deliberately so that any downstream system (like an internal QMS) can loop over the JSON the same way for every field, without needing to write separate parsing logic for each of the roughly 40 data points being extracted.

## 9. Assumptions Made

- The sample PDFs provided with the assignment are genuine GMC / group health policy documents, and the field list requested in the assignment (room rent, waiting periods, maternity, and so on) is assumed to be the complete set of information needed for the internal QMS system.
- Where a document gives a range or multiple values for the same field, the value is reported as text in a human-readable way (for example "1% of Sum Insured, subject to a maximum of Rs. 5,000 per day") rather than being force-split into separate numeric fields, since insurance wording is often not clean enough to safely split without changing its meaning.
- All values are extracted as text (strings), including numbers and percentages, since insurance limits are frequently written with extra conditions attached to them (for example "up to 2% of SI or actuals, whichever is lower") that would lose meaning if converted to a plain number.
- If more than one LLM provider key is present in `.env` at the same time, only the provider named in `LLM_PROVIDER` is actually used, the rest are ignored for that run.
- OCR is only triggered for pages where very little text could be extracted directly, on the assumption that this reliably identifies scanned or image-only pages without needing OCR on every page (which would be much slower).

## 10. Known Limitations

- Extraction quality depends on the LLM model being used. Smaller or free-tier models can occasionally miss a value that a larger model would catch, especially when the relevant text is spread across a table and a footnote in different parts of the document.
- The system currently has no automatic fallback if the chosen LLM provider fails or the response is unusable even after one repair retry, that document is simply skipped with an error message rather than being retried with a different provider.
- Free-tier LLM providers (for example Gemini) apply a request-per-minute or token-per-minute limit, so processing many large PDFs back-to-back can occasionally need a short wait between calls. This is handled with a basic retry-and-wait mechanism, but a very large batch of documents may still take a while to fully process.
- OCR accuracy for scanned pages depends on the scan quality of the original PDF. A low quality or skewed scan can still produce imperfect OCR text, which can affect that page's extraction.
- This is a working prototype built to demonstrate the extraction approach, and it has not been hardened for production use (for example, there is no queue system, no retry across providers, and no persistent database, all of which a production deployment would likely need).

## 11. Sample Output

The `outputs/` folder in this repository already contains the generated JSON output for every sample PDF provided with the assignment, produced by actually running `python main.py` against the `data/sample_policies/` folder. No output file in that folder was hand-written or manually edited, every value there came directly from this pipeline.

## 12. Future Improvements

- Add an automatic fallback to a second LLM provider if the primary provider's daily quota is reached.
- Add a lightweight confidence score per field, based on things like how directly the evidence notes supported the value.
- Build a simple web interface to upload a PDF and view the extracted JSON side by side with the original document, instead of only running from the command line.
- Add an automated evaluation script that compares the generated JSON output against a small manually verified answer set, to track extraction accuracy over time as prompts or models change.
