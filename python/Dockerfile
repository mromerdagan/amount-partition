FROM python:3.11-slim

# Prevent interactive prompts from tools like apt
ENV DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies (optional: tzdata, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the actual application
COPY . .

# Use non-root user for better security (create user, switch to it)
RUN useradd -m appuser
USER appuser

# Expose port (default 8000, can be overridden)
ARG PORT=8000
ENV PORT=${PORT}
EXPOSE ${PORT}

# Run the server, main.py should read PORT from env
CMD ["python", "main.py"]


