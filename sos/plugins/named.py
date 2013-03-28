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

from sos.plugins import Plugin, RedHatPlugin
import commands
from os.path import normpath, join, exists

class named(Plugin, RedHatPlugin):
    """named related information
    """

    files = ('/etc/named.conf', '/etc/sysconfig/named')
    packages = ('bind',)

    def getDnsDir(self, configFile):
        """ grab directory path from named{conf,boot}
        """
        directoryList = self.do_regex_find_all("directory\s+\"(.*)\"", configFile)
        return normpath(directoryList[0])

    def setup(self):
        cfgFiles = ("/etc/named.conf",
                    "/etc/named.boot")
        for cfg in cfgFiles:
            if exists(cfg):
                self.add_copy_spec(cfg)
                self.add_copy_spec(self.getDnsDir(cfg))
                self.add_forbidden_path(join(self.getDnsDir(cfg),"chroot/dev"))
                self.add_forbidden_path(join(self.getDnsDir(cfg),"chroot/proc"))

        self.add_copy_spec("/etc/named/")
        self.add_copy_spec("/etc/sysconfig/named")
        self.add_cmd_output("klist -ket /etc/named.keytab")
        self.add_forbidden_path("/etc/named.keytab")
        return

    def postproc(self):
        match = r"(\s*arg \"password )[^\"]*"
        subst = r"\1******"
        self.do_file_sub("/etc/named.conf", match, subst)
