# Use a pre-configured PyTorch base image with CUDA 12.1 runtime support
FROM pytorch/pytorch:2.2.2-cuda12.1-cudnn8-runtime

# Set system parameters
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies required by OpenCV and PaddleOCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    git \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies list and install python packages
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the backend source code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Start Uvicorn API server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
