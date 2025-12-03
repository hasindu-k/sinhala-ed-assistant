# FastAPI API Setup Guide

Follow these steps to set up and run the **Sinhala ED API** locally:

---

## 1. Navigate to the API folder

```bash
cd api
```

## 2. Create and activate a virtual environment

```bash
# Create venv next to pyproject.toml
python3 -m venv .venv

# Activate (Linux/macOS)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate
```

## 3. Upgrade pip and helpers

```bash
python -m pip install -U pip setuptools wheel
```

## 4. Install dependencies

These match the packages declared in `pyproject.toml`.

```bash
pip install \
  "fastapi" "uvicorn[standard]" "pydantic" "python-multipart" \
  "torch" "transformers" "sentence-transformers" "onnxruntime" \
  "faiss-cpu" "qdrant-client" "opencv-python" "pytesseract" \
  "scikit-learn" "pandas" "indic-nlp-library" "python-dotenv" "psycopg[binary]"
```

## 5. Run the API

```bash
uvicorn app.main:app --reload --port 8000
```

The API should now be live at: [http://localhost:8000](http://localhost:8000)

---

## Quick re-activation (later)

Each time you open a new shell, activate the venv before running:

```bash
cd api && source .venv/bin/activate
```
