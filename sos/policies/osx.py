from sos.policies import Policy
from sos.utilities import shell_out


class OSXPolicy(Policy):

    distro = "Mac OS X"

    @classmethod
    def check(cls, remote=None):

        if remote:
            return cls.distro in remote.read_file('/etc/os-release')

        try:
            return "Mac OS X" in shell_out("sw_vers")
        except Exception:
            return False

# vim: set et ts=4 sw=4 :
