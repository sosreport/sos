# This file is part of the sos project: https://github.com/sosreport/sos

"""User-facing entry point for the whole-report sanitizer."""

import os
import sys
import tarfile

from sos.component import SoSComponent
from sos.cleaner.sanitizer import ReportSanitizer


class SoSSanitizeReport(SoSComponent):
    """Run the safe whole-report sanitizer without legacy cleaner state."""

    desc = 'Create a sanitized copy of an sosreport archive'
    configure_logging = False
    load_policy = False
    load_probe = False

    def __init__(self, parser, args, cmdline):
        # Like clean-text, this command must not initialize policy, logging,
        # or any host-local discovery. All work is invocation-local.
        self.opts = args

    @classmethod
    def add_parser_options(cls, parser):
        parser.usage = 'sos sanitize-report INPUT --output OUTPUT'
        parser.description = (
            'Create a sanitized tar.xz copy of an sosreport archive. '
            'Identity discovery is limited to the report tree.'
        )
        parser.epilog = (
            'Examples:\n'
            '  sos sanitize-report sosreport.tar.xz '
            '--output sosreport-sanitized.tar.xz\n'
            '  sos sanitize-report sosreport.tar.xz '
            '--output sosreport-sanitized.tar.xz '
            '--mapping-output ~/private/report-map.json\n'
            '  sos sanitize-report sosreport.tar.xz '
            '--output sosreport-sanitized.tar.xz '
            '--domain customer.example --username alice\n\n'
            'The mapping output is private correlation data and may contain '
            'sensitive customer identifiers. Do not share it with the '
            'sanitized report.'
        )
        parser.add_argument('input', metavar='INPUT',
                            help='input sosreport tar.xz archive')
        parser.add_argument('--output', required=True,
                            help='sanitized tar.xz output path')
        parser.add_argument('--mapping-output', default=None,
                            help='write private original-to-pseudonym '
                                 'mapping JSON')
        parser.add_argument('--hostname', action='extend', default=[],
                            dest='hostnames',
                            help='known hostname seed; repeat or comma-separate')
        parser.add_argument('--domain', action='extend', default=[],
                            dest='domains',
                            help='known domain seed; repeat or comma-separate')
        parser.add_argument('--username', action='extend', default=[],
                            dest='usernames',
                            help='known username seed; repeat or comma-separate')

    def execute(self):
        try:
            self._validate()
            result = ReportSanitizer(
                hostnames=self.opts.hostnames,
                domains=self.opts.domains,
                usernames=self.opts.usernames,
                temp_parent=self.opts.tmp_dir or None,
            ).sanitize(self.opts.input, self.opts.output,
                       mapping_output=self.opts.mapping_output)
            if not self.opts.quiet:
                print('Sanitized report written successfully.')
                print('Mapping file written: ' +
                      ('yes' if result['mapping_written'] else 'no'))
                for namespace, count in result['mapping_entries'].items():
                    print(f'{namespace}: {count}')
                sys.stdout.flush()
        except KeyboardInterrupt:
            print('sos sanitize-report: interrupted', file=sys.stderr)
            sys.stderr.flush()
            raise SystemExit(130) from None
        except Exception as err:
            message = str(err) if isinstance(err, _CliError) else \
                'report sanitization failed'
            print(f'sos sanitize-report: ERROR: {message}', file=sys.stderr)
            sys.stderr.flush()
            raise SystemExit(1) from None

    def _validate(self):
        input_path = os.path.abspath(self.opts.input)
        output_path = os.path.abspath(self.opts.output)
        mapping_path = (os.path.abspath(self.opts.mapping_output)
                        if self.opts.mapping_output else None)
        if not os.path.isfile(input_path) or os.path.islink(input_path):
            raise _CliError('invalid input archive')
        if not tarfile.is_tarfile(input_path):
            raise _CliError('unsupported input archive')
        if not output_path.endswith('.tar.xz'):
            raise _CliError('unsupported output format')
        if not os.path.isdir(os.path.dirname(output_path)):
            raise _CliError('invalid output path')
        if os.path.lexists(output_path):
            raise _CliError('output already exists')
        paths = [input_path, output_path]
        if mapping_path:
            if not os.path.isdir(os.path.dirname(mapping_path)):
                raise _CliError('invalid mapping output path')
            if os.path.lexists(mapping_path):
                raise _CliError('mapping output already exists')
            paths.append(mapping_path)
        real_paths = [os.path.realpath(path) for path in paths]
        if len(real_paths) != len(set(real_paths)):
            raise _CliError('input and output paths must be different')
        for domain in self.opts.domains:
            if len(domain.split('.')) < 2:
                raise _CliError('invalid domain seed')


class _CliError(Exception):
    """A safe user-input error with no interpolated values."""

