# Copyright (C) 2012 Red Hat, Inc.,
#   Jesse Jaggars <jjaggars@redhat.com>
#   Bryn M. Reeves <bmr@redhat.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import os
import re
from importlib import import_module
from io import BytesIO
from pathlib import Path


def _decompress_xz(archive, compression, content):
    result = bytearray()
    while content:
        decoder = compression.LZMADecompressor(
            format=compression.FORMAT_XZ, memlimit=archive._lzma_memory_limit)
        while True:
            result.extend(decoder.decompress(
                content, max_length=archive._substitution_limit + 1 -
                len(result)))
            if len(result) > archive._substitution_limit:
                raise OSError("Decompressed substitution limit exceeded")
            if decoder.eof:
                content = decoder.unused_data
                # XZ permits stream padding in multiples of four bytes.
                padding = len(content) - len(content.lstrip(b'\0'))
                if padding % 4:
                    raise OSError("Invalid XZ stream padding")
                content = content[padding:]
                break
            if decoder.needs_input:
                raise EOFError("Incomplete XZ stream")
            content = b''
    return bytes(result)


def substitute_file(archive, path, regexp, subst):
    common_flags = re.IGNORECASE | re.MULTILINE
    if hasattr(regexp, "pattern"):
        pattern = regexp.pattern
        flags = regexp.flags | common_flags
    else:
        pattern = regexp
        flags = common_flags

    with archive.open_file(path, binary=True) as readable:
        content = readable.read()
    compression = None
    for magic, module_name in ((b'\x1f\x8b', 'gzip'),
                               (b'BZh', 'bz2'),
                               (b'\xfd7zXZ\x00', 'lzma')):
        if module_name == 'bz2':
            # A text line beginning BZh is not a bzip2 stream header.
            matched = (content.startswith(magic) and
                       b'1' <= content[3:4] <= b'9' and
                       content[4:10] in (b'1AY&SY', b'\x17rE8P\x90'))
        else:
            matched = content.startswith(magic)
        if matched:
            decompression_error = OSError
            try:
                compression = import_module(module_name)
                if module_name == 'gzip':
                    decompression_error = compression.zlib.error
                elif module_name == 'lzma':
                    decompression_error = compression.LZMAError
                if module_name == 'lzma':
                    content = _decompress_xz(archive, compression, content)
                else:
                    with compression.open(BytesIO(content), 'rb') as src:
                        content = src.read(archive._substitution_limit + 1)
                if len(content) > archive._substitution_limit:
                    raise OSError("Decompressed substitution "
                                  "limit exceeded")
            except (ImportError, OSError, EOFError, ValueError,
                    decompression_error) as err:
                archive._failed_substitution = True
                raise OSError(
                    f"Cannot decompress archived file '{path}'") from err
            break
    if not isinstance(content, str):
        content = content.decode('utf8', 'ignore')
    result, replacements = re.subn(pattern, subst, content,
                                   flags=flags)
    if replacements:
        if compression:
            archive.add_binary(compression.compress(result.encode('utf-8')),
                               path, force=True)
        else:
            archive.add_string(result, path)
    else:
        replacements = 0
    return replacements


def obfuscate_upload_passwords(component):
    # obfuscate strings like:
    # --upload-pass=PASSWORD
    # --upload-pass PASSWORD
    # --upload-url https://user:PASSWORD@some.url
    # in both sos_logs/sos.log and in sos_reports/manifest.json
    # and several sos_commands/* places from plugins's collected data
    try:
        component.archive.check_substitutions()
    except OSError:
        component._exit(1, msg="A collected file could not be redacted; "
                        "report will not be packaged or uploaded.")
    _arc_path = component.archive.get_archive_path()
    for path in component.files_with_upload_passwd:
        for f in Path(_arc_path).glob(path):
            # get just the relative path that archive works with
            f = os.path.relpath(f, _arc_path)
            for expression in [r"(--upload-pass[\s=]+)\S+",
                               r"(--upload-url[\s=]+\S+://.*:)([^@]*)",
                               r"(--upload-s3-secret-key[\s=]+)\S+"]:
                try:
                    component.archive.do_file_sub(f, expression, r"\1********")
                except OSError:
                    component._exit(
                        1, msg="Unable to redact upload credentials; "
                        "report will not be packaged or uploaded.")
