FROM python:3.8

RUN mkdir /app

COPY . /app

WORKDIR /app

RUN pip install -r /app/requirements.txt

CMD python3 tidconsole.py