from sos.plugins import Plugin, SCLPlugin


class SCLNpm(Plugin, SCLPlugin):
    """
    Get info about global modules from SCL collections that contain "npm"
    """

    requires_root = False
    packages = ("%(scl_name)s-npm",)
    profiles = ('system',)

    def setup(self):
        for scl in self.scls_matched:
            self.add_cmd_output_scl(scl, "npm ls -g --json")
