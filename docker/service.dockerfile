ARG app_env

FROM python:3.12.0-bullseye as base

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

# add makedeb prebuilt MPR repo (required for just)
RUN wget -qO - 'https://proget.makedeb.org/debian-feeds/prebuilt-mpr.pub' | \
    gpg --dearmor | \
    tee /usr/share/keyrings/prebuilt-mpr-archive-keyring.gpg 1> /dev/null

RUN echo "deb [arch=all,$(dpkg --print-architecture) signed-by=/usr/share/keyrings/prebuilt-mpr-archive-keyring.gpg] https://proget.makedeb.org prebuilt-mpr bullseye" | \
    tee /etc/apt/sources.list.d/prebuilt-mpr.list

# libgdal-dev required to build geopandas
RUN apt-get update && apt-get install -y just build-essential libgdal-dev
RUN useradd -ms /bin/bash joyvan
USER joyvan
ENV PATH="/home/joyvan/.local/bin:${PATH}"
RUN pip install poetry
COPY . .

FROM shared-setup as dev
RUN just install-dev

FROM shared-setup as prod
RUN just install

CMD ["just", "run"]
