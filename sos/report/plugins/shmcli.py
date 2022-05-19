# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class SHMcli(Plugin, IndependentPlugin):
    """shmcli pulls hardware information from PowerVault/Dell
    Storage JBOD's attached to server.
    It provides information of the adapters, emms, drives,
    enclosures, fans, power supplies and the sensory data of
    temp, voltage, and current sensors.
    """

    short_desc = 'Dell Server Hardware Manager'

    plugin_name = 'shmcli'
    profiles = ('system', 'storage', 'hardware',)
    shmcli_bin = "/opt/dell/ServerHardwareManager/" \
                 "ServerHardwareManagerCLI/bin/shmcli"
    files = (shmcli_bin,)

    option_list = [
        PluginOpt('debug', default=False, desc='capture support debug data')
    ]

    def setup(self):
        cmd = self.shmcli_bin

        subcmds = [
            'list adapters',
            'list physical enclosures',
            'list failed drives'
        ]

        for subcmd in subcmds:
            self.add_cmd_output(
                "%s %s" % (cmd, subcmd),
                suggest_filename="shmcli_%s" % (subcmd))

        models = []

        # Get the storage hardware models
        result = self.exec_cmd('lsscsi -g')
        if result['status'] == 0:
            for line in result['output'].splitlines():
                words = line.split()
                if (len(words) > 2 and words[2].upper() == 'DELL'):
                    models.append(line.split()[3])
        models = list(set(models))

        subcmds = [
            'list emms',
            'list drawers',
            'list emm slots',
            'list drive slots',
            'list fans',
            'list temp sensors',
            'list voltage sensors',
            'list current sensors',
            'list power supplies',
            'info enclosure'
        ]

        result = self.collect_cmd_output(
            '%s list enclosures' % (cmd),
            suggest_filename='shmcli_list_enclosures'
        )
        if result['status'] == 0:
            for line in result['output'].splitlines()[2:-2]:
                _line = line.split()
                if any(m in _line for m in models):
                    adapt_index = _line[-1]
                    enc_index = _line[0]
                    for subcmd in subcmds:
                        _cmd = ("%s %s -a=%s -enc=%s"
                                % (cmd, subcmd, adapt_index, enc_index))
                        _fname = _cmd.replace(cmd, 'shmcli')
                        self.add_cmd_output(_cmd, suggest_filename=_fname)
                    if self.get_option('debug'):
                        logpath = self.get_cmd_output_path(make=False)
                        _dcmd = ("%s getdebugcli -a=%s -enc=%s"
                                 % (cmd, adapt_index, enc_index))
                        _dname = _dcmd.replace(cmd, 'shmcli')
                        _odir = (" -outputdir=%s" % (logpath))
                        self.add_cmd_output(
                            _dcmd + _odir, suggest_filename=_dname,
                            timeout=300
                        )

        result = self.collect_cmd_output(
            '%s list drives' % (cmd),
            suggest_filename='shmcli_list_drives'
        )
        if result['status'] == 0:
            for line in result['output'].splitlines():
                words = line.split()
                if (len(words) > 6):
                    if (words[0] not in ['WWN', '---']):
                        _cmd = ("%s info drive -d=%s"
                                % (cmd, words[0]))
                        _fname = _cmd.replace(cmd, 'shmcli')
                        self.add_cmd_output(_cmd, suggest_filename=_fname)

# vim: set et ts=4 sw=4 :
