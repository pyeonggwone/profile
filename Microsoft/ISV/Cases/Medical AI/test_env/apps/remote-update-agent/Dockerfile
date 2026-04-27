ARG PYTHON_BASE_IMAGE=python:3.11.14-bookworm
FROM ${PYTHON_BASE_IMAGE}

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8080

CMD ["python", "app.py"]