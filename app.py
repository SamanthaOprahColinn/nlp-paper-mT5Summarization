import os
import re
import fitz
import torch

from docx import Document
from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File, HTTPException

from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM
)


load_dotenv()

MODEL_PATH = os.getenv("MODEL_PATH")


device = "cuda" if torch.cuda.is_available() else "cpu"

print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

print("Loading model...")
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH)

model.to(device)

print(f"Model loaded on {device}")


app = FastAPI()


def extract_pdf(file_path):

    doc = fitz.open(file_path)

    text = ""

    for page in doc:
        text += page.get_text()

    return text


def extract_document(file_path):

    extension = os.path.splitext(file_path)[1]

    if extension == ".pdf":
        return extract_pdf(file_path)

    # elif extension == ".txt":
    #     return extract_txt(file_path)

    # elif extension == ".docx":
    #     return extract_docx(file_path)

    else:
        raise Exception("Unsupported file")


def clean_text(text: str) -> str:
    import re

    text = text.lower()

    # hapus special tokens
    text = re.sub(r"</s>", " ", text)
    text = re.sub(r"<s>", " ", text)
    text = re.sub(r"<extra_id_\d+>", " ", text)

    # hapus karakter aneh
    text = re.sub(r'[^a-z0-9\s.,;:%()-]', ' ', text)

    # rapikan spasi
    text = re.sub(r'\s+', ' ', text)

    return text.strip()

SECTION_PATTERNS = {
    "abstrak": [
        r"\b\d+\.\s*abstrak\b",
        r"\babstrak\b"
    ],

    "pendahuluan": [
        r'\b\d+\.\s*pendahuluan',
        r'\bi\.\s*pendahuluan',
        r'\bpendahuluan\b'
    ],

    "metodologi": [
        r'\b\d+\.\s*metode penelitian',
        r'\bmetode penelitian\b',
        r'\bmetodologi\b',
        r'\bmetode\b',
        r'\bpengumpulan data\b',
        r'\bdeskripsi obyek survei\b'
    ],

    "hasil_pembahasan": [
        r'\b\d+\.\s*hasil dan pembahasan',
        r'\bhasil dan pembahasan\b',
        r'\bhasil survei\b',
        r'\bhasil\b'
    ],

    "kesimpulan": [
        r'\b\d+\.\s*kesimpulan dan saran',
        r'\bkesimpulan dan saran\b',
        r'\bkesimpulan\b',
        r'\bpenutup\b'
    ]
}


def find_sections(text):

    lower_text = text.lower()

    positions = []

    for section_name, patterns in SECTION_PATTERNS.items():

        for pattern in patterns:

            match = re.search(pattern, lower_text)

            if match:

                positions.append({
                    "section": section_name,
                    "start": match.start()
                })

                break

    positions = sorted(
        positions,
        key=lambda x: x["start"]
    )

    sections = {}

    for i in range(len(positions)):

        current = positions[i]

        start = current["start"]

        if i < len(positions) - 1:
            end = positions[i + 1]["start"]
        else:
            end = len(text)

        section_text = text[start:end]

        sections[current["section"]] = section_text

    return sections

def chunk_text(text, max_tokens=800):

    sentences = text.split(". ")

    chunks = []

    current_chunk = ""

    for sentence in sentences:

        temp = current_chunk + sentence

        tokens = tokenizer.encode(temp)

        if len(tokens) < max_tokens:

            current_chunk += sentence + ". "

        else:

            chunks.append(current_chunk)

            current_chunk = sentence + ". "

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

def summarize_text(text):

    chunks = chunk_text(text)

    summaries = []

    for chunk in chunks:

        inputs = tokenizer(
            chunk,
            return_tensors="pt",
            truncation=True,
            max_length=1024
        ).to(device)

        with torch.no_grad():

            summary_ids = model.generate(
                **inputs,
                max_length=256,
                min_length=64,
                num_beams=4,
                no_repeat_ngram_size=3,
                early_stopping=True
            )

        summary = tokenizer.decode(
            summary_ids[0],
            skip_special_tokens=True
        )

        summaries.append(summary)

    final_summary = " ".join(summaries)

    # summarize ulang kalau chunk lebih dari 1
    if len(summaries) > 1:

        inputs = tokenizer(
            final_summary,
            return_tensors="pt",
            truncation=True,
            max_length=1024
        ).to(device)

        with torch.no_grad():

            summary_ids = model.generate(
                **inputs,
                max_length=256,
                min_length=64,
                num_beams=4
            )

        final_summary = tokenizer.decode(
            summary_ids[0],
            skip_special_tokens=True
        )

    return final_summary


@app.get("/")
def root():

    return {
        "message": "Summarization API Running"
    }


@app.post("/summarize")
async def summarize(
    file: UploadFile = File(...)
):

    allowed = [".pdf", ".txt", ".docx"]

    extension = os.path.splitext(file.filename)[1]

    if extension.lower() not in allowed:

        raise HTTPException(
            status_code=400,
            detail="Unsupported file"
        )

    # save file
    save_path = f"uploads/{file.filename}"

    with open(save_path, "wb") as buffer:
        buffer.write(await file.read())

    # extract text
    text = extract_document(save_path)

    # clean
    text = clean_text(text)

    # section extraction
    sections = find_sections(text)

    results = {}

    for section_name, section_text in sections.items():

        summary = summarize_text(section_text)

        results[section_name] = {
            "original_text": section_text,
            "summary": summary,
            "original_length": len(section_text),
            "summary_length": len(summary)
        }

    return {
        "status": "success",
        "document_title": file.filename,
        "sections": results
    }