# Dockerfile
FROM python:3.10-slim

# Upgrade pip and install dependencies
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app
COPY . .

# Expose port 8000 for FastAPI
EXPOSE 8000

# Note: For CI/CD, one could use GitHub Actions to build and push this Docker image.
# Update: This Dockerfile is minimal for the POC; CI/CD integration would be added in production.

# Run the FastAPI application with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
