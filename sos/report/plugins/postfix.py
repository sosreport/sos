# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re
from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Postfix(Plugin):

    short_desc = 'Postfix smtp server'
    plugin_name = "postfix"
    profiles = ('mail', 'services')

    packages = ('postfix',)

    def forbidden_ssl_keys_files(self):
        """ list of attributes defining a location of a SSL key file
        we must forbid from collection
        """
        forbid_attributes = [
            "lmtp_tls_dkey_file",
            "lmtp_tls_eckey_file",
            "lmtp_tls_key_file",
            "smtp_tls_dkey_file",
            "smtp_tls_eckey_file",
            "smtp_tls_key_file",
            "smtpd_tls_dkey_file",
            "smtpd_tls_eckey_file",
            "smtpd_tls_key_file",
            "tls_legacy_public_key_fingerprints",
            "tlsproxy_tls_dkey_file",
            "tlsproxy_tls_eckey_file",
            "tlsproxy_tls_key_file",
            "smtpd_tls_dh1024_param_file",
            "smtpd_tls_dh512_param_file",
            "tlsproxy_tls_dh1024_param_file",
            "tlsproxy_tls_dh512_param_file",
        ]
        fpaths = []
        try:
            with open(self.path_join('/etc/postfix/main.cf'), 'r',
                      encoding='UTF-8') as cffile:
                for line in cffile.readlines():
                    # ignore comments and take the first word after '='
                    if line.startswith('#'):
                        continue
                    words = line.split('=')
                    if words[0].strip() in forbid_attributes:
                        fpaths.append(words[1].split()[0])
        except Exception:  # pylint: disable=broad-except
            pass
        return fpaths

    def forbidden_password_files(self):
        """ Get the list of password to exclude """
        forbid_attributes = (
            "lmtp_sasl_password_maps",
            "smtp_sasl_password_maps",
            "postscreen_dnsbl_reply_map",
            "smtp_sasl_auth_cache_name",
        )
        fpaths = []
        prefix = 'hash:'
        option_format = re.compile(r"^(.*)=(.*)")
        try:
            with open(self.path_join('/etc/postfix/main.cf'), 'r',
                      encoding='UTF-8') as cffile:
                for line in cffile.readlines():
                    # ignore comment and check option format
                    line = re.sub('#.*', '', line)
                    option = option_format.match(line)
                    if option is None:
                        continue

                    # sieving
                    attribute = option.group(1).strip()
                    if attribute in forbid_attributes:
                        filepath = option.group(2).strip()
                        # ignore no filepath
                        if len(filepath) == 0:
                            continue
                        # remove prefix
                        if filepath.startswith(prefix):
                            filepath = filepath[len(prefix):]
                        fpaths.append(filepath)
        except Exception as err:  # pylint: disable=broad-except
            # error log
            msg = f"Error parsing main.cf: {err.args[0]}"
            self._log_error(msg)
        return fpaths

    def setup(self):
        self.add_copy_spec([
            "/etc/postfix/",
        ])
        self.add_cmd_output([
            'postconf',
            'mailq'
        ])
        # don't collect SSL keys or certs or ssl dir
        self.add_forbidden_path([
            "/etc/postfix/*.key",
            "/etc/postfix/*.crt",
            "/etc/postfix/ssl/",
        ])
        self.add_forbidden_path(self.forbidden_ssl_keys_files())
        self.add_forbidden_path(self.forbidden_password_files())


class RedHatPostfix(Postfix, RedHatPlugin):

    files = ('/etc/rc.d/init.d/postfix',)
    packages = ('postfix',)

    def setup(self):
        super().setup()
        self.add_copy_spec("/etc/mail")


class DebianPostfix(Postfix, DebianPlugin, UbuntuPlugin):

    packages = ('postfix',)


# vim: set et ts=4 sw=4 :
