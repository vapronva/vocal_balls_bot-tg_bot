FROM python:3.11-alpine

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN apk add build-base=0.5-r3 && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

USER 1056

CMD [ "python", "./main.py" ]
