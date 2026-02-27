#!/bin/bash

SUCCESS=0

if grep -iq ubuntu /etc/os-release; then
    sudo snap install openstack --channel $SUNBEAM_VER
    sudo sunbeam prepare-node-script --bootstrap | sudo -i -u ubuntu bash -x
    sudo -i -u ubuntu -- sunbeam -v cluster bootstrap --accept-defaults && SUCCESS=1
fi

if [[ $SUCCESS != 1 ]]; then
    echo "Setup failed"
    exit 1
fi
