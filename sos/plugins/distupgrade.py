# Copyright (C) 2014 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

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
