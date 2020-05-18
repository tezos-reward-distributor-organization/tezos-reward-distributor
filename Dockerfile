FROM python:3

COPY requirements.txt /app/
WORKDIR /app
RUN pip install -r requirements.txt

COPY / /app

RUN mkdir -p /trd/config
RUN mkdir -p /trd/reports

VOLUME ["/trd/config", "/trd/reports", "/tezos-client", "/root/.tezos-client"]

ENTRYPOINT [ "python", "src/main.py", "-f","/trd/config", "-r","/trd/reports", "-E","/"]