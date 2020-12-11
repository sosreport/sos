
import sys
from sos.component import SoSComponent


class MissingCollect(SoSComponent):
    """This is used as a placeholder for when the local sos installation
    attempts to import sos.collector, but that module is not present. In those
    scenarios, it means that sos has been split into sub-packages. Barring
    incorrect splitting, this 'sos.missing' module should always be available
    to the main sos package.
    """

    load_policy = False
    configure_logging = False
    desc = '(unavailable) Collect an sos report from multiple nodes'
    missing_msg = (
        'It appears likely that your distribution separately ships a package '
        'called sos-collector. Please install it to enable this function'
    )

    def execute(self):
        sys.stderr.write(
            "The collect command is unavailable as it appears to be packaged "
            "separately for your distribution.\n\nPlease install the latest "
            "sos-collector package to enable this functionality.\n"
        )

    def load_options(self):
        """Override the normal component method to basically ignore all options
        given, so that we always print the error message that collect is
        unavailable, rather than failing on the parser when collect is called
        with options.
        """
        return []

    @classmethod
    def add_parser_options(cls, parser):
        """Set the --help output for collect to a message that shows that
        the functionality is unavailable
        """
        msg = "%s %s" % (
            'WARNING: `collect` is not available with this installation!',
            cls.missing_msg
        )
        parser.epilog = msg
        return parser


class MissingPexpect(MissingCollect):
    """This is used as a placeholder for when the collect component is locally
    installed, but cannot be used due to a missing pexpect dependency.
    """

    missing_msg = (
        'Please install the python3-pexpect package for your distribution in '
        'order to enable this function'
    )

    def execute(self):
        sys.stderr.write(
            "The collect command is unavailable due to a missing dependency "
            "on python3-pexpect.\n\nPlease install python3-pexpect to enable "
            "this functionality.\n"
        )

# vim: set et ts=4 sw=4 :
