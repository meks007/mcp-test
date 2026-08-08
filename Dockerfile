FROM python:3.11.15-slim

ARG REQUIREMENTS_FILE
ARG SERVER_FILE

WORKDIR /app

COPY ${REQUIREMENTS_FILE} /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY ${SERVER_FILE} /app/server.py

CMD ["python", "/app/server.py"]
