# Copyright (C) 2020 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.options import SoSOptions
from sos.presets import PresetDefaults


RHEL_RELEASE_STR = "Red Hat Enterprise Linux"

_opts_verify = SoSOptions(verify=True)
_opts_all_logs = SoSOptions(all_logs=True)
_opts_all_logs_verify = SoSOptions(all_logs=True, verify=True)
_cb_profiles = ['boot', 'storage', 'system']
_cb_plugopts = ['boot.all-images=on', 'rpm.rpmva=on', 'rpm.rpmdb=on']


RHV = "rhv"
RHV_DESC = "Red Hat Virtualization"

RHEL = "rhel"
RHEL_DESC = RHEL_RELEASE_STR

RHOSP = "rhosp"
RHOSP_DESC = "Red Hat OpenStack Platform"
RHOSP_OPTS = SoSOptions(plugopts=[
                             'process.lsof=off',
                             'networking.ethtool_namespaces=False',
                             'networking.namespaces=200'])

RHOCP = "ocp"
RHOCP_DESC = "OpenShift Container Platform by Red Hat"
RHOCP_OPTS = SoSOptions(
    verify=True, skip_plugins=['cgroups'], container_runtime='crio',
    no_report=True, log_size=100,
    plugopts=[
        'crio.timeout=600',
        'networking.timeout=600',
        'networking.ethtool_namespaces=False',
        'networking.namespaces=200'
    ])

RH_CFME = "cfme"
RH_CFME_DESC = "Red Hat CloudForms"

RH_SATELLITE = "satellite"
RH_SATELLITE_DESC = "Red Hat Satellite"
SAT_OPTS = SoSOptions(log_size=100, plugopts=['apache.log=on'])

CB = "cantboot"
CB_DESC = "For use when normal system startup fails"
CB_OPTS = SoSOptions(
            verify=True, all_logs=True, profiles=_cb_profiles,
            plugopts=_cb_plugopts
          )
CB_NOTE = ("Data collection will be limited to a boot-affecting scope")

NOTE_SIZE = "This preset may increase report size"
NOTE_TIME = "This preset may increase report run time"
NOTE_SIZE_TIME = "This preset may increase report size and run time"

RHEL_PRESETS = {
    RHV: PresetDefaults(name=RHV, desc=RHV_DESC, note=NOTE_TIME,
                        opts=_opts_verify),
    RHEL: PresetDefaults(name=RHEL, desc=RHEL_DESC),
    RHOSP: PresetDefaults(name=RHOSP, desc=RHOSP_DESC, opts=RHOSP_OPTS),
    RHOCP: PresetDefaults(name=RHOCP, desc=RHOCP_DESC, note=NOTE_SIZE_TIME,
                          opts=RHOCP_OPTS),
    RH_CFME: PresetDefaults(name=RH_CFME, desc=RH_CFME_DESC, note=NOTE_TIME,
                            opts=_opts_verify),
    RH_SATELLITE: PresetDefaults(name=RH_SATELLITE, desc=RH_SATELLITE_DESC,
                                 note=NOTE_TIME, opts=SAT_OPTS),
    CB: PresetDefaults(name=CB, desc=CB_DESC, note=CB_NOTE, opts=CB_OPTS)
}


ATOMIC = "atomic"
ATOMIC_RELEASE_STR = "Atomic"
ATOMIC_DESC = "Red Hat Enterprise Linux Atomic Host"

ATOMIC_PRESETS = {
    ATOMIC: PresetDefaults(name=ATOMIC, desc=ATOMIC_DESC, note=NOTE_TIME,
                           opts=_opts_verify)
}


# vim: set et ts=4 sw=4 :
