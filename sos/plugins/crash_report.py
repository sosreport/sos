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
import sys
import time
from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
from sos.utilities import sos_get_command_output, find
from datetime import datetime

class CrashLog(Plugin):
    """Crash kernel report
    """
    plugin_name = "crash_report"
    profiles = ('system', 'debug')

    dbg_vmlinux_path = '/usr/lib/debug/'
    vmcore_stnd_path = '/var/crash'

    dump_file_prefix = ''
    crashed_kernel_name = ''
    vmlinux_path = ''
    message_to_log = ''
    vmcore_file_path = ''
    crash_script = ""
    # crash result output file
    crashed_output_file = '/var/log/os_crash_report.txt'

    # list of crash command
    crash_cmd_list = [
                    ("sys", "\"SYSTEM INFORMATION:\""),
                    ("mach", "\"MACHINE SPECIFIC DATA:\""),
                    ("mach", "\"MACHINE SPECIFIC DATA:\""),
                    ("bt", "\"STACK TRACE OF CURRENT CONTEXT:\""),
                    ("bt -a", "\"STACK TRACES OF ACTIVE TASKS:\""),
                    ("kmem -i", "\"MEMORY USAGE:\""),
                    ("kmem -s" , "\"KMALLOC SLAB DATA:\""),
                    ("mod", "\"MODULES:\""),
                    ("ps", "\"PROCESS STATUS:\""),
                    ("log", "\"SYSTEM MESSAGE BUFFER:\""),
                    ("files", "\"OPEN FILES OF CURRENT CONTEXT:\""),
                    ("dev -p", "\"PCI DEVICE DATA:\""),
                    ("runq", "\"RUN QUEUE TASK:\""),
                    ("mach -o", "\"OPALMSG LOG:\""),
                    ("irq -s", "\"DUMP KERNEL IRQ STATE:\"")]

    """
    parse crash_cmd_list and form crash_script which will
    be given as an input to crash command
    """
    def form_crash_script(self):
        for idx in range(len(self.crash_cmd_list)):
            cmd = self.crash_cmd_list[idx][0]
            header = self.crash_cmd_list[idx][1]
            self.crash_script += "!echo %s >>{OUTPUT}\n" %header
            self.crash_script += "!echo >> {OUTPUT}\n"
            self.crash_script += "%s >> {OUTPUT}\n" %cmd
            self.crash_script += "!echo >> {OUTPUT}\n"
            self.crash_script += "!echo >> {OUTPUT}\n"
        self.crash_script += "quit\n"
        self.crash_script += "!echo >> {OUTPUT}\n"
        self.crash_script += "!echo >> {OUTPUT}\n"

    """
    used to find dump for crashed kernel.
    it compares the time of dump file with last crashed time.
    return
        True  : In case of success.
        False : In case of failure.
    """
    def is_dump_for_crashing_kernel(self,  file_path, crashing_time):
        file_creation_info = time.ctime(os.path.getctime(file_path))

        """
        get the actual time string using split on complete line
        ctime returns string as 'Mon Mar 13 02:54:32 2017'
        we are interested only in Month date hrs:min field
        """
        vmcore_creation_time = file_creation_info.rsplit(':', 1)[0].split(' ', 1)[1]
        t1 = datetime.strptime(vmcore_creation_time, "%b %d %H:%M")
        t2 = datetime.strptime(crashing_time, "%b %d %H:%M")
        difference = t1 - t2
        return  True if difference.days == 0 else False

    # retrieve path of vmlinux/vmcore
    def retrieve_path(self, start_path, file_type, file_opt, crashing_time):
        if file_type == "vmcore":
            for filename in find(self.dump_file_prefix, start_path):
                ret = self.is_dump_for_crashing_kernel(filename, crashing_time)
                if ret:
                    self.vmcore_file_path = filename
                    return 0
        elif file_type == "vmlinu":
            for filename in find("vmlinu*", start_path):
                """
                in rhel : 3.10.0-327.el7.ppc64/vmlinux
                in ubuntu: vmlinux-4.4.0-21-generic
                hence below check confirms that vmlinux is of crashed kernel
                """
                if filename.find(file_opt) != -1:
                    self.vmlinux_path = filename
                    return 0
        return -1

    def get_crash_time(self, line):
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


    def get_vmlinux_vmcore_path(self):
        # retrieve data from last command
        last_cmd_res = sos_get_command_output('last')
        if last_cmd_res['status']:
            self.message_to_log = '\n\n' + 'last cmd failed' + '\n\n'
            self.dump_log_data()
            return -1

        crash_found = False

        for line in last_cmd_res['output'].splitlines():
            line = line.rstrip()
            if crash_found == True:
                reboot_str = (line.split()[0] +' ' + line.split()[1] + ' ' +
                        line.split()[2])
                if reboot_str == 'reboot system boot':
                    line_contain_os = line
                    self.crashed_kernel_name = line.split()[3]
                    break
            elif "crash" in line:
                line_contain_crash = line
                crash_found = True
        if not crash_found or self.crashed_kernel_name == "":
            self.message_to_log = ('\n\n' +
                'Failed in retrieving crash from last cmd output:' +
                '\n\n')
            return -1
        crashing_time = self.get_crash_time(line_contain_crash)
        if not crashing_time:
            self.message_to_log = ('\n\n' +
                'Failed in retrieving time for last crash:' +
                '[ ' + line_contain_crash + ' ]' + '\n\n')
            return -1
        ret = self.retrieve_path(self.dbg_vmlinux_path, "vmlinu",
                   self.crashed_kernel_name, crashing_time)
        if ret:
            self.message_to_log = ('\n\n' +
                    'Failed in retrieving debug linux:' +
                    '[ ' + self.crashed_kernel_name + ' ]' +
                    ' inside path: [ ' + self.dbg_vmlinux_path + ' ]' +
                    '\nPlease install debug linux and rerun sosreport\n\n')
            return -1
        ret = self.retrieve_path(self.vmcore_stnd_path, "vmcore", "",
                    crashing_time)
        if ret:
            self.message_to_log = ('\n\n' +
                'Failed in retrieving vmcore for kernel[ ' +
                self.crashed_kernel_name + ']' + ' inside path: [ ' +
                self.vmcore_stnd_path + ' ]' + '\n\n')
            return -1
        return 0

    #dump error log to output file
    def dump_log_data(self):
        try:
            f = open(self.crashed_output_file,"a")
        except IOError:
            sys.stderr.write('\n\nFailed opening crash log file:[%s]\n\n'
                % self.crashed_output_file)
            return -1
        try:
            f.write("\n\n[%s]\n\n"
                % self.message_to_log)
        except:
            sys.stderr.write('write to log file failed\n')
            f.close()
            return -1
        f.close()
        return 0

    def postproc(self):
        if os.path.exists(self.crashed_output_file):
            os.remove(self.crashed_output_file)

    def get_crash_report(self):
        result = self.get_vmlinux_vmcore_path()
        if result:
            self.dump_log_data()
            return

        self.form_crash_script()
        crash_full_command  = ("crash" + " -s " +
            self.vmlinux_path + " " + self.vmcore_file_path)
        self.message_to_log = 'crash command: ' + crash_full_command
        self.dump_log_data()
        print ("\n\nCollecting crash report. This may take a while !!! ...\n\n")
        result = sos_get_command_output(crash_full_command, stderr=True,
                input=self.crash_script.format(OUTPUT=self.crashed_output_file))

        if result['status']:
            self.message_to_log = '\n\n' + 'crash cmd failed' + '\n\n'
            self.dump_log_data()
        return

class RedHatCrashLog(CrashLog, RedHatPlugin):

    def setup(self):
        CrashLog.dump_file_prefix = 'vmcore'
        self.get_crash_report()
        self.add_copy_spec([
            CrashLog.crashed_output_file
        ])


class DebianCrashLog(CrashLog, DebianPlugin, UbuntuPlugin):

    def setup(self):
        CrashLog.dump_file_prefix = 'dump.*'
        self.get_crash_report()
        self.add_copy_spec([
            CrashLog.crashed_output_file
        ])

# vim: set et ts=4 sw=4 :
