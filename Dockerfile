FROM python:alpine

COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt

ENTRYPOINT [ "python", "src/main.py" ]
