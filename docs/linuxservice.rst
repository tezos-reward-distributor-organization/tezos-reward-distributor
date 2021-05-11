Run as Linux Service (WIP)
============================

Alternatively, it is possible to add tezos-reward-distributer as a Linux service. It
can run in the background.

If docker is used, make sure user is in docker group

::

    sudo usermod -a -G docker $USER

In order to set up the service with default configuration arguments, run
the following command:

::

    sudo python3 service_add.py


**Note:**

If you do not want to use the default arguments, append any arguments
you wish to change after service_add.py. They will be appended to
main.py call. For example if you want to change configuration directory:

::

    sudo python3 service_add.py -f ~/payment/config/

It will create a service file and use it to enable the service.
Once enabled use following commands to start/stop the service.

::

    sudo systemctl start tezos-reward.service
    sudo systemctl stop tezos-reward.service

In order to see service status:

::

    systemctl status tezos-reward.service

In order to see logs:

::

    journalctl --follow --unit=tezos-reward.service