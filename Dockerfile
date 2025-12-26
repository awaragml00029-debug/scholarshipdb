FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    ca-certificates \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt* ./

# Install Python dependencies
RUN pip install --no-cache-dir \
    playwright \
    beautifulsoup4 \
    lxml \
    loguru \
    pydantic \
    pydantic-settings \
    sqlalchemy \
    python-dotenv \
    pyyaml \
    gspread \
    oauth2client

# Install Playwright and browsers
RUN playwright install chromium && \
    playwright install-deps chromium

# Copy application code
COPY . .

# Create data directory for outputs
RUN mkdir -p data docs/data

# Set git config for commits
RUN git config --global user.email "scholarship-bot@example.com" && \
    git config --global user.name "Scholarship Bot"

# Make scripts executable
RUN chmod +x *.sh 2>/dev/null || true

# Entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Health check
HEALTHCHECK --interval=1h --timeout=30s --start-period=5s --retries=3 \
    CMD test -f data/all_scholarships.json || exit 1

# Use entrypoint for scheduled runs
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Default command (can be overridden)
CMD []
