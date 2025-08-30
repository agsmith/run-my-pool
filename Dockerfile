FROM --platform=linux/amd64 python:3.11-slim

WORKDIR /workspace
COPY requirements.txt /workspace/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /workspace
ENV PYTHONPATH=/workspace

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]