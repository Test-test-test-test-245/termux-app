FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

# Create and set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    procps \
    libffi-dev \
    git \
    curl \
    wget \
    vim \
    nano \
    sqlite3 \
    # Python development packages
    python3-dev \
    python3-pip \
    python3-venv \
    python3-wheel \
    # C/C++ development
    gcc \
    g++ \
    make \
    # Libraries commonly needed for Python packages
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libncurses5-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Install common Python packages
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir \
    numpy \
    pandas \
    matplotlib \
    scikit-learn \
    requests \
    beautifulsoup4 \
    flask \
    django \
    jupyterlab \
    pytest

# Install Python dependencies for the web service
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a volume for persistent storage
VOLUME /app/storage

# Copy application code
COPY . .

# Create a directory for user files
RUN mkdir -p /app/storage/user_files && \
    chmod 777 /app/storage/user_files

# Set up entry point
CMD gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:$PORT app:app