# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Postfix(Plugin):

    short_desc = 'Postfix smtp server'
    plugin_name = "postfix"
    profiles = ('mail', 'services')

    packages = ('postfix',)

    def forbidden_ssl_keys_files(self):
        # list of attributes defining a location of a SSL key file
        # we must forbid from collection
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
        fp = []
        try:
            with open(self.path_join('/etc/postfix/main.cf'), 'r') as cffile:
                for line in cffile.readlines():
                    # ignore comments and take the first word after '='
                    if line.startswith('#'):
                        continue
                    words = line.split('=')
                    if words[0].strip() in forbid_attributes:
                        fp.append(words[1].split()[0])
        finally:
            return fp

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


class RedHatPostfix(Postfix, RedHatPlugin):

    files = ('/etc/rc.d/init.d/postfix',)
    packages = ('postfix',)

    def setup(self):
        super(RedHatPostfix, self).setup()
        self.add_copy_spec("/etc/mail")


class DebianPostfix(Postfix, DebianPlugin, UbuntuPlugin):

    packages = ('postfix',)

    def setup(self):
        super(DebianPostfix, self).setup()

# vim: set et ts=4 sw=4 :
