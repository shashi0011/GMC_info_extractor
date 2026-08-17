import os
import sys
from dotenv import load_dotenv

load_dotenv()
from app.pipeline import process_pdf

data = "data/sample_policies"


def process_one_pdf(path: str):
    source_file = os.path.basename(path)
    print("\n" + "=" * 60)
    print(f"Processing: {source_file}")
    print("=" * 60)

    output_path = process_pdf(path, source_file)
    print(f"Done. Output saved at: {output_path}")


def main():
    provider = os.environ.get("LLM_PROVIDER", "groq").lower()
    key_needed_map = {
        "groq": "GROQ_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "openrouter":"OPENROUTER_API_KEY",
        "cerebras":"CEREBRAS_API_KEY",
    }
    key_needed = key_needed_map.get(provider)
    if not os.environ.get(key_needed):
        print(f"ERROR: {key_needed} is not set. Add it to a .env file.")
        sys.exit(1)

    if len(sys.argv) > 1:
        process_one_pdf(sys.argv[1])
    else:
        pdf_files = [f for f in os.listdir(data) if f.lower().endswith(".pdf")]
        if not pdf_files:
            print(f"No PDF files found in {data}")
            return

        for pdf_file in pdf_files:
            full_path = os.path.join(data, pdf_file)
            process_one_pdf(full_path)


if __name__ == "__main__":
    main()
