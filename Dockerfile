FROM python:3.13-slim-bookworm AS build

ENV PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN pip install --target=/app/dependencies -r requirements.txt

FROM build AS release

RUN useradd -m apprunner
USER apprunner

ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY --chown=apprunner: . /app

ENV PYTHONPATH="${PYTHONPATH}:/app/dependencies"

ARG PORT=8000
EXPOSE ${PORT}

CMD ["python", "main.py"]