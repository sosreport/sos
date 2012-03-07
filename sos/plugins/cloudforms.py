import sos.plugintools
import os

class cloudforms(sos.plugintools.PluginBase):
    """CloudForms related information
    """

    def defaultenabled(self):
        return True

    def checkenabled(self):
        self.packages = ["katello", "katello-common",
                        "katello-headpin", "aeolus-conductor"]
        self.files = ["/usr/share/katello/script/katello-debug",
                        "/usr/bin/aeolus-debug"]
        return sos.plugintools.PluginBase.checkenabled(self)

    def setup(self):
        katello_debug = "/usr/share/katello/script/katello-debug"
        aeolus_debug = "/usr/bin/aeolus-debug"
        if os.path.isfile(katello_debug):
            katello_debug_path = os.path.join(self.cInfo['dstroot'],"katello-debug")
            self.collectExtOutput("%s --notar -d %s" % (katello_debug, katello_debug_path))
        if os.path.isfile(aeolus_debug):
            aeolus_debug_path = os.path.join(self.cInfo['dstroot'],"aeolus-debug")
            self.collectExtOutput("%s --notar -d %s" % (aeolus_debug, aeolus_debug_path))

