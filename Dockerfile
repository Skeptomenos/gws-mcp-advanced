# Use a specific version for reproducibility
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Default transport mode to stdio
    FASTMCP_TRANSPORT_MODE=stdio \
    # Create a non-root user
    APP_USER=mcpuser \
    APP_HOME=/app

# Create the application directory and user
RUN groupadd -r $APP_USER && \
    useradd -r -g $APP_USER -d $APP_HOME -s /sbin/nologin -c "Docker image user" $APP_USER && \
    mkdir -p $APP_HOME && \
    chown -R $APP_USER:$APP_USER $APP_HOME

WORKDIR $APP_HOME

# Install system dependencies (if any needed, e.g. for build)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management (optional but good practice)
# For now, we'll use pip with the existing pyproject.toml
COPY pyproject.toml .
# If you have uv.lock or requirements.txt, copy them here
COPY uv.lock .

# Install dependencies
# We install with --user or directly since we are in a container
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copy the rest of the application code
COPY . .

# Change ownership to the non-root user
RUN chown -R $APP_USER:$APP_USER $APP_HOME

# Switch to non-root user
USER $APP_USER

# Expose port if using SSE (Streamable HTTP) - default fastmcp port is often 8000
EXPOSE 8000

# Default command: run the main entrypoint
# This assumes 'google-workspace-mcp' is installed as a script or we run main.py
CMD ["python", "main.py"]
