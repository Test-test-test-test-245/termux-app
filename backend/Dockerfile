FROM python:3.9-slim

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

# Create a volume for persistent storage
VOLUME /app/storage

# Copy application code
COPY . .

# Create directories for user files and customize configuration
RUN mkdir -p /app/storage/user_files && \
    chmod 777 /app/storage/user_files && \
    mkdir -p /app/storage/home && \
    mkdir -p /app/storage/home/bin

# Create a custom .bashrc with developer-friendly defaults
RUN echo '# Terminal configuration' > /app/storage/home/.bashrc && \
    echo 'export PS1="\\[\\033[01;32m\\]\\u@termux-web\\[\\033[00m\\]:\\[\\033[01;34m\\]\\w\\[\\033[00m\\]\\$ "' >> /app/storage/home/.bashrc && \
    echo '' >> /app/storage/home/.bashrc && \
    echo '# Environment variables' >> /app/storage/home/.bashrc && \
    echo 'export EDITOR=nano' >> /app/storage/home/.bashrc && \
    echo 'export VISUAL=nano' >> /app/storage/home/.bashrc && \
    echo 'export LANG=en_US.UTF-8' >> /app/storage/home/.bashrc && \
    echo 'export LC_ALL=en_US.UTF-8' >> /app/storage/home/.bashrc && \
    echo 'export HISTSIZE=5000' >> /app/storage/home/.bashrc && \
    echo 'export HISTFILESIZE=10000' >> /app/storage/home/.bashrc && \
    echo 'export HISTCONTROL=ignoreboth:erasedups' >> /app/storage/home/.bashrc && \
    echo '' >> /app/storage/home/.bashrc && \
    echo '# Path configuration' >> /app/storage/home/.bashrc && \
    echo 'export PATH=$HOME/bin:$PATH:/app/storage/user_files' >> /app/storage/home/.bashrc && \
    echo '' >> /app/storage/home/.bashrc && \
    echo '# Aliases' >> /app/storage/home/.bashrc && \
    echo 'alias ll="ls -la"' >> /app/storage/home/.bashrc && \
    echo 'alias python=python3' >> /app/storage/home/.bashrc && \
    echo 'alias py=python3' >> /app/storage/home/.bashrc && \
    echo 'alias pip=pip3' >> /app/storage/home/.bashrc && \
    echo 'alias cls="clear"' >> /app/storage/home/.bashrc && \
    echo 'alias h="history"' >> /app/storage/home/.bashrc && \
    echo 'alias ..="cd .."' >> /app/storage/home/.bashrc && \
    echo 'alias ...="cd ../.."' >> /app/storage/home/.bashrc && \
    echo 'alias gst="git status"' >> /app/storage/home/.bashrc && \
    echo 'alias gl="git log --oneline"' >> /app/storage/home/.bashrc && \
    echo '' >> /app/storage/home/.bashrc && \
    echo '# Colors for ls command' >> /app/storage/home/.bashrc && \
    echo 'export LS_COLORS="di=1;34:ln=1;36:so=1;35:pi=1;33:ex=1;32:bd=1;33:cd=1;33:su=1;31:sg=1;31:tw=1;34:ow=1;34"' >> /app/storage/home/.bashrc && \
    echo 'alias ls="ls --color=auto"' >> /app/storage/home/.bashrc && \
    echo 'alias grep="grep --color=auto"' >> /app/storage/home/.bashrc && \
    echo '' >> /app/storage/home/.bashrc && \
    echo '# Welcome message' >> /app/storage/home/.bashrc && \
    echo 'echo "Welcome to Termux Web Terminal!"' >> /app/storage/home/.bashrc && \
    echo 'echo "• Edit files:  nano file.py, vim file.py, or emacs file.py"' >> /app/storage/home/.bashrc && \
    echo 'echo "• Run scripts: python file.py"' >> /app/storage/home/.bashrc && \
    echo 'echo "• Install packages: pip install <package_name>"' >> /app/storage/home/.bashrc && \
    echo 'echo "• Try tmux for multiple terminal sessions"' >> /app/storage/home/.bashrc && \
    echo 'echo ""' >> /app/storage/home/.bashrc && \
    chmod 755 /app/storage/home/.bashrc

# Create .vimrc configuration
RUN echo 'syntax on' > /app/storage/home/.vimrc && \
    echo 'set autoindent' >> /app/storage/home/.vimrc && \
    echo 'set expandtab' >> /app/storage/home/.vimrc && \
    echo 'set number' >> /app/storage/home/.vimrc && \
    echo 'set tabstop=4' >> /app/storage/home/.vimrc && \
    echo 'set shiftwidth=4' >> /app/storage/home/.vimrc && \
    echo 'set softtabstop=4' >> /app/storage/home/.vimrc && \
    echo 'set background=dark' >> /app/storage/home/.vimrc && \
    echo 'colorscheme default' >> /app/storage/home/.vimrc && \
    echo 'set ruler' >> /app/storage/home/.vimrc && \
    echo 'set showcmd' >> /app/storage/home/.vimrc && \
    echo 'set incsearch' >> /app/storage/home/.vimrc && \
    echo 'set hlsearch' >> /app/storage/home/.vimrc && \
    echo 'set showmatch' >> /app/storage/home/.vimrc && \
    echo 'filetype plugin indent on' >> /app/storage/home/.vimrc

# Create tmux configuration file
RUN echo 'set -g default-terminal "screen-256color"' > /app/storage/home/.tmux.conf && \
    echo 'set -g history-limit 10000' >> /app/storage/home/.tmux.conf && \
    echo 'set -g base-index 1' >> /app/storage/home/.tmux.conf && \
    echo 'setw -g pane-base-index 1' >> /app/storage/home/.tmux.conf && \
    echo 'set -g status-bg black' >> /app/storage/home/.tmux.conf && \
    echo 'set -g status-fg white' >> /app/storage/home/.tmux.conf

# Create /app/storage/home/.inputrc for better command line editing
RUN echo 'set completion-ignore-case on' > /app/storage/home/.inputrc && \
    echo 'set show-all-if-ambiguous on' >> /app/storage/home/.inputrc && \
    echo 'set mark-symlinked-directories on' >> /app/storage/home/.inputrc && \
    echo '"\e[A": history-search-backward' >> /app/storage/home/.inputrc && \
    echo '"\e[B": history-search-forward' >> /app/storage/home/.inputrc

# Set up entry point
CMD gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:$PORT app:app