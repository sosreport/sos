# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import glob
import yaml

from sos.report.plugins import Plugin, IndependentPlugin


class SaltMaster(Plugin, IndependentPlugin):

    short_desc = 'Salt Master'

    plugin_name = 'saltmaster'
    profiles = ('sysmgmt',)

    packages = ('salt-master', 'salt-api',)

    def setup(self):
        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/salt")
        else:
            self.add_copy_spec("/var/log/salt/master")

        self.add_copy_spec("/etc/salt")
        self.add_forbidden_path("/etc/salt/pki/*/*.pem")

        self.add_pillar_roots()
        self.add_cmd_output([
            "salt-master --version",
            "systemctl --full status salt-master",
            "systemctl --full status salt-api",
            "salt-key --list all",
            "salt-run jobs.list_jobs --out=yaml",
            "salt-run manage.list_state --out=yaml",
            "salt-run manage.list_not_state --out=yaml",
            "salt-run manage.joined --out=yaml",
        ], timeout=30)

    def add_pillar_roots(self):
        """ Collect pilliar_roots of all salt configs """
        cfgs = glob.glob("/etc/salt/master.d/*conf")
        main_cfg = "/etc/salt/master"

        if self.path_exists(main_cfg):
            cfgs.append(main_cfg)

        all_pillar_roots = []
        for cfg in cfgs:
            with open(cfg, "r", encoding='UTF-8') as file:
                cfg_pillar_roots = (
                    yaml.safe_load(file).get("pillar_roots", {}).
                    get("base", [])
                )
                all_pillar_roots.extend(cfg_pillar_roots)

        self.add_copy_spec(all_pillar_roots)

    def postproc(self):
        regexp = r'(^\s+.*(pass|secret|(?<![A-z])key(?![A-z])).*:\ ).+$'
        subst = r'\1******'
        self.do_path_regex_sub("/etc/salt/*", regexp, subst)

# vim: set et ts=4 sw=4 :
