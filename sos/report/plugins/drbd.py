# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin
from sos.utilities import find


class DRBD(Plugin, RedHatPlugin, UbuntuPlugin):

    short_desc = 'Distributed Replicated Block Device (DRBD)'

    plugin_name = 'drbd'
    profiles = ('storage',)
    commands = ('drbdsetup',)

    # In case of kernel bugs, drbdsetup may hang indefinitely.
    # Set a shorter than default timeout.
    cmd_timeout = 60

    def add_drbd_thread_stacks(self):
        stacks = ""
        for pid_file in find("*_pid", "/sys/kernel/debug/drbd/resources/"):
            with open(pid_file, 'r', encoding='utf-8') as f:
                pid = f.read().strip()
            stacks += f"--- {pid_file}: {pid} ---\n"
            if pid.isdigit():
                try:
                    sfn = f"/proc/{pid}/stack"
                    with open(sfn, 'r', encoding='utf-8') as sf:
                        stacks += sf.read()
                except Exception as e:
                    stacks += f"Could not read /proc/{pid}/stack: {e}\n"
            stacks += "\n"

        self.add_string_as_file(stacks, "drbd_thread_stacks")

    def setup(self):
        self.add_cmd_output([
            "drbdadm dump",
            "drbdadm -d -vvv adjust all",
            "drbdsetup status -vs all",
            "drbdsetup show all"
        ])
        self.add_drbd_thread_stacks()
        for kmod in find("drbd*.ko*", "/lib/modules"):
            self.add_cmd_output([
                f"modinfo {kmod}",
            ], suggest_filename=f"modinfo_{kmod.replace('/', '_')}")
        self.add_copy_spec([
            "/etc/drbd.conf",
            "/etc/drbd.d/*",
            "/proc/drbd",
            "/sys/kernel/debug/drbd/*",
            "/var/lib/drbd/*",
            "/var/lib/drbd-support/*",
            "/var/lib/linstor.d/*"
        ])

    def postproc(self):
        # Scrub nodehash from /var/lib/drbd-support/registration.json
        nodehash_re = r'("nodehash"\s*:\s*")[a-zA-Z0-9]+"'
        repl = r'\1********"'
        self.do_path_regex_sub(
            '/var/lib/drbd-support/registration.json',
            nodehash_re, repl
        )

        # Scrub shared secret from *.{conf,res} files and command outputs
        secret_re = r'(shared-secret\s+\"?).[^\"]+(\"?\s*;)'
        repl = r'\1********\2'
        self.do_path_regex_sub(r'.*\.(conf|res)', secret_re, repl)
        self.do_cmd_output_sub("drbdadm dump", secret_re, repl)
        self.do_cmd_output_sub("drbdsetup show all", secret_re, repl)

# vim: set et ts=4 sw=4 :
