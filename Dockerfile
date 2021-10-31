FROM python:3.9

RUN curl -fsSL https://deb.nodesource.com/setup_17.x | bash - \
    && apt-get install -y nodejs \
    && node -v && npm -v

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install -U pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_trf
