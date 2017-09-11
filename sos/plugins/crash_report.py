# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
import time
from datetime import datetime
from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
from sos.utilities import sos_get_command_output, find


class CrashReport(Plugin):
    """Crash kernel report
    """
    plugin_name = "crash_report"
    profiles = ('system', 'debug')

    dbg_vmlinux_path = '/usr/lib/debug/'
    vmcore_stnd_path = '/var/crash'

    crash_script = ""

    # list of crash command
    crash_cmd_list = [
        ("sys", "SYSTEM INFORMATION:"),
        ("help -m", "STACK LOCATION INFO:"),
        ("bt", "STACK TRACE OF CURRENT CONTEXT:"),
        ("bt -a", "STACK TRACES OF ACTIVE TASKS:"),
        ("kmem -i", "MEMORY USAGE:"),
        ("kmem -s", "KMALLOC SLAB DATA:"),
        ("mod", "MODULES:"),
        ("ps", "PROCESS STATUS:"),
        ("log", "SYSTEM MESSAGE BUFFER:"),
        ("files", "OPEN FILES OF CURRENT CONTEXT:"),
        ("dev -p", "PCI DEVICE DATA:"),
        ("runq", "RUN QUEUE TASK:"),
        ("mach -o", "OPALMSG LOG:"),
        ("irq -s", "DUMP KERNEL IRQ STATE:")]

    def setup(self):
        path = self.get_cmd_output_path()
        CrashReport.output_file = os.path.join(path, 'crash_report.txt')
        self.get_crash_report()

    def form_crash_script(self):
        """
        parse crash_cmd_list and form crash_script which will
        be given as an input to crash command
        """
        for (cmd, header) in self.crash_cmd_list:
            self.crash_script += "!echo %s >>{OUTPUT}\n" % header
            self.crash_script += "!echo >> {OUTPUT}\n"
            self.crash_script += "%s >> {OUTPUT}\n" % cmd
            self.crash_script += "!echo >> {OUTPUT}\n"
            self.crash_script += "!echo >> {OUTPUT}\n"
        self.crash_script += "quit\n"
        self.crash_script += "!echo >> {OUTPUT}\n"
        self.crash_script += "!echo >> {OUTPUT}\n"

    def is_dump_for_crashing_kernel(self, file_path, crashing_time):
        file_creation_info = time.ctime(os.path.getctime(file_path))
        """
        used to find dump for crashed kernel.
        it compares the time of dump file with last crashed time.
        It looks for dump(vmcore) file whose creation time is newer
        than the time of system crashed, In this case (t1 >= t2) and
        hence difference.days >= 0.
        return
            True  : In case of success.
            False : In case of failure.
        """

        """
        get the actual time string using split on complete line
        ctime returns string as 'Mon Mar 13 02:54:32 2017'
        we are interested only in Month date hrs:min field
        """
        vmcore_creation_time = file_creation_info.rsplit(':', 1)[0].split(
                                                          ' ', 1)[1]
        t1 = datetime.strptime(vmcore_creation_time, "%b %d %H:%M")
        t2 = datetime.strptime(crashing_time, "%b %d %H:%M")
        difference = t1 - t2
        return True if difference.days >= 0 else False

    def get_crash_time(self, line):
        """
        Here we are trying to get crash time(m/d/hr/min) from last cmd output
        Sample example of lines are:
        root     pts/0        gateway       Fri Aug 18 04:35 - crash  (00:05)
        root     hvc0                       Fri Aug 18 04:41 - crash  (00:06)
        """
        crashing_time = (line.split()[4] + ' ' + line.split()[5] +
                         ' ' + line.split()[6])
        try:
            t2 = datetime.strptime(crashing_time, "%b %d %H:%M")
        except ValueError:
            t2 = None
            crashing_time = (line.split()[3] + ' ' + line.split()[4] +
                             ' ' + line.split()[5])
            try:
                t2 = datetime.strptime(crashing_time, "%b %d %H:%M")
            except ValueError:
                t2 = None
                return ""
        return crashing_time

    def get_core_info(self):
        # Collect data from last command
        last_cmd_res = sos_get_command_output('last')
        if last_cmd_res['status']:
            self._log_error("last command failed")
            return -1

        crash_found = False

        for line in last_cmd_res['output'].splitlines():
            """
            Sample example of last command output:
            root     pts/0        gateway   Mon Aug 21 23:52   still logged in
            root     hvc0                   Fri Aug 18 04:41 - crash(00:06)
            reboot   system boot  3.10.0-514.el7.p Mon Aug 21 01:28 - 00:41
            Below loop reads line by line and get crash kernel name,
            crashing time info
            """
            line = line.rstrip()
            if crash_found is True:
                reboot_str = (line.split()[0] + ' ' + line.split()[1] + ' ' +
                              line.split()[2])
                if reboot_str == 'reboot system boot':
                    self.crashed_kernel_name = line.split()[3]
                    break
            elif "crash" in line:
                line_contain_crash = line
                crash_found = True
        if not crash_found or self.crashed_kernel_name == "":
            self._log_error("Failed in finding crash from last cmd output")
            return -1
        crashing_time = self.get_crash_time(line_contain_crash)
        if not crashing_time:
            self._log_error("Failed in locating time for last crash:[%s]"
                            % line_contain_crash)
            return -1
        ret = self.get_vmlinux_path(self.dbg_vmlinux_path,
                                    self.crashed_kernel_name)
        if ret:
            return -1
        ret = self.get_vmcore_path(self.vmcore_stnd_path, crashing_time)
        if ret:
            return -1
        return 0

    def get_vmlinux_path(self, dbg_vmlinux_path, kernel_name):
        for filename in find("vmlinu*", dbg_vmlinux_path):
            """
            in rhel : 3.10.0-327.el7.ppc64/vmlinux
            in ubuntu: vmlinux-4.4.0-21-generic
            hence below check confirms that vmlinux is of crashed kernel
            """
            if filename.find(kernel_name) != -1:
                self.vmlinux_path = filename
                return 0
        self._log_error("Debug vmlinux not found['%s'] inside path:['%s']"
                        % (self.crashed_kernel_name, self.dbg_vmlinux_path))
        return -1

    def get_vmcore_path(self, vmcore_stnd_path, crashing_time):
        for filename in find(self.dump_file_prefix, vmcore_stnd_path):
            ret = self.is_dump_for_crashing_kernel(filename, crashing_time)
            if ret:
                self.vmcore_file_path = filename
                return 0
        self._log_error("vmcore not found for kernel['%s'] inside path: ['%s']"
                        % (self.crashed_kernel_name, self.vmcore_stnd_path))
        return -1

    def get_crash_report(self):
        result = self.get_core_info()
        if result:
            return

        self.form_crash_script()
        crash_full_command = ("crash" + " -s " + self.vmlinux_path + " " +
                              self.vmcore_file_path)
        self._log_info("crash command: '%s'" % crash_full_command)
        result = sos_get_command_output(
                crash_full_command, stderr=True,
                input=self.crash_script.format(
                 OUTPUT=self.output_file)
                )

        if result['status']:
            self._log_error("crash command failed")
        return


class RedHatCrashReport(CrashReport, RedHatPlugin):

    def default_enabled(self):
        return False

    def setup(self):
        CrashReport.dump_file_prefix = 'vmcore'
        super(RedHatCrashReport, self).setup()


class DebianCrashReport(CrashReport, DebianPlugin, UbuntuPlugin):

    def default_enabled(self):
        return False

    def setup(self):
        CrashReport.dump_file_prefix = 'dump.*'
        super(DebianCrashReport, self).setup()

# vim: set et ts=4 sw=4 :
