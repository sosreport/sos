# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin
import os

YUM_PLUGIN_PATH = "/usr/lib/yum-plugins/"


class Yum(Plugin, RedHatPlugin):

    short_desc = 'yum information'

    plugin_name = 'yum'
    profiles = ('system', 'packagemanager', 'sysmgmt')

    files = ('/etc/yum.conf',)
    packages = ('yum',)
    verify_packages = ('yum',)

    option_list = [
        ("yumlist", "list repositories and packages", "slow", False),
        ("yumdebug", "gather yum debugging data", "slow", False),
        ("yum-history-info", "gather yum history info", "slow", False),
    ]

    def setup(self):

        self.add_file_tags({
            '/etc/yum.repos.d/.*': 'yum_repos_d',
            '/var/log/yum.log': 'yum_log',
            '/etc/yum.conf': 'yum_conf'
        })

        # Pull all yum related information
        self.add_copy_spec([
            "/etc/yum",
            "/etc/yum.repos.d",
            "/etc/yum.conf",
            "/var/log/yum.log"
        ])

        # Get a list of channels the machine is subscribed to.
        self.add_cmd_output("yum -C repolist", tags="yum_repolist")

        # Get the same list, but with various statistics related to its
        # contents such as package count.
        self.add_cmd_output("yum -C repolist --verbose")

        # Get list of available plugins and their configuration files.
        if os.path.exists(YUM_PLUGIN_PATH) and os.path.isdir(YUM_PLUGIN_PATH):
            plugins = ""
            for p in os.listdir(YUM_PLUGIN_PATH):
                if not p.endswith(".py"):
                    continue
                plugins = plugins + " " if len(plugins) else ""
                plugins = plugins + os.path.join(YUM_PLUGIN_PATH, p)
            if len(plugins):
                self.add_cmd_output("rpm -qf %s" % plugins,
                                    suggest_filename="plugin-packages")
                plugnames = [os.path.basename(p)[:-3] for p in plugins.split()]
                plugnames = "%s\n" % "\n".join(plugnames)
                self.add_string_as_file(plugnames, "plugin-names")

        self.add_copy_spec("/etc/yum/pluginconf.d")

        # candlepin info
        self.add_forbidden_path([
            "/etc/pki/entitlement/key.pem",
            "/etc/pki/entitlement/*-key.pem"
        ])

        self.add_copy_spec([
            "/etc/pki/product/*.pem",
            "/etc/pki/consumer/cert.pem",
            "/etc/pki/entitlement/*.pem"
        ])

        self.add_cmd_output([
            "yum history",
            "yum list installed",
            "package-cleanup --dupes",
            "package-cleanup --problems"
        ], cmd_as_tag=True)

        # packages installed/erased/updated per transaction
        if self.get_option("yum-history-info"):
            history = self.exec_cmd("yum history")
            transactions = None
            if history['status'] == 0:
                for line in history['output'].splitlines():
                    try:
                        transactions = int(line.split('|')[0].strip())
                        break
                    except ValueError:
                        pass
            for tr_id in range(1, transactions+1):
                self.add_cmd_output("yum history info %d" % tr_id)

        if self.get_option("yumlist"):
            # List various information about available packages
            self.add_cmd_output("yum list")

        if self.get_option("yumdebug") and self.is_installed('yum-utils'):
            # RHEL6+ alternative for this whole function:
            # self.add_cmd_output("yum-debug-dump '%s'"
            # % os.path.join(self.commons['dstroot'],"yum-debug-dump"))
            r = self.exec_cmd("yum-debug-dump")
            try:
                self.add_cmd_output("zcat %s" % (r['output'].split()[-1],))
            except IndexError:
                pass

    def postproc(self):
        regexp = r"(proxy_password(\s)*=(\s)*)(\S+)\n"
        repl = r"\1********\n"
        self.do_path_regex_sub("/etc/yum.repos.d/*", regexp, repl)

# vim: set et ts=4 sw=4 :
