# Text-In-Model-Out

Text-In-Model-Out creates a BPMN 2.0 process model from a textual process description.
This tool is part of my bachelor thesis at the Vienna University of Economics and Business.

## Prerequisites

* Docker >= 20.10.6
* docker-compose >= 1.29.2

## Supported Browsers

* Google Chrome >= 90
* Microsoft Edge >= 90
* Mozilla Firefox >= 89

## Setup

### With Docker (recommended)

```
docker-compose up -d
docker-compose run app npm install
```

### Without Docker

```
pip install --no-cache-dir -r requirements.txt
python -m spacy download en_core_web_trf
python manage.py runserver
npm install
```
