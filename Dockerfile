FROM python:3.10

RUN curl -fsSL https://deb.nodesource.com/setup_17.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest \
    && node -v && npm -v

WORKDIR /usr/src/app

RUN pip install -U pip setuptools wheel spacy lemminflect Django gunicorn
RUN python -m spacy download en_core_web_trf
