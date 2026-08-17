import pdfplumber
from app.extraction.ocr import ocr_page_image

min_char = 20

def load_pdf(path: str) -> dict:

    data = []
    text = []

    with pdfplumber.open(path) as pdf:
        pages = len(pdf.pages)

        for i, page in enumerate(pdf.pages):
            page_number = i + 1
            page_text = page.extract_text() or ""

            tables = page.extract_tables()
            table_text_lines = []
            for table in tables:
                for row in table:
                    clean_row = [str(cell).strip() if cell else "" for cell in row]
                    table_text_lines.append(" | ".join(clean_row))
            table_text = "\n".join(table_text_lines)

            if len(page_text.strip()) < min_char:
                ocr_text = ocr_page_image(page)
                page_text = ocr_text

            combined_page_text = page_text
            if table_text:
                combined_page_text += "\n\n[tables on thiis page]\n" + table_text

            data.append({
                "page_number": page_number,
                "text": combined_page_text,
                "tables": tables,
            })

            text.append(f"[PAGE {page_number}]\n{combined_page_text}")

    full_text = "\n\n".join(text)

    return {
        "full_text": full_text,
        "pages": data,
        "total_pages": pages,
    }
