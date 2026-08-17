import pytesseract
from PIL import Image
import io

def ocr_page_image(page) -> str:
    try:
        page_img = page.to_image(resolution=200)
        img_byt = io.BytesIO()
        page_img.original.save(img_byt, format="PNG")
        img_byt.seek(0)
        pil_image = Image.open(img_byt)
        text = pytesseract.image_to_string(pil_image)
        return text
    except Exception as error:
        print(f"OCR failed for a page: {error}")
        return ""
