import sos.plugintools

# Class name must be the same as file name and method names must not change
class ovirt(sos.plugintools.PluginBase):
    """oVirt related information"""

    optionList = [
         ("vdsmlogs",  'Directory containing all of the SOS logs from the hypervisor(s)', '', False),
         ("prefix", "Prefix the sosreport archive", '', False)
    ]

    def setup(self):
        # Copy ovirt config files.
        self.addCopySpec("/etc/ovirt-engine")
        self.addCopySpec("/var/log/ovirt-engine")
        self.addCopySpec("/etc/rhevm")
        self.addCopySpec("/var/log/rhevm/")
        if self.getOption("vdsmlogs"):
            self.addCopySpec(self.getOption("vdsmlogs"))


    def postproc(self):
        """
        Obfuscate passwords.
        """
        self.doRegexSub("/etc/ovirt-engine/engine-config/engine-config.properties",
                        r"Password.type=(.*)",
                        r'Password.type=********')

        self.doRegexSub("/etc/rhevm/rhevm-config/rhevm-config.properties",
                        r"Password.type=(.*)",
                        r'Password.type=********')

        if self.getOption("prefix"):
            current_name = self.policy().reportName
            self.policy().reportName = "LogCollector-" + current_name
