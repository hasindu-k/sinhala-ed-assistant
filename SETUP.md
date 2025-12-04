# FastAPI API Setup Guide

Follow these steps to set up and run the Sinhala ED API locally.

---

## 1. Prerequisites

- Python 3.8+
- pip

Example (Debian/Ubuntu):

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential
```

## 2. Create and activate a virtual environment

```bash
# Create venv next to pyproject.toml
python3 -m venv .venv

# Activate (Linux/macOS)
source .venv/bin/activate

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate (Windows cmd)
.venv\Scripts\activate
```

## 3. Upgrade pip and packaging helpers

```bash
python -m pip install --upgrade pip setuptools wheel
```

## 4. Install the project and dependencies

Install the project (reads pyproject.toml):

```bash
python -m pip install .
# for editable install during development:
python -m pip install -e .
```

If you need to install dependencies manually:

```bash
python -m pip install \
  "fastapi" "uvicorn[standard]" "pydantic" "python-multipart" \
  "torch" "transformers" "sentence-transformers" "onnxruntime" \
  "faiss-cpu" "qdrant-client" "opencv-python" "pytesseract" \
  "scikit-learn" "pandas" "indic-nlp-library" "python-dotenv" "psycopg[binary]"
```

## 5. Run the API

```bash
uvicorn app.main:app --reload --port 8000
```

The API is available at http://localhost:8000 and interactive docs at http://localhost:8000/docs

---

## Quick re-activation (later)

Each time you open a new shell, activate the venv:

```bash
source .venv/bin/activate
```
