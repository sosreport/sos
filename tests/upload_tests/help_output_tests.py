# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageOneOutputTest


# A path that is guaranteed not to exist. Commands that need a FILE
# positional use this so that SoSUpload.execute() reaches the intro banner
# and target selection, then stops at the os.stat() call without ever
# attempting a real upload.
MISSING_ARCHIVE = '/nonexistent/sos-upload-stageone.tar.xz'

# Every flag documented under the 'Upload Options' group by
# SoSUpload.add_parser_options().
UPLOAD_OPTIONS = [
    '--preauth',
    '--case-id',
    '--upload-url',
    '--upload-user',
    '--upload-pass',
    '--upload-directory',
    '--upload-s3-endpoint',
    '--upload-s3-region',
    '--upload-s3-bucket',
    '--upload-s3-access-key',
    '--upload-s3-secret-key',
    '--upload-s3-object-prefix',
    '--upload-method',
    '--upload-protocol',
    '--upload-no-ssl-verify',
    '--upload-target',
    '--upload-threads',
]


class UploadHelpOutputTest(StageOneOutputTest):
    """S1-01 - Ensure `upload --help` documents the Upload Options group
    and every flag the component defines

    :avocado: tags=stageone
    """

    sos_cmd = 'upload --help'

    def test_usage_line_shown(self):
        self.assertOutputContains(r'usage: sos upload FILE \[options\]')

    def test_upload_options_group_shown(self):
        self.assertOutputContains('Upload Options:')
        self.assertOutputContains(
            'These options control how upload manages files')

    def test_file_positional_documented(self):
        self.assertOutputContains('The file or archive to upload')

    def test_all_upload_flags_documented(self):
        for option in UPLOAD_OPTIONS:
            self.assertOutputContains(option)

    def test_option_choices_documented(self):
        self.assertOutputContains(r'\{auto,put,post\}')
        self.assertOutputContains(r'\{auto,https,ftp,sftp,s3\}')
        self.assertOutputContains(r'\{redhat,canonical,generic,local\}')


class UploadInvalidMethodTest(StageOneOutputTest):
    """S1-02 - An unrecognised --upload-method is rejected by argparse

    :avocado: tags=stageone
    """

    _exception_expected = True
    sos_cmd = f'upload --upload-method bogus {MISSING_ARCHIVE}'

    def test_invalid_choice_reported(self):
        self.assertOutputContains(
            "argument --upload-method: invalid choice: 'bogus'")


class UploadInvalidProtocolTest(StageOneOutputTest):
    """S1-03 - An unrecognised --upload-protocol is rejected by argparse

    :avocado: tags=stageone
    """

    _exception_expected = True
    sos_cmd = f'upload --upload-protocol bogus {MISSING_ARCHIVE}'

    def test_invalid_choice_reported(self):
        self.assertOutputContains(
            "argument --upload-protocol: invalid choice: 'bogus'")


class UploadInvalidTargetTest(StageOneOutputTest):
    """S1-04 - An unrecognised --upload-target is rejected by argparse

    :avocado: tags=stageone
    """

    _exception_expected = True
    sos_cmd = f'upload --upload-target bogus {MISSING_ARCHIVE}'

    def test_invalid_choice_reported(self):
        self.assertOutputContains(
            "argument --upload-target: invalid choice: 'bogus'")


class UploadMissingFileTest(StageOneOutputTest):
    """S1-05 - Omitting the FILE positional is reported, with a non-zero
    exit

    Since --preauth was added the FILE positional is nargs='?', so
    argparse accepts its absence and SoSUpload.execute() performs the
    check instead. --batch is needed to get past the ENTER prompt.

    :avocado: tags=stageone
    """

    _exception_expected = True
    sos_cmd = 'upload --batch'

    def test_help_error_reported(self):
        # Overrides the inherited assertion, which requires empty stdout
        # and non-empty stderr. execute() reports this failure through
        # ui_log, which writes to stdout, so only the exit code and the
        # presence of output can be asserted here.
        self.assertTrue(self.cmd_output.exit_status != 0)
        assert self.cmd_output.stdout, "No stdout output generated"

    def test_missing_file_reported(self):
        self.assertOutputContains('No FILE provided to upload')

    def test_preauth_alternative_suggested(self):
        self.assertOutputContains(
            'use --preauth to only store an auth token')


class UploadIntroOutputTest(StageOneOutputTest):
    """S1-06 - The intro disclaimer and version banner are printed when
    running with --batch

    --batch suppresses the "Press ENTER to continue" prompt and the case id
    prompt, so the command runs unattended. The archive path does not exist,
    so execute() reports that it cannot upload the file and exits 0 without
    contacting any remote host.

    :avocado: tags=stageone
    """

    sos_cmd = f'upload --batch {MISSING_ARCHIVE}'

    def test_version_banner_shown(self):
        self.assertOutputContains(r'sos upload \(version')

    def test_disclaimer_shown(self):
        self.assertOutputContains(
            'This utility is used to upload files to a target location')
        self.assertOutputContains(
            'should be reviewed by the originating organization')
        self.assertOutputContains(
            'No configuration changes will be made to the system')

    def test_upload_target_reported(self):
        self.assertOutputContains('Upload target set to')

    def test_no_upload_attempted_for_missing_archive(self):
        self.assertOutputContains(f'Cannot upload {MISSING_ARCHIVE}')

# vim: set et ts=4 sw=4 :
