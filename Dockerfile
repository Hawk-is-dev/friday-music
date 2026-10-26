FROM nikolaik/python-nodejs:python3.13-nodejs22

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ffmpeg \
       libgl1 \
       libglib2.0-0 \
       git \
       gcc \
       python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip3 install --no-cache-dir --upgrade pip \
    && pip3 install --no-cache-dir --upgrade -r requirements.txt

CMD bash scripts/start
