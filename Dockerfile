FROM python:3.12.9-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get -y update
RUN add-apt-repository ppa:zhangsongcui3371/fastfetch
RUN apt-get -y install git fastfetch

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -U -r requirements.txt

COPY . .

ENTRYPOINT [ "python3", ".", "--production"]