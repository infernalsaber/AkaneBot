FROM python:3.11-slim-buster

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt --no-cache-dir

COPY . .
RUN apt-get update

CMD ["python3", "-OO", "main.py"]