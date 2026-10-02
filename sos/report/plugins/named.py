# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from os.path import join, normpath
from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Named(Plugin):

    short_desc = 'BIND named server'

    plugin_name = "named"
    profiles = ('system', 'services', 'network')
    named_conf = "/etc/named.conf"
    config_files = named_conf

    def setup(self):
        self.add_copy_spec([
            "/etc/default/bind",
            "/var/log/named*.log"
        ])
        for cfg in self.config_files:
            if self.path_exists(cfg):
                self.add_copy_spec([
                    cfg,
                    self.get_dns_dir(cfg)
                ])
                self.add_forbidden_path([
                    join(self.get_dns_dir(cfg), "chroot/dev"),
                    join(self.get_dns_dir(cfg), "chroot/proc")
                ])

        # runtime state of the running server. `rndc status` is read-only
        # and does not modify the daemon.
        self.add_cmd_output("rndc status", tags="rndc_status")

        # configuration syntax validation
        if self.path_exists(self.named_conf):
            self.add_cmd_output(f"named-checkconf {self.named_conf}",
                                tags="named_checkconf")

    def get_dns_dir(self, config_file):
        """ grab directory path from named{conf,boot}
        """
        directory_list = self.do_regex_find_all(r"directory\s+\"(.*)\"",
                                                config_file)
        if directory_list:
            return normpath(directory_list[0])

        return ""

    def postproc(self):
        match = r"(\s*arg \"password )[^\"]*"
        subst = r"\1******"
        self.do_file_sub(self.named_conf, match, subst)


class RedHatNamed(Named, RedHatPlugin):

    named_conf = "/etc/named.conf"
    config_files = ("/etc/named.conf",
                    "/etc/named.boot")
    files = (named_conf, '/etc/sysconfig/named')
    packages = ('bind',)
    chroot_dir = "/var/named/chroot"

    def setup(self):
        super().setup()
        self.add_copy_spec("/etc/named/")
        self.add_copy_spec("/etc/sysconfig/named")
        self.add_cmd_output("klist -ket /etc/named.keytab")
        self.add_forbidden_path("/etc/named.keytab")

        # for named-chroot deployments, validate the config inside the
        # chroot using BIND's own -t flag
        if self.path_exists(self.chroot_dir):
            self.add_cmd_output(
                f"named-checkconf -t {self.chroot_dir} {self.named_conf}",
                tags="named_checkconf"
            )


class DebianNamed(Named, DebianPlugin, UbuntuPlugin):

    files = ('/etc/bind/named.conf',)
    packages = ('bind9',)
    named_conf = "/etc/bind/named.conf"
    config_files = (named_conf,
                    "/etc/bind/named.conf.options",
                    "/etc/bind/named.conf.local")

    def setup(self):
        super().setup()
        self.add_copy_spec("/etc/bind/")


# vim: set et ts=4 sw=4 :
