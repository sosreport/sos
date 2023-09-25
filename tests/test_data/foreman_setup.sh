#!/bin/bash

SUCCESS=0

if grep -iq centos /etc/os-release; then
    if  [[ `echo | awk "{print ($FOREMAN_VER >= 3.4)}"` -eq 1 ]]; then
        dnf -y install https://yum.puppet.com/puppet7-release-el-8.noarch.rpm
        dnf -y install https://yum.theforeman.org/releases/$FOREMAN_VER/el8/x86_64/foreman-release.rpm
        dnf -y module enable foreman:el8
    else
        dnf -y install https://yum.puppet.com/puppet6-release-el-8.noarch.rpm
        dnf -y install https://yum.theforeman.org/releases/$FOREMAN_VER/el8/x86_64/foreman-release.rpm
        dnf -y module enable ruby:2.7 postgresql:12 foreman:el8
    fi
    dnf -y install foreman-installer && SUCCESS=1
elif grep -iq debian /etc/os-release; then
    apt-get update
    apt-get -y install ca-certificates locales
    sed -i 's/^# *\(en_US.UTF-8\)/\1/' /etc/locale.gen
    locale-gen
    export LC_ALL=en_US.UTF-8
    export LANG=en_US.UTF-8
    curl https://apt.puppet.com/puppet7-release-bullseye.deb --output /root/puppet7-release-bullseye.deb
    apt-get install /root/puppet7-release-bullseye.deb
    curl https://deb.theforeman.org/foreman.asc --output /etc/apt/trusted.gpg.d/foreman.asc
    echo "deb http://deb.theforeman.org/ bullseye $FOREMAN_VER" | tee /etc/apt/sources.list.d/foreman.list
    echo "deb http://deb.theforeman.org/ plugins $FOREMAN_VER" | tee -a /etc/apt/sources.list.d/foreman.list
    apt-get update
    apt-get -y install foreman-installer && SUCCESS=1
fi

if [[ $SUCCESS == 1 ]]; then
    foreman-installer --foreman-db-password='S0Sdb=p@ssw0rd!' --foreman-initial-admin-password='S0S@dmin\\p@ssw0rd!'
else
    echo "Setup failed"
    exit 1
fi
