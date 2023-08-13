ARG app_env

FROM python:3.11.4-bullseye as base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1

WORKDIR /app

FROM base as dev-setup
RUN apt-get update && apt-get install -y git less vim

FROM base as prod-setup

FROM ${app_env}-setup as shared-setup
ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# libgdal-dev required to build geopandas
RUN apt-get update && apt-get install -y build-essential libgdal-dev
RUN useradd -ms /bin/bash joyvan
USER joyvan
ENV PATH="/home/joyvan/.local/bin:${PATH}"
RUN pip install poetry
COPY . .

FROM shared-setup as dev
RUN make install-dev

FROM shared-setup as prod
RUN make install

CMD ["make", "run", "--always-make"]
