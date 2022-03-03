How to run TRD in Docker
========================

It is possible to run TRD within Docker.

You will need a pre-existing configuration file. It is recommended to run `configure.py` script outside of docker, then put the configuration yaml file in the `cfg` folder mounted in the container.

The following mount points are expected:

  * `pymnt` folder containing the overall folder structure
  * `pymnt/cfg` folder for the configuration file created before

Access to a signer endpoint and node endpoint are assumed in the host network.

Here are the steps:

1. Build the Docker container:

  ::

    docker build -t trdo/tezos-reward-distributor .

2. Alternatively, you can pull directly the official tezos-reward-distributor Docker image:

  ::

    docker pull trdo/tezos-reward-distributor

3. Run the container:

  ::

      docker run --network=host -v $(pwd)/pymnt:/app/pymnt:z trdo/tezos-reward-distributor --base_directory /app/pymnt <ARGS>

<ARGS> are the other arguments that you would normally pass to the TRD program.

In a microservice environment, omit `--network=host`, instead, specify the signer service using the `--signer_endpoint` and the Tezos node service using the `--node_endpoint` arguments to TRD.
