from sos.plugins import UbuntuPlugin, IndependentPlugin
from sos.policies import PackageManager, Policy
from sos.utilities import shell_out

class UbuntuPackageManager(PackageManager):

    def _get_deb_list(self):
        pkg_list = shell_out(["dpkg-query",
            "-W",
            "-f=",
        "${Package}|${Version}\\n"]).splitlines()
        self._debs = {}
        for pkg in pkg_list:
            name, version = pkg.split("|")
            self._debs[name] = {
                    'name': name,
                    'version': version
                    }

    def allPkgsByName(self, name):
        return fnmatch.filter(self.allPkgs().keys(), name)

    def allPkgsByNameRegex(self, regex_name, flags=None):
        reg = re.compile(regex_name, flags)
        return [pkg for pkg in self.allPkgs().keys() if reg.match(pkg)]

    def pkgByName(self, name):
        try:
            self.AllPkgsByName(name)[-1]
        except Exception:
            return None

    def allPkgs(self):
        if not self._rpms:
            self._rpms = self._get_deb_list()
        return self._rpms

    def pkgNVRA(self, pkg):
        fields = pkg.split("-")
        version, release, arch = fields[-3:]
        name = "-".join(fields[:-3])
        return (name, version, release, arch)
        
class UbuntuPolicy(Policy):
    def __init__(self):
        super(UbuntuPolicy, self).__init__()
        self.reportName = ""
        self.ticketNumber = ""
        self.package_manager = UbuntuPackageManager()

   def validatePlugin(self, plugin_class):
        "Checks that the plugin will execute given the environment"
        return issubclass(plugin_class, UbuntuPlugin) or issubclass(plugin_class, IndependentPlugin)

    @classmethod
    def check(self):
        """This method checks to see if we are running on Ubuntu.
           It returns True or False."""
        if os.path.isfile('/etc/lsb-release'):
            try:
                fp = open('/etc/lsb-release', 'r')
                if "Ubuntu" in fp.read():
                    fp.close()
                    return True
            except:
                return False
        return False
            
