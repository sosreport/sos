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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import commands
from os.path import normpath, join, exists

class Named(Plugin):
    """named related information
    """

    plugin_name = "named"

    def get_dns_dir(self, config_file):
        """ grab directory path from named{conf,boot}
        """
        directory_list = self.do_regex_find_all("directory\s+\"(.*)\"", config_file)
        if directory_list:
            return normpath(directory_list[0])
        else:
            return ""

class RedHatNamed(Named, RedHatPlugin):
    """named related information for RedHat based distribution
    """

    files = ('/etc/named.conf', '/etc/sysconfig/named')
    packages = ('bind',)

    def setup(self):
        super(RedHatNamed, self).setup()
        config_files = ("/etc/named.conf",
                    "/etc/named.boot")
        for cfg in config_files:
            if exists(cfg):
                self.add_copy_spec(cfg)
                self.add_copy_spec(self.get_dns_dir(cfg))
                self.add_forbidden_path(join(self.get_dns_dir(cfg),"chroot/dev"))
                self.add_forbidden_path(join(self.get_dns_dir(cfg),"chroot/proc"))

        self.add_copy_spec("/etc/named/")
        self.add_copy_spec("/etc/sysconfig/named")
        self.add_cmd_output("klist -ket /etc/named.keytab")
        self.add_forbidden_path("/etc/named.keytab")
        return

    def postproc(self):
        match = r"(\s*arg \"password )[^\"]*"
        subst = r"\1******"
        self.do_file_sub("/etc/named.conf", match, subst)

class DebianNamed(Named, DebianPlugin, UbuntuPlugin):
    """named related information for Debian based distribution
    """

    files = ('/etc/bind/named.conf')
    packages = ('bind9',)

    def setup(self):
        super(DebianNamed, self).setup()
        config_files = ("/etc/bind/named.conf",
                    "/etc/bind/named.conf.options",
                    "/etc/bind/named.conf.local")
        for cfg in config_files:
            if exists(cfg):
                self.add_copy_spec(cfg)
                self.add_copy_spec(self.get_dns_dir(cfg))
                self.add_forbidden_path(join(self.get_dns_dir(cfg),"chroot/dev"))
                self.add_forbidden_path(join(self.get_dns_dir(cfg),"chroot/proc"))

        self.add_copy_spec("/etc/bind/")
        return

    def postproc(self):
        match = r"(\s*arg \"password )[^\"]*"
        subst = r"\1******"
        self.do_file_sub("/etc/bind/named.conf", match, subst)
