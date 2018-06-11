# Copyright (C) 2015 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

# This enables the use of with syntax in python 2.5 (e.g. jython)
from __future__ import print_function
import os
import sys

from sos.plugins import RedHatPlugin, SuSEPlugin
from sos.policies import LinuxPolicy, PackageManager
from sos import _sos as _


class SuSEPolicy(LinuxPolicy):
    distro = "SuSE"
    vendor = "SuSE"
    vendor_url = "https://www.suse.com/"
    _tmp_dir = "/var/tmp"

    def __init__(self, sysroot=None):
        super(SuSEPolicy, self).__init__()
        self.ticket_number = ""
        self.package_manager = PackageManager(
            'rpm -qa --queryformat "%{NAME}|%{VERSION}\\n"')
        self.valid_subclasses = [SuSEPlugin, RedHatPlugin]

        pkgs = self.package_manager.all_pkgs()

        # If rpm query timed out after timeout duration exit
        if not pkgs:
            print("Could not obtain installed package list", file=sys.stderr)
            sys.exit(1)

        self.PATH = "/usr/sbin:/usr/bin:/root/bin"
        self.PATH += os.pathsep + "/usr/local/bin"
        self.PATH += os.pathsep + "/usr/local/sbin"
        self.set_exec_path()

    @classmethod
    def check(cls):
        """This method checks to see if we are running on SuSE. It must be
        overriden by concrete subclasses to return True when running on an
        OpenSuSE, SLES or other Suse distribution and False otherwise."""
        return False

    def runlevel_by_service(self, name):
        from subprocess import Popen, PIPE
        ret = []
        p = Popen("LC_ALL=C /sbin/chkconfig --list %s" % name,
                  shell=True,
                  stdout=PIPE,
                  stderr=PIPE,
                  bufsize=-1,
                  close_fds=True)
        out, err = p.communicate()
        if err:
            return ret
        for tabs in out.split()[1:]:
            try:
                (runlevel, onoff) = tabs.split(":", 1)
            except IndexError:
                pass
            else:
                if onoff == "on":
                    ret.append(int(runlevel))
        return ret

    def get_tmp_dir(self, opt_tmp_dir):
        if not opt_tmp_dir:
            return self._tmp_dir
        return opt_tmp_dir

    def get_local_name(self):
        return self.host_name()


class OpenSuSEPolicy(SuSEPolicy):
    distro = "OpenSuSE"
    vendor = "SuSE"
    vendor_url = "https://www.opensuse.org/"
    msg = _("""\
This command will collect diagnostic and configuration \
information from this %(distro)s system and installed \
applications.

An archive containing the collected information will be \
generated in %(tmpdir)s and may be provided to a %(vendor)s \
support representative.

No changes will be made to system configuration.
%(vendor_text)s
""")

    def __init__(self, sysroot=None):
        super(OpenSuSEPolicy, self).__init__(sysroot=sysroot)

    @classmethod
    def check(cls):
        """This method checks to see if we are running on SuSE.
        """
        return (os.path.isfile('/etc/SuSE-release'))
