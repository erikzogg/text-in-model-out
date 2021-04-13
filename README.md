# Source Code of My Bachelor Thesis

## Prerequisites

* Docker >= 20.10.5
* docker-compose >= 1.28.6

## Supported Browsers

* Google Chrome >= 89
* Microsoft Edge >= 89
* Mozilla Firefox >= 87

## Setup

### With Docker (recommended)

```
docker-compose build
docker-compose up -d
```

### Without Docker

```
pip install --no-cache-dir -r requirements.txt
python -m spacy download en_core_web_trf
python manage.py runserver
```
