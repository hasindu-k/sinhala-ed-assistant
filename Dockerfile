FROM python:3.12-slim

# 1. Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /code

# 2. Install System Dependencies
# Added 'gcc' and 'libpq-dev' to handle the database driver build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    tesseract-ocr \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 3. Cache Dependencies 
# Copy ONLY the file that defines dependencies first
COPY pyproject.toml .
COPY README.md . 

RUN pip install --upgrade pip && \
    pip install .

COPY . /code

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]