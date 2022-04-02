# Text-In-Model-Out

Text-In-Model-Out creates a BPMN 2.0 process model from a textual process description.
This tool is part of my bachelor thesis at the Vienna University of Economics and Business.

## Prerequisites

* Docker >= 20.10.13
* docker-compose >= 1.29.2

## Supported Browsers

* Google Chrome >= 100
* Microsoft Edge >= 100
* Mozilla Firefox >= 98

## Setup

### With Docker (recommended)

```
docker-compose up -d
docker-compose run --rm app npm install
```

### Without Docker

```
pip install --no-cache-dir -r requirements.txt
python manage.py runserver
npm install
```

### Initial Setup (not needed)

```
pip install -U pip setuptools wheel spacy lemminflect Django gunicorn
python -m spacy download en_core_web_trf
```