# Copyright (C) 2026 Canonical Ltd., Arif Ali <arif-ali@ubuntu.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.options import SoSOptions
from sos.presets import PresetDefaults


UBUNTU = "ubuntu"
UBUNTU_DESC = "Ubuntu"

SUNBEAM = "sunbeam"
SUNBEAM_DESC = "Canonical OpenStack"
SUNBEAM_OPTS = SoSOptions(
    all_logs=True,
    plugopts=[
        'sunbeam.juju-allow-login = True',
        'kubernetes.all = True',
        'kubernetes.describe = True',
        'kubernetes.kubelogs = True',
        'kubernetes.podlogs = True',
    ])

UBUNTU_PRESETS = {
    SUNBEAM: PresetDefaults(name=SUNBEAM, desc=SUNBEAM_DESC,
                            opts=SUNBEAM_OPTS),
    UBUNTU: PresetDefaults(name=UBUNTU, desc=UBUNTU_DESC),
}

# vim: set et ts=4 sw=4 :
