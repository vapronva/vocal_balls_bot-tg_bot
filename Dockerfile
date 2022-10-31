FROM python:3.11-alpine

WORKDIR /usr/src/app

USER 1054

COPY requirements.txt ./

RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python3", "./main.py" ]
