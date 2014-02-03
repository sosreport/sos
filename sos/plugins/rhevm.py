from sos.plugins import Plugin, RedHatPlugin

# Class name must be the same as file name and method names must not change
class RhevM(Plugin, RedHatPlugin):
    """RHEV-Manager related information"""

    plugin_name = 'rhevm'

    option_list = [("vdsmlogs",  'Directory containing all of the SOS logs from the RHEV hypervisor(s)', '', False)]

    def setup(self):
        # Copy rhevm config files.
        self.add_copy_spec("/etc/rhevm")
        self.add_copy_spec("/var/log/rhevm")
        if self.get_option("vdsmlogs"):
            self.add_copy_spec(str(self.get_option("vdsmlogs")))

    def postproc(self):
        """
        Obfuscate passwords.
        """

        self.do_file_sub("/etc/rhevm/rhevm-config/rhevm-config.properties",
                        r"Password.type=(.*)",
                        r'Password.type=********')
