# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, SoSPredicate
from sos.utilities import is_executable


class ZVM(Plugin, IndependentPlugin):

    plugin_name = 'zvm'
    short_desc = 'IBM z/VM information'
    commands = ('vmcp', 'hcp')

    def setup(self):

        zvm_pred = SoSPredicate(self, kmods=['vmcp', 'cpint'])
        self.set_cmd_predicate(zvm_pred)

        self.vm_cmd = None
        for cmd in self.commands:
            if is_executable(cmd):
                self.vm_cmd = cmd
                break

        # vm commands from dbginfo.sh
        vm_cmds = [
            "q userid",
            "q users",
            "q privclass",
            "q cplevel",
            "q cpservice",
            "q cpprot user",
            "q specex",
            "q ssi",
            "q cpus",
            "q srm",
            "q vtod",
            "q time full",
            "q timezone",
            "q loaddev",
            "q v osa",
            "q v dasd",
            "q v crypto",
            "q v fcp",
            "q v pav",
            "q v sw",
            "q v st",
            "q v nic",
            "q st",
            "q xstore",
            "q xstore user system",
            "q sxspages",
            "q vmlan",
            "q vswitch",
            "q vswitch details",
            "q vswitch access",
            "q vswitch active",
            "q vswitch accesslist",
            "q vswitch promiscuous",
            "q vswitch controller",
            "q port group all active details",
            "q set",
            "q comm",
            "q controller all",
            "q fcp",
            "q frames",
            "q lan",
            "q lan all details",
            "q lan all access",
            "q memassist",
            "q nic",
            "q pav",
            "q proc",
            "q proc topology",
            "q mt",
            "q qioass",
            "q spaces",
            "q swch all",
            "q trace",
            "q mdcache",
            "q alloc page",
            "q alloc spool",
            "q dump",
            "q dumpdev",
            "q pcifunction",
            "q vmrelocate",
            "ind load",
            "ind sp",
            "ind user"
        ]

        vm_id_out = self.collect_cmd_output("%s q userid" % self.vm_cmd)
        if vm_id_out['status'] == 0:
            vm_id = vm_id_out['output'].split()[0]
            vm_cmds.extend([
                "q reorder %s" % vm_id,
                "q quickdsp %s" % vm_id
            ])

        self.add_cmd_output([
            "%s %s" % (self.vm_cmd, vcmd) for vcmd in vm_cmds
        ])

# vim: set et ts=4 sw=4 :
