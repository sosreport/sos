# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.policies.distros.redhat import RedHatPolicy


class KylinPolicy(RedHatPolicy):
    vendor = "Kylin"
    vendor_urls = [('Distribution Website', 'https://www.kylinos.cn/')]
    os_release_file = '/etc/kylin-release'
    os_release_name = 'Kylin Linux Advanced Server'

# vim: set et ts=4 sw=4 :
