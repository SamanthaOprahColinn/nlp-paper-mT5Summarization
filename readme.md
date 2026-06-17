# mT5 Single Scientific Paper Document Summarization

## Setup Project

## 1. Install Dependency

```bash
pip install -r requirements.txt
```

---

## 2. Download Model

Download model fine-tuning dari Google Drive berikut:

[https://drive.google.com/file/d/1pLW2-wZkdxxVYbDMBXjL-ZoehXiwIAyr/view?usp=sharing]

atau 

copy dari folder checkpoint-522 folder summarization-mt5 jika download folder keseluruhan (training, model, backend) 

---

## 2b. Extract Model (jika download zip)

1. Extract file ZIP hasil download

2. Letakkan folder `model` di root project

Struktur akhirnya:

```txt
project/
│
├── app.py
├── model/
│   ├── config.json
│   ├── pytorch_model.bin
│   ├── tokenizer.json
│   └── ...
│
├── uploads/
├── requirements.txt
└── README.md
```

---

## 3. Jalankan Backend

Run server menggunakan:

```bash
python -m uvicorn app:app --reload
```

Jika berhasil:

```txt
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

## 4. Swagger Documentation

Buka browser:

```txt
http://127.0.0.1:8000/docs
```

