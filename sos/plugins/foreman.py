import sos.plugintools
import os

class foreman(sos.plugintools.PluginBase):
    """Foreman project related information
    """

    def defaultenabled(self):
        return True

    def checkenabled(self):
        self.packages = ["foreman"]
        self.files = ["/usr/sbin/foreman-debug"]
        return sos.plugintools.PluginBase.checkenabled(self)

    def setup(self):
        foreman_debug = "/usr/sbin/foreman-debug"
        if os.path.isfile(foreman_debug):
            foreman_debug_path = os.path.join(self.cInfo['dstroot'],"foreman-debug")
            self.collectExtOutput("%s -a -d %s" % (foreman_debug, foreman_debug_path))
