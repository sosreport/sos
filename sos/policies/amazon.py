# Copyright (C) Red Hat, Inc. 2019

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

# This enables the use of with syntax in python 2.5 (e.g. jython)
from __future__ import print_function

from sos.policies.redhat import RedHatPolicy, OS_RELEASE


class AmazonPolicy(RedHatPolicy):

    distro = "Amazon Linux"
    vendor = "Amazon"
    vendor_url = "https://aws.amazon.com"

    def __init__(self, sysroot=None):
        super(AmazonPolicy, self).__init__(sysroot=sysroot)

    @classmethod
    def check(cls):
        with open(OS_RELEASE, 'r') as f:
            for line in f:
                if line.startswith('NAME'):
                    if 'Amazon Linux' in line:
                        return True
        return False

# vim: set et ts=4 sw=4 :
