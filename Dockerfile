# Stage 1: Build the React Frontend
FROM node:20 AS frontend-builder
WORKDIR /app/frontend

# Copy frontend source
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

COPY frontend/ ./
# Build for production
RUN npm run build

# Stage 2: Setup Python Backend
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libsqlite3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install uvicorn

# Copy all source code
COPY . /app

# Overwrite frontend with built static files from Stage 1
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Expose Hugging Face default port (7860) or standard 8000
EXPOSE 7860

# Run FastAPI backend, which also serves the frontend
CMD ["python", "-m", "uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "7860"]
