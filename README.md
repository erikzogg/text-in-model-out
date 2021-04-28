# Source Code of My Bachelor Thesis

## Prerequisites

* Docker >= 20.10.6
* docker-compose >= 1.29.1

## Supported Browsers

* Google Chrome >= 90
* Microsoft Edge >= 90
* Mozilla Firefox >= 89

## Setup

### With Docker (recommended)

```
docker-compose build
docker-compose up -d
docker-compose run django npm install
```

### Without Docker

```
pip install --no-cache-dir -r requirements.txt
python -m spacy download en_core_web_trf
python manage.py runserver
npm install
```
