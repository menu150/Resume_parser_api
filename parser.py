# parser.py
import fitz  # PyMuPDF
import spacy

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

def extract_text_from_pdf(contents: bytes) -> str:
    try:
        doc = fitz.open(stream=contents, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text.strip()
    except Exception as e:
        return f"Error parsing PDF: {e}"

def parse_resume_text(text: str) -> dict:
    doc = nlp(text)

    names = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
    orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
    skills = []  # spaCy doesn't have a built-in SKILL label

    return {
        "names": names[:3],
        "organizations": orgs[:3],
        "raw_text": text[:500] + "..." if len(text) > 500 else text
    }
