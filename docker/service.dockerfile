FROM python:3.10.4-bullseye as base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1

WORKDIR /app

FROM base as builder

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y build-essential git
RUN useradd -ms /bin/bash joyvan
USER joyvan
RUN pip install poetry
ENV PATH="/home/joyvan/.local/bin:${PATH}"
COPY . .
RUN poetry install

CMD ["./docker/bot-docker-entrypoint.sh"]