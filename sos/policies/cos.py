from sos.plugins import CosPlugin
from sos.policies import LinuxPolicy

import os


class CosPolicy(LinuxPolicy):
    distro = "Container-Optimized OS"
    vendor = "Google Cloud Platform"
    vendor_url = "https://cloud.google.com/container-optimized-os/"
    valid_subclasses = [CosPlugin]
    PATH = "/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin"

    @classmethod
    def check(cls):
        try:
            with open('/etc/os-release', 'r') as fp:
                os_release = dict(line.strip().split('=') for line in fp)
                id = os_release.get('ID')
                return id == 'cos'
        except IOError:
            return False

# vim: set et ts=4 sw=4 :
