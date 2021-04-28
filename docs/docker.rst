How to run TRD in Docker
========================

It is possible to run TRD within Docker.

You will need a pre-existing configuration file. It is recommended to run `configure.py` script outside of docker, then put the configuration yaml file in a `config` folder mounted in the container.

The following mount points are expected:

  * `config` folder containing config file
  * `reports` folder containing payout reports

Access to a signer endpoint and node endpoint are assumed in the host network.

Here are the steps:

1. Build the docker container
  ::

    docker build -t trd .


2. Run the container:
  ::

      docker run --network=host -v $(pwd)/reports:/app/reports:z -v $(pwd)/config:/app/config:z trd --config_dir /app/config --reports_base /app/reports <ARGS>

<ARGS> are the other arguments that you would normally pass to the TRD program.

In a microservice environment, omit `--network=host`, instead, specify the signer service using the `--signer_endpoint` and the Tezos node service using the `--node_endpoint` arguments to TRD.
