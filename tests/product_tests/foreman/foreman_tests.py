# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from sos_tests import StageOneReportTest, redhat_only, ubuntu_only

# known values in our CI test images
FOREMAN_DB_PASSWORD = r'S0Sdb=p@ssw0rd!'
FOREMAN_ADMIN_PASSWORD = r'S0S@dmin\\p@ssw0rd!'
CANDLEPIN_DB_PASSWORD = r'S0SKatello%sp@ssw0rd!'

FOREMAN_PASSWORDS = [FOREMAN_DB_PASSWORD, FOREMAN_ADMIN_PASSWORD, CANDLEPIN_DB_PASSWORD]


class ForemanBasicTest(StageOneReportTest):
    """Ensure that a basic execution runs as expected with all TFM related
    plugins. For the Red Hat tests, it assumes Foreman has been deployed on a
    Katello system. On Debian systems, these tests are skipped.

    :avocado: tags=foreman
    """

    sos_cmd = '-v'

    def test_tfm_plugins_ran(self):
        self.assertPluginIncluded([
            'apache',
            'foreman',
            'postgresql',
            'puppet',
            'ruby'
        ])

    @redhat_only
    def test_candlepin_plugin_ran(self):
        self.assertPluginIncluded('candlepin')

    def test_foreman_keys_skipped(self):
        self.assertFileGlobNotInArchive("/etc/foreman*/*key.pem")

    def test_foreman_database_sizes_collected(self):
        self.assertFileCollected('sos_commands/foreman/foreman_db_tables_sizes')

    def test_foreman_installer_dirs_collected(self):
        self.assertFileGlobInArchive("/etc/foreman-installer/*")
        self.assertFileGlobInArchive("/var/log/foreman-installer/*")

    def test_foreman_production_log_collected(self):
        self.assertFileCollected('/var/log/foreman/production.log')

    def test_foreman_database_dump_collected(self):
        self.assertFileCollected('sos_commands/foreman/foreman_settings_table')

    def test_foreman_tasks_csv_collected(self):
        self.assertFileCollected('sos_commands/foreman/foreman_tasks_tasks')

    def test_proxyfeatures_not_collected(self):
        self.assertFileGlobNotInArchive("sos_commands/foreman/smart_proxies_features/*")

    def test_foreman_config_postproc_worked(self):
        self.assertFileNotHasContent('/etc/foreman/database.yml', FOREMAN_DB_PASSWORD)

    def test_foreman_password_postproc_worked(self):
        for _check in ['/var/log/foreman-installer/foreman.log', '/etc/foreman-installer/scenarios.d/foreman-answers.yaml']:
            for passwd in FOREMAN_PASSWORDS:
                self.assertFileNotHasContent(_check, passwd)

    @redhat_only
    def test_candlepin_table_sizes_collected(self):
        self.assertFileCollected('sos_commands/candlepin/candlepin_db_tables_sizes')

    @redhat_only
    def test_katello_password_postproc_worked(self):
        for _check in ['/var/log/foreman-installer/katello.log', '/etc/foreman-installer/scenarios.d/katello-answers.yaml']:
            for passwd in FOREMAN_PASSWORDS:
                self.assertFileNotHasContent(_check, passwd)

    @redhat_only
    def test_foreman_httpd_collected(self):
        self.assertFileGlobInArchive("/var/log/httpd*/foreman-ssl_*_ssl*log*")

    @ubuntu_only
    def test_foreman_apache_collected(self):
        self.assertFileGlobInArchive("/var/log/apache2/foreman-ssl_*_ssl*log*")

    def test_ruby_gems_collected(self):
        self.assertFileCollected('sos_commands/ruby/gem_list')


class ForemanWithOptionsTest(StageOneReportTest):
    """Enable Foreman/Katello/Candlepin specific options and ensure they are
    working

    :avocado: tags=foreman
    """

    sos_cmd = '-v -k foreman.proxyfeatures=on'

    @redhat_only
    def test_proxyfeatures_collected(self):
        self.assertFileGlobInArchive("sos_commands/foreman/smart_proxies_features/*")
