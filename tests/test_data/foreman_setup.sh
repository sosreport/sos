#!/bin/bash

SUCCESS=0
EXTRA_OPTS=""
puppet_ver=8

if grep -iq centos /etc/os-release; then
    os_version=$(grep VERSION_ID /etc/os-release | sed 's/VERSION_ID=\"\(.*\)\"/\1/')
    dnf -y install https://yum.puppet.com/puppet${puppet_ver}-release-el-${os_version}.noarch.rpm
    dnf -y install https://yum.theforeman.org/releases/$FOREMAN_VER/el${os_version}/x86_64/foreman-release.rpm
    dnf -y install https://yum.theforeman.org/katello/$KATELLO_VER/katello/el${os_version}/x86_64/katello-repos-latest.rpm
    dnf -y module enable foreman:el${os_version}
    dnf -y install foreman-installer-katello
    dnf -y install foreman-installer && SUCCESS=1
    EXTRA_OPTS="--scenario katello"
elif grep -iq debian /etc/os-release; then
    series=$(grep VERSION_CODENAME /etc/os-release | sed s/VERSION_CODENAME=//g)
    apt-get update
    apt-get -y install ca-certificates locales
    sed -i 's/^# *\(en_US.UTF-8\)/\1/' /etc/locale.gen
    locale-gen
    export LC_ALL=en_US.UTF-8
    export LANG=en_US.UTF-8
    curl https://apt.puppet.com/puppet${puppet_ver}-release-${series}.deb --output /root/puppet${puppet_ver}-release-${series}.deb
    apt-get install /root/puppet${puppet_ver}-release-${series}.deb
    sudo wget https://deb.theforeman.org/foreman.asc -O /etc/apt/trusted.gpg.d/foreman.asc
    echo "deb http://deb.theforeman.org/ ${series} $FOREMAN_VER" | tee /etc/apt/sources.list.d/foreman.list
    echo "deb http://deb.theforeman.org/ plugins $FOREMAN_VER" | tee -a /etc/apt/sources.list.d/foreman.list
    apt-get update
    apt-get -y install foreman-installer && SUCCESS=1
fi

if [[ $SUCCESS == 1 ]]; then
    foreman-installer --foreman-db-password='S0Sdb=p@ssw0rd!' --foreman-initial-admin-password='S0S@dmin\\p@ssw0rd!' ${EXTRA_OPTS}
else
    echo "Setup failed"
    exit 1
fi
