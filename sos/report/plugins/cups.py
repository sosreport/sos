# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import pwd

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class Cups(Plugin, IndependentPlugin):

    short_desc = 'CUPS IPP print service'

    plugin_name = 'cups'
    profiles = ('hardware',)
    services = ('cups', 'cups-browsed',
                'lprint', 'legacy-printer-app')
    packages = ('cups',)

    option_list = [
        PluginOpt('userconfs', default=False,
                  desc=('Changes whether plugin will '
                        'collect user .cups configs'))
    ]

    def setup(self):
        if not self.get_option("all_logs"):
            self.add_copy_spec("/var/log/cups/access_log")
            self.add_copy_spec("/var/log/cups/error_log")
            self.add_copy_spec("/var/log/cups/page_log")
            self.add_copy_spec("/var/log/ipp-usb/main.log")
        else:
            self.add_copy_spec("/var/log/cups")
            self.add_copy_spec("/var/log/ipp-usb")

        self.add_copy_spec([
            "/etc/cups/*.conf",
            "/etc/cups/*.types",
            "/etc/cups/lpoptions",
            "/etc/cups/ppd/*.ppd",
            "/etc/ipp-usb/",
            "/etc/lprint.conf",
            "/etc/legacy-printer-app.conf",
            "/var/lib/lprint.state",
            "/var/lib/legacy-printer-app.state",
        ])

        self.add_cmd_output([
            "lpstat -t",
            "lpstat -s",
            "lpstat -d"
        ])

        if self.get_option('userconfs'):
            self.get_user_configs()

    def get_user_configs(self):
        """
        Iterate over .cups folders in user homes to capture config files.
        """
        users_data = pwd.getpwall()
        config_files = [
            "client.conf",
            "lpoptions",
        ]
        fs_mount_info = {}
        try:
            with open('/proc/mounts', "r", encoding='UTF-8') as mounts_file:
                for line in mounts_file:
                    (fs_file, fs_vstype) = line.split()[1:3]
                    fs_mount_info[fs_file] = fs_vstype
        except Exception:
            self._log_error("Couldn't read /proc/mounts")
            return
        non_local_fs = {'nfs', 'nfs4', 'autofs'}
        # Read the home paths of users in the system and
        # config files from .cups
        for user in users_data:
            if user.pw_dir in fs_mount_info and \
                    fs_mount_info[user.pw_dir] in non_local_fs:
                self._log_info(
                    f"Skipping capture in {user.pw_dir}"
                    " because it's a remote directory"
                )
                continue
            home_dir = self.path_join(user.pw_dir, '.cups')
            self.add_copy_spec(
                [f"{home_dir}/{config_file}" for config_file in config_files]
            )

# vim: set et ts=4 sw=4 :
