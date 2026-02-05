FROM python:3.12-slim

# Our source files will live in /app
WORKDIR /app

# Install necessary python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all our code into the container on build.
COPY src/ src/
COPY notebooks/ notebooks/

# Default command run when the container starts and nothing else specified.
# we'll probably update this as we develop to make it easy for review.
CMD ["python", "src/main.py"]
