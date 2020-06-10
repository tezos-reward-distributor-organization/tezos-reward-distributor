FROM python:3

COPY requirements.txt /app/
WORKDIR /app
RUN pip install -r requirements.txt

COPY / /app
COPY tezos-config-docker /root/.tezos-client/config
RUN mkdir -p /trd/config
RUN mkdir -p /trd/reports

VOLUME ["/trd/config", "/trd/reports", "/tezos-client", "/trd/tezos"]

ENTRYPOINT [ "python", "src/main.py", "-f","/trd/config", "-r","/trd/reports", "-E","/"]