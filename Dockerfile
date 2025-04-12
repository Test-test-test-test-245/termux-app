FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    TERM=xterm-256color \
    LANG=en_US.UTF-8 \
    SHELL=/bin/bash

# Create and set working directory
WORKDIR /app

# Install system dependencies including terminal-based editors and tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    procps \
    libffi-dev \
    git \
    curl \
    wget \
    htop \
    # Terminal editors
    vim \
    nano \
    emacs-nox \
    joe \
    # Terminal multiplexers
    tmux \
    screen \
    # Development tools
    sqlite3 \
    zip \
    unzip \
    tar \
    jq \
    openssh-client \
    rsync \
    # Python base requirements
    python3-dev \
    python3-pip \
    python3-venv \
    python3-wheel \
    # Node.js and npm
    nodejs \
    npm \
    # C/C++ development (needed for building some Python packages)
    gcc \
    g++ \
    make \
    # Libraries commonly needed for building Python packages
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libncurses5-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    locales \
    # Cleanup
    && rm -rf /var/lib/apt/lists/* \
    # Generate locales
    && sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen

# Set the locale
RUN update-locale LANG=en_US.UTF-8

# Upgrade pip but don't pre-install packages - let users install what they need
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Python dependencies for the web service only
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directories for user storage
RUN mkdir -p /app/storage/users

# Copy application code
COPY . .

# Set up entry point - using gevent for Python 3.11 compatibility
# Use wsgi.py to avoid name conflict with app directory
CMD gunicorn --worker-class gevent -w 1 -b 0.0.0.0:$PORT wsgi:app
