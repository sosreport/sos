# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class Libraries(Plugin, IndependentPlugin):

    short_desc = 'Dynamic shared libraries'

    plugin_name = 'libraries'
    profiles = ('system',)

    option_list = [
        PluginOpt('ldconfigv', default=False,
                  desc='collect verbose ldconfig output')
    ]

    def setup(self):
        self.add_copy_spec(["/etc/ld.so.conf", "/etc/ld.so.conf.d"])
        if self.get_option("ldconfigv"):
            self.add_cmd_output("ldconfig -v -N -X")

        self.add_env_var([
            'PATH',
            'LD_LIBRARY_PATH',
            'LD_PRELOAD'
        ])

        ldconfig = self.collect_cmd_output("ldconfig -p -N -X")

        if ldconfig['status'] == 0:
            # Collect library directories from ldconfig's cache
            dirs = set()
            for lib in ldconfig['output'].splitlines():
                s = lib.split(" => ", 2)
                if len(s) != 2:
                    continue
                dirs.add(s[1].rsplit('/', 1)[0])

            if dirs:
                self.add_cmd_output("ls -lanH %s" % " ".join(dirs),
                                    suggest_filename="ld_so_cache")

# vim: set et ts=4 sw=4 :
