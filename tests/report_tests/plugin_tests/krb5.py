# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from sos_tests import StageTwoReportTest, redhat_only, ubuntu_only


class Krb5PluginTest(StageTwoReportTest):
    """Ensure that the krb5 plugin activates for the distros that we support it
    on.

    See https://github.com/sosreport/sos/issues/3041

    :avocado: tags=stageone
    """

    sos_cmd = '-o krb5'
    packages = {
        'rhel': ['krb5-libs', 'krb5-server'],
        'Ubuntu': ['krb5-user', 'krb5-kdc']
    }

    def test_plugin_ran(self):
        self.assertPluginIncluded('krb5')

    def test_conf_collected(self):
        self.assertFileCollected('/etc/krb5.conf')

    @ubuntu_only
    def test_ubuntu_kdcdir_collected(self):
        self.assertFileGlobInArchive('/var/lib/krb5kdc/*')

    @redhat_only
    def test_redhat_kdcdir_collected(self):
        self.assertFileGlobInArchive('/var/kerberos/krb5kdc/*')
