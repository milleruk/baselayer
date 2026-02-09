FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev build-essential netcat-openbsd \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --upgrade pip setuptools wheel \
    && pip install --upgrade --force-reinstall -r requirements.txt

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:6993"]
