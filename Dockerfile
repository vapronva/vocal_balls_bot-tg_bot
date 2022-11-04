FROM python:3.11-alpine

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN apk add build-base=0.5-r3 ffmpeg=5.0.1-r1 && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./main.py" ]
