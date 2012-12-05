from sos.plugins import Plugin, RedHatPlugin

# Class name must be the same as file name and method names must not change
class rhevm(Plugin, RedHatPlugin):
    """Nogah related information"""

    optionList = [("vdsmlogs",  'Directory containing all of the SOS logs from the RHEV hypervisor(s)', '', False)]

    def setup(self):
        # Copy rhevm config files.
        self.addCopySpec("/etc/rhevm")
        self.addCopySpec("/var/log/rhevm")
        if self.getOption("vdsmlogs"):
            self.addCopySpec(self.getOption("vdsmlogs"))

    def postproc(self):
        """
        Obfuscate passwords.
        """

        self.doFileSub("/etc/rhevm/rhevm-config/rhevm-config.properties",
                        r"Password.type=(.*)",
                        r'Password.type=********')
