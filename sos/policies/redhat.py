## Implement policies required for the sos system support tool

## Copyright (C) Steve Conklin <sconklin@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

# This enables the use of with syntax in python 2.5 (e.g. jython)
from __future__ import with_statement

import os
import sys

from sos.plugins import RedHatPlugin
from sos.policies import LinuxPolicy, PackageManager
from sos.utilities import shell_out

sys.path.insert(0, "/usr/share/rhn/")
try:
    from up2date_client import up2dateAuth
    from up2date_client import config
    from rhn import rpclib
except:
    # might fail if non-RHEL
    pass


class RHELPackageManager(PackageManager):

    def _get_rpm_list(self):
        pkg_list = shell_out(["rpm",
            "-qa",
            "--queryformat",
            "%{NAME}|%{VERSION}\\n"]).splitlines()
        self._rpms = {}
        for pkg in pkg_list:
            name, version = pkg.split("|")
            self._rpms[name] = {
                    'name': name,
                    'version': version
                    }

    def allPkgs(self):
        if not self._rpms:
            self._rpms = self._get_rpm_list()
        return self._rpms


class RHELPolicy(LinuxPolicy):

    def __init__(self):
        super(RHELPolicy, self).__init__()
        self.reportName = ""
        self.ticketNumber = ""
        self.package_manager = RHELPackageManager()
        self.valid_subclasses = [RedHatPlugin]

    @classmethod
    def check(self):
        "This method checks to see if we are running on RHEL. It returns True or False."
        return os.path.isfile('/etc/redhat-release') or os.path.isfile('/etc/fedora-release')

    def runlevelByService(self, name):
        from subprocess import Popen, PIPE
        ret = []
        p = Popen("LC_ALL=C /sbin/chkconfig --list %s" % name,
                  shell=True,
                  stdout=PIPE,
                  stderr=PIPE,
                  bufsize=-1)
        out, err = p.communicate()
        if err:
            return ret
        for tabs in out.split()[1:]:
            try:
                (runlevel, onoff) = tabs.split(":", 1)
            except:
                pass
            else:
                if onoff == "on":
                    ret.append(int(runlevel))
        return ret

    def rhelVersion(self):
        try:
            pkg = self.pkgByName("redhat-release") or \
            self.allPkgsByNameRegex("redhat-release-.*")[-1]
            pkgname = pkg["version"]
            if pkgname[0] == "4":
                return 4
            elif pkgname in [ "5Server", "5Client" ]:
                return 5
            elif pkgname[0] == "6":
                return 6
        except:
            pass
        return False

    def rhnUsername(self):
        try:
            cfg = config.initUp2dateConfig()

            return rpclib.xmlrpclib.loads(up2dateAuth.getSystemId())[0][0]['username']
        except:
            # ignore any exception and return an empty username
            return ""

    def getLocalName(self):
        return self.rhnUsername() or self.hostName()

    def get_msg(self):
        msg_dict = {"distro": "Red Hat Enterprise Linux"}
        if os.path.isfile('/etc/fedora-release'):
           msg_dict['distro'] = 'Fedora'
        return self.msg % msg_dict

# vim: ts=4 sw=4 et
