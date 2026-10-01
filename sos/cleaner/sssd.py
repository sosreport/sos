"""Exact SSSD KCM rotated-log omission policy."""

import datetime
import re

from sos.cleaner.corosync import CorosyncLog, CorosyncLogError


class SssdLog(CorosyncLog):
    _path = re.compile(
        r'var/log/sssd/sssd_kcm\.log-([0-9]{4})([0-9]{2})([0-9]{2})\.gz\Z')

    @classmethod
    def _path_date(cls, parts):
        if len(parts) != 4 or parts[:3] != ('var', 'log', 'sssd'):
            return None
        match = cls._path.fullmatch('/'.join(parts))
        if not match:
            return None
        try:
            return datetime.date(*(int(value) for value in match.groups()))
        except ValueError:
            return None

    @classmethod
    def classify(cls, source, compressed_size):
        try:
            payload = cls.decode(source, compressed_size)
            payload.decode('utf-8')
        except (CorosyncLogError, UnicodeError):
            return 'reject'
        return 'omit'
