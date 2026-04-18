FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (needed for git and xhtml2pdf)
RUN apt-get update && apt-get install -y \
    git \
    libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set placeholder env for docker build
ENV PORTFOLIO_MODE=false
ENV MOCK_AI_MODE=true

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]