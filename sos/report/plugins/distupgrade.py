# Copyright (C) 2014 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class DistUpgrade(Plugin):
    """ Distribution upgrade data """

    plugin_name = "distupgrade"
    profiles = ('system', 'sysmgmt')

    files = None


class RedHatDistUpgrade(DistUpgrade, RedHatPlugin):

    packages = (
        'preupgrade-assistant',
        'preupgrade-assistant-ui',
        'preupgrade-assistant-el6toel7',
        'redhat-upgrade-tool'
    )

    files = (
        "/var/log/upgrade.log",
        "/var/log/redhat_update_tool.log",
        "/root/preupgrade/all-xccdf*",
        "/root/preupgrade/kickstart"
    )

    def postproc(self):
        self.do_file_sub(
            "/root/preupgrade/kickstart/anaconda-ks.cfg",
            r"(useradd --password) (.*)",
            r"\1 ********"
        )

        self.do_file_sub(
            "/root/preupgrade/kickstart/anaconda-ks.cfg",
            r"(\s*rootpw\s*).*",
            r"\1********"
        )

        self.do_file_sub(
            "/root/preupgrade/kickstart/untrackeduser",
            r"\/home\/.*",
            r"/home/******** path redacted ********"
        )

# vim: set et ts=4 sw=4 :
