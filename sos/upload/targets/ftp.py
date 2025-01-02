# Copyright 2024, Jake Hunsaker <jacob.r.hunsaker@gmail.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import ftplib
import os
import socket


from sos.upload.targets import SoSUploadTarget
from sos.utilities import is_executable


class FtpUpload(SoSUploadTarget):
    """
    This upload target handles FTP and SFTP upload attempts to generic S/FTP
    destinations.
    """
    target_id = 'ftp'
    target_protocols = ['ftp', 'sftp']
    prompt_for_credentials = True

    def __init__(self, options, user=None, password=None, directory=None):
        super().__init__(options)
        self.user = user or self.opts.upload_user
        self.password = password or self.opts.upload_pass
        self.directory = directory or self.opts.upload_directory
        if url := self.opts.upload_url:
            self.proto, self.url = url.split('://')
        else:
            raise Exception(
                'No FTP address specified. Set one using the --upload-url '
                'option or in your configuration file'
            )

    def upload(self):
        if self.proto == 'ftp':
            self.upload_ftp()
        elif self.proto == 'sftp':

            self.upload_sftp()
        else:
            raise Exception(f"Unknown ftp protocol '{self.proto}' given")

    def upload_sftp(self):
        """Attempts to upload the archive to an SFTP location.

        Due to the lack of well maintained, secure, and generally widespread
        python libraries for SFTP, sos will shell-out to the system's local ssh
        installation in order to handle these uploads.

        Do not override this method with one that uses python-paramiko, as the
        upstream sos team will reject any PR that includes that dependency.
        """
        # if we somehow don't have sftp available locally, fail early
        if not is_executable('sftp'):
            raise Exception('SFTP is not locally supported')

        # soft dependency on python3-pexpect, which we need to use to control
        # sftp login since as of this writing we don't have a viable solution
        # via ssh python bindings commonly available among downstreams
        try:
            import pexpect
        except ImportError as err:
            raise Exception('SFTP upload requires python3-pexpect, which is '
                            'not currently installed') from err

        sftp_connected = False

        sftp_opts = ['-oStrictHostKeyChecking=no']
        if self.opts.upload_port:
            sftp_opts.append(f"-P {self.opts.upload_port}")

        sftp_cmd = f"sftp {' '.join(sftp_opts)} {self.user}@{self.url} "
        ret = pexpect.spawn(sftp_cmd, encoding='utf-8')
        sftp_expects = [
            'sftp>',
            'password:',
            'Connection refused',
            pexpect.TIMEOUT,
            pexpect.EOF
        ]

        idx = ret.expect(sftp_expects, timeout=15)

        if idx == 0:
            sftp_connected = True
        elif idx == 1:
            ret.sendline(self.password)
            pass_expects = [
                'sftp>',
                'Permission denied',
                pexpect.TIMEOUT,
                pexpect.EOF
            ]
            sftp_connected = ret.expect(pass_expects, timeout=10) == 0
            if not sftp_connected:
                ret.close()
                raise Exception(
                    f"Incorrect username or password for {self.url}"
                )
        elif idx == 2:
            raise Exception(f"Connection refused by {self.url}. "
                            f"Incorrect port?")
        elif idx == 3:
            raise Exception(f"Timeout hit trying to connect to {self.url}")
        elif idx == 4:
            raise Exception("Unexpected error trying to connect to sftp: "
                            f"{ret.before}")

        if not sftp_connected:
            ret.close()
            raise Exception("Unable to connect via SFTP to "
                            f"{self.url}")

        if self.directory:
            fname = os.path.join(self.directory, self.upload_file)
        else:
            fname = self.upload_file

        put_cmd = f"put {self.upload_file} {fname}"
        ret.sendline(put_cmd)

        put_expects = [
            '100%',
            pexpect.TIMEOUT,
            pexpect.EOF,
            'No such file or directory'
        ]

        put_success = ret.expect(put_expects, timeout=180)

        if put_success == 0:
            ret.sendline('bye')
            return True
        if put_success == 1:
            raise Exception("Timeout expired while uploading")
        if put_success == 2:
            raise Exception(f"Unknown error during upload: {ret.before}")
        if put_success == 3:
            raise Exception("Unable to write archive to destination")
        raise Exception(f"Unexpected response from server: {ret.before}")

    def upload_ftp(self):
        try:
            session = ftplib.FTP(self.url, self.user, self.password,
                                 timeout=15)

            if not session:
                raise Exception("connection failed, did you set a user and "
                                "password?")

            if self.directory:
                session.cwd(self.directory)
        except socket.timeout as err:
            raise Exception(
                f"timeout hit while connecting to {self.url}"
            ) from err
        except socket.gaierror as err:
            raise Exception(f"unable to connect to {self.url}") from err
        except ftplib.error_perm as err:
            errno = str(err).split()[0]
            if errno == '503':
                raise Exception(f"could not login as '{self.user}'") from err
            if errno == '530':
                raise Exception(
                    f"invalid password for user '{self.user}'"
                ) from err
            if errno == '550':
                raise Exception("could not set upload directory to "
                                f"{self.directory}") from err
            raise Exception(f"error trying to establish session: {str(err)}") \
                from err

        with open(self.upload_file, 'rb') as _arcfile:
            session.storbinary(
                f"STOR {self.upload_file.split('/')[-1]}", _arcfile
                )
        session.quit()
        return True
