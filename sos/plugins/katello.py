import sos.plugintools
import os

class katello(sos.plugintools.PluginBase):
    """Katello project related information
    """

    def defaultenabled(self):
        return True

    def checkenabled(self):
        self.packages = ["katello", "katello-common", "katello-headpin"]
        self.files = ["/usr/bin/katello-debug"]
        return sos.plugintools.PluginBase.checkenabled(self)

    def setup(self):
        katello_debug = "/usr/bin/katello-debug"
        if os.path.isfile(katello_debug):
            katello_debug_path = os.path.join(self.cInfo['dstroot'],"katello-debug")
            self.collectExtOutput("%s --notar -d %s" % (katello_debug, katello_debug_path))
