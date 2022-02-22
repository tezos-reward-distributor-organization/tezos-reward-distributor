FROM python:3.10.1-alpine3.15

COPY . /app
# Create a unprivileged user
RUN addgroup trd \
    && adduser -G trd -D -h /app trd \
    && mkdir /app/config \
    && chown -R trd:trd /app

WORKDIR /app
USER trd
RUN pip install -r requirements.txt

ENTRYPOINT [ "python", "src/main.py" ]
