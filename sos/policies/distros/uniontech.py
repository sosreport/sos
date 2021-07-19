from __future__ import print_function

from sos.plugins import RedHatPlugin
from sos.policies.redhat import RedHatPolicy, OS_RELEASE
import os

class UnionTechPolicy(RedHatPolicy):

    distro = "UnionTech"
    vendor = "the UnionTech Project"
    vendor_url = "https://www.chinauos.com/"

    def __init__(self, sysroot=None):
        super(UnionTechPolicy, self).__init__(sysroot=sysroot)

    @classmethod
    def check(cls):
        if not os.path.exists(OS_RELEASE):
            return False

        with open(OS_RELEASE, 'r') as f:
            for line in f:
                if line.startswith('NAME'):
                    if 'UnionTech' in line:
                        return True
        return False



