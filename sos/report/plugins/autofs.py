# Copyright (C) 2007 Red Hat, Inc., Adam Stokes <astokes@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin


class Autofs(Plugin):

    short_desc = 'Autofs on-demand automounter'

    plugin_name = "autofs"
    profiles = ('storage', 'nfs')

    files = ('/etc/sysconfig/autofs', '/etc/default/autofs')
    packages = ('autofs',)

    def checkdebug(self):
        """ testing if autofs debug has been enabled anywhere
        """
        # Global debugging
        opt = self.file_grep(r"^(DEFAULT_LOGGING|DAEMONOPTIONS)=(.*)",
                             *self.files)
        for opt1 in opt:
            for opt2 in opt1.split(" "):
                if opt2 in ("--debug", "debug"):
                    return True
        return False

    def getdaemondebug(self):
        """ capture daemon debug output
        """
        debugout = self.file_grep(r"^(daemon.*)\s+(\/var\/log\/.*)",
                                  *self.files)
        for i in debugout:
            return i[1]

    def setup(self):
        self.add_copy_spec("/etc/auto*")
        self.add_service_status("autofs")
        self.add_cmd_output("automount -m")
        if self.checkdebug():
            self.add_copy_spec(self.getdaemondebug())

    def postproc(self):
        self.do_path_regex_sub(
            "/etc/auto*",
            r"(password=)[^,\s]*",
            r"\1********"
        )
        self.do_cmd_output_sub(
            "automount -m",
            r"(password=)[^,\s]*",
            r"\1********"
        )


class RedHatAutofs(Autofs, RedHatPlugin):

    def setup(self):
        super(RedHatAutofs, self).setup()
        if self.get_option("verify"):
            self.add_cmd_output("rpm -qV autofs")


class DebianAutofs(Autofs, DebianPlugin, UbuntuPlugin):

    def setup(self):
        super(DebianAutofs, self).setup()
        self.add_cmd_output("dpkg-query -s autofs")

# vim: set et ts=4 sw=4 :
