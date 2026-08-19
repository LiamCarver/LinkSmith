FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY schemas /app/schemas

RUN pip install --no-cache-dir /app

ENTRYPOINT ["python", "-m", "linksmith_services.obsidian_canvas_to_relationships"]
