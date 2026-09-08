# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import sys
import tempfile
from contextlib import ExitStack

from sos.component import SoSComponent
from sos.cleaner.parsers.hostname_parser import SoSHostnameParser
from sos.cleaner.parsers.ip_parser import SoSIPParser
from sos.cleaner.parsers.ipv6_parser import SoSIPv6Parser
from sos.cleaner.parsers.mac_parser import SoSMacParser


def sanitize_stream(source, destination, parsers):
    """Sanitize UTF-8 binary streams using the existing cleaner parsers.

    Binary I/O preserves line endings and a missing final newline. Each line
    must pass every parser before it is written. Errors propagate to the
    caller; previously written lines cannot be retracted from a pipe.
    """
    for number, raw_line in enumerate(source, start=1):
        line = raw_line.decode('utf-8')
        for parser in parsers:
            try:
                line, _ = parser.parse_line(line)
            except Exception as err:
                # Do not echo potentially sensitive input from the exception.
                raise RuntimeError(
                    f'{parser.name} failed on line {number}'
                ) from err
        destination.write(line.encode('utf-8'))


class SoSCleanText(SoSComponent):
    """A text-only frontend to the cleaner's existing parsers and maps."""

    desc = 'Obfuscate known identities and network addresses in UTF-8 text'

    def __init__(self, parser, args, cmdline):
        # pylint: disable=super-init-not-called
        # This stream filter needs neither local-system probing nor the
        # component's report logging/configuration (which can write stdout).
        # Defer all I/O to execute(), where failures are reported on stderr.
        self.opts = args

    @classmethod
    def add_parser_options(cls, parser):
        parser.usage = 'sos clean-text [FILE|-] [options]'
        parser.description = (
            'Write sanitized UTF-8 text to stdout. Hostnames and domains must '
            'be explicitly seeded; unknown names and usernames are unchanged. '
            'Uses a private temporary cache, without loading or updating the '
            'system cleaner mapping. On failure, earlier output may be '
            'partial.'
        )
        parser.add_argument('target', metavar='FILE', nargs='?', default='-',
                            help='Input file, or - for stdin (default)')
        parser.add_argument('--hostnames', action='extend', default=[],
                            help='Comma-separated known hostnames to '
                                 'obfuscate')
        parser.add_argument('--domains', action='extend', default=[],
                            help='Comma-separated known domains to obfuscate')

    def execute(self):
        try:
            for domain in self.opts.domains:
                if len(domain.split('.')) < 2:
                    raise ValueError('--domains values must contain a dot')
            with ExitStack() as stack:
                workdir = stack.enter_context(tempfile.TemporaryDirectory(
                    prefix='sos-clean-text-', dir=self.opts.tmp_dir or None
                ))
                # Keep the same relative ordering as SoSCleaner. Username and
                # keyword parsers have no identities to match in this mode.
                parsers = [cls({}, workdir) for cls in (
                    SoSHostnameParser, SoSIPParser, SoSIPv6Parser, SoSMacParser
                )]
                hostname_parser = parsers[0]
                for identity in self.opts.hostnames + self.opts.domains:
                    hostname_parser.mapping.add(identity.lower())
                hostname_parser.generate_item_regexes()

                if self.opts.target == '-':
                    source = sys.stdin.buffer
                else:
                    source = stack.enter_context(open(self.opts.target, 'rb'))
                sanitize_stream(source, sys.stdout.buffer, parsers)
                # bin/sos exits with os._exit(), so flush explicitly.
                sys.stdout.buffer.flush()
        except Exception as err:
            print(f'sos clean-text: {err}', file=sys.stderr)
            raise SystemExit(1) from err
        except KeyboardInterrupt:
            print('sos clean-text: interrupted', file=sys.stderr)
            raise SystemExit(130) from None
