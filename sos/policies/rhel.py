# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import RedHatPlugin, RHELPlugin
from sos.policies import RedHatPolicy
from sos import _sos as _
from sos.options import SoSOptions

OS_RELEASE = "/etc/os-release"

class RHELPolicy(RedHatPolicy):
    distro = RHEL_RELEASE_STR
    vendor = "Red Hat"
    vendor_url = "https://access.redhat.com/support/"
    msg = _("""\
This command will collect diagnostic and configuration \
information from this %(distro)s system and installed \
applications.

An archive containing the collected information will be \
generated in %(tmpdir)s and may be provided to a %(vendor)s \
support representative.
""" + disclaimer_text + "%(vendor_text)s\n")
    _upload_url = RH_FTP_HOST
    _upload_user = 'anonymous'
    _upload_directory = '/incoming'

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super(RHELPolicy, self).__init__(sysroot=sysroot, init=init,
                                         probe_runtime=probe_runtime,
                                         remote_exec=remote_exec)
        self.register_presets(rhel_presets)

    def prompt_for_upload_user(self):
        if self.commons['cmdlineopts'].upload_user:
            return
        # Not using the default, so don't call this prompt for RHCP
        if self.commons['cmdlineopts'].upload_url:
            super(RHELPolicy, self).prompt_for_upload_user()
            return
        if self.case_id:
            self.upload_user = input(_(
                "Enter your Red Hat Customer Portal username (empty to use "
                "public dropbox): ")
            )

    def get_upload_url(self):
        if self.commons['cmdlineopts'].upload_url:
            return self.commons['cmdlineopts'].upload_url
        if (not self.case_id or not self.upload_user or not
                self.upload_password):
            # Cannot use the RHCP. Use anonymous dropbox
            self.upload_user = self._upload_user
            self.upload_directory = self._upload_directory
            self.upload_password = None
            return RH_FTP_HOST
        else:
            rh_case_api = "/hydra/rest/cases/%s/attachments"
            return RH_API_HOST + rh_case_api % self.case_id

    def _get_upload_headers(self):
        if self.get_upload_url().startswith(RH_API_HOST):
            return {'isPrivate': 'false', 'cache-control': 'no-cache'}
        return {}

    def get_upload_url_string(self):
        if self.get_upload_url().startswith(RH_API_HOST):
            return "Red Hat Customer Portal"
        return self.upload_url or RH_FTP_HOST

    def get_upload_user(self):
        # if this is anything other than dropbox, annonymous won't work
        if self.upload_url != RH_FTP_HOST:
            return self.upload_user
        return self._upload_user

    def dist_version(self):
        try:
            rr = self.package_manager.all_pkgs_by_name_regex("redhat-release*")
            pkgname = self.pkgs[rr[0]]["version"]
            if pkgname[0] == "4":
                return 4
            elif pkgname[0] in ["5Server", "5Client"]:
                return 5
            elif pkgname[0] == "6":
                return 6
            elif pkgname[0] == "7":
                return 7
            elif pkgname[0] == "8":
                return 8
        except Exception:
            pass
        return False

    def probe_preset(self):
        # Emergency or rescue mode?
        for target in ["rescue", "emergency"]:
            if self.init_system.is_running("%s.target" % target):
                return self.find_preset(CB)
        # Package based checks
        if self.pkg_by_name("satellite-common") is not None:
            return self.find_preset(RH_SATELLITE)
        if self.pkg_by_name("rhosp-release") is not None:
            return self.find_preset(RHOSP)
        if self.pkg_by_name("cfme") is not None:
            return self.find_preset(RH_CFME)
        if self.pkg_by_name("ovirt-engine") is not None or \
                self.pkg_by_name("vdsm") is not None:
            return self.find_preset(RHV)

        # Vanilla RHEL is default
        return self.find_preset(RHEL)
