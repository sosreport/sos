# Copyright Red Hat 2020, Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


class InvalidPasswordException(Exception):
    """Raised when the provided password is rejected by the remote host"""

    def __init__(self):
        message = 'Invalid password provided'
        super().__init__(message)


class TimeoutPasswordAuthException(Exception):
    """Raised when a timeout is hit waiting for an auth reply using a password
    """

    def __init__(self):
        message = 'Timeout hit while waiting for password validation'
        super().__init__(message)


class PasswordRequestException(Exception):
    """Raised when the remote host requests a password that was not anticipated
    """

    def __init__(self):
        message = 'Host requested password, but none provided'
        super().__init__(message)


class AuthPermissionDeniedException(Exception):
    """Raised when authentication attempts return a permission error"""

    def __init__(self):
        message = 'Permission denied while trying to authenticate'
        super().__init__(message)


class ConnectionException(Exception):
    """Raised when an attempt to connect fails"""

    def __init__(self, address='', port=''):
        message = (f"Could not connect to host {address} on specified port "
                   f"{port}")
        super().__init__(message)


class CommandTimeoutException(Exception):
    """Raised when a timeout expires"""

    def __init__(self, command=None):
        message = 'Timeout expired'
        if command:
            message += f" executing {command}"
        super().__init__(message)


class ConnectionTimeoutException(Exception):
    """Raised when a timeout expires while trying to connect to the host"""

    def __init__(self):
        message = 'Timeout expires while trying to connect'
        super().__init__(message)


class ControlSocketMissingException(Exception):
    """Raised when the SSH control socket is missing"""

    def __init__(self, path=''):
        message = f"SSH control socket {path} does not exist"
        super().__init__(message)


class ControlPersistUnsupportedException(Exception):
    """Raised when SSH ControlPersist is unsupported locally"""

    def __init__(self):
        message = 'ControlPersist unsupported by local SSH installation'
        super().__init__(message)


class UnsupportedHostException(Exception):
    """Raised when the host type is unsupported or undetermined"""

    def __init__(self):
        message = 'Host did not match any supported distributions'
        super().__init__(message)


class InvalidTransportException(Exception):
    """Raised when a transport is requested but it does not exist or is
    not supported locally"""

    def __init__(self, transport=None):
        message = ("Connection failed: unknown or unsupported transport "
                   f"{transport if transport else ''}")
        super().__init__(message)


class SaltStackMasterUnsupportedException(Exception):
    """Raised when SaltStack Master is unsupported locally"""

    def __init__(self):
        message = 'Master unsupported by local SaltStack installation'
        super().__init__(message)


class JujuNotInstalledException(Exception):
    """Raised when juju is not installed locally"""

    def __init__(self):
        message = (
            'Juju is not installed, '
            'please ensure you have installed juju.'
        )
        super().__init__(message)


__all__ = [
    'AuthPermissionDeniedException',
    'CommandTimeoutException',
    'ConnectionException',
    'ConnectionTimeoutException',
    'ControlPersistUnsupportedException',
    'ControlSocketMissingException',
    'InvalidPasswordException',
    'PasswordRequestException',
    'SaltStackMasterUnsupportedException',
    'TimeoutPasswordAuthException',
    'UnsupportedHostException',
    'InvalidTransportException',
    'JujuNotInstalledException'
]
