# This file is part of the sos project: https://github.com/sosreport/sos

"""Private, deterministic publication of a mapping manifest."""

import ctypes
import errno
import json
import os
import re
import tempfile


class MappingManifestWriterError(Exception):
    """A fail-closed mapping publication error."""

    def __init__(self):
        super().__init__('mapping manifest publication failed')


class MappingManifestWriter:
    """Serialize one manifest to a mode-0600, no-replace JSON file."""

    _generated_username = re.compile(r'obfuscateduser\d+$', re.I)
    _generated_email = re.compile(
        r'user\d+@obfuscateddomain\d+\.example$', re.I)

    def __init__(self, manifest, destination):
        self.manifest = manifest
        self.destination = os.path.abspath(destination)
        self._summary = {
            'mapping_written': False,
            'mapping_entries': manifest.summary(),
        }

    def summary(self):
        return {
            'mapping_written': self._summary['mapping_written'],
            'mapping_entries': dict(self._summary['mapping_entries']),
        }

    def write(self):
        temporary = None
        try:
            payload = self._payload()
            parent = os.path.dirname(self.destination)
            if not os.path.isdir(parent) or os.path.lexists(self.destination):
                self._fail()
            fd, temporary = tempfile.mkstemp(
                prefix='.sos-mapping-', suffix='.tmp', dir=parent)
            os.fchmod(fd, 0o600)
            encoded = (json.dumps(payload, ensure_ascii=True, indent=2) +
                       '\n').encode('utf-8')
            with os.fdopen(fd, 'wb', closefd=True) as stream:
                fd = None
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            self._validate_file(temporary)
            self._publish_noreplace(temporary)
            temporary = None
            self._summary['mapping_written'] = True
            return self.destination
        except MappingManifestWriterError:
            raise
        except Exception:
            self._fail()
        finally:
            if temporary is not None:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass

    def _fail(self):
        raise MappingManifestWriterError()

    def _payload(self):
        raw = self.manifest.raw_mappings()
        namespaces = tuple(self.manifest.namespaces)
        if raw.get('schema_version') != self.manifest.schema_version or \
                set(raw) != {'schema_version', *namespaces}:
            self._fail()
        aliases = set()
        payload = {'schema_version': self.manifest.schema_version}
        for namespace in namespaces:
            values = raw.get(namespace)
            if not isinstance(values, dict):
                self._fail()
            normalized = {}
            for original, pseudonym in sorted(values.items()):
                if (not isinstance(original, str) or
                        not isinstance(pseudonym, str) or not original or
                        original == pseudonym or
                        self._generated_key(original)):
                    self._fail()
                normalized[original] = pseudonym
                aliases.add(pseudonym)
            payload[namespace] = normalized
        for values in payload.values():
            if not isinstance(values, dict):
                continue
            if any(key in aliases for key in values):
                self._fail()
        return payload

    @classmethod
    def _generated_key(cls, value):
        return (cls._generated_username.fullmatch(value) is not None or
                cls._generated_email.fullmatch(value) is not None)

    def _validate_file(self, path):
        try:
            if os.stat(path, follow_symlinks=False).st_mode & 0o777 != 0o600:
                self._fail()
            with open(path, 'r', encoding='utf-8') as stream:
                data = json.load(stream)
            if data != self._payload():
                self._fail()
            if set(data) != {'schema_version', *self.manifest.namespaces}:
                self._fail()
            if not isinstance(data['schema_version'], int) or \
                    isinstance(data['schema_version'], bool):
                self._fail()
        except MappingManifestWriterError:
            raise
        except Exception:
            self._fail()

    def _publish_noreplace(self, temporary):
        if os.name != 'posix':
            raise OSError(errno.ENOTSUP, 'atomic no-replace unavailable')
        try:
            libc = ctypes.CDLL(None, use_errno=True)
            renameat2 = libc.renameat2
        except (AttributeError, OSError):
            raise OSError(errno.ENOTSUP,
                          'atomic no-replace unavailable') from None
        renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p,
                              ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        renameat2.restype = ctypes.c_int
        if renameat2(-100, os.fsencode(temporary), -100,
                     os.fsencode(self.destination), 1) != 0:
            error = ctypes.get_errno()
            raise OSError(error, 'atomic no-replace publication failed')
