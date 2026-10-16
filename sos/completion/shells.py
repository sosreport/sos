# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

"""
Formatters that translate a ``Completion`` into the output expected by the
completion script of a given shell. Support for a new shell requires a new
formatter here, registered in ``SHELLS``, and a completion script for that
shell that consumes the formatter's output.
"""


class ShellFormatter():
    """Base class for shell formatters.

    :param args:    Any shell-specific arguments given to ``sos _complete``
    """

    name = None

    def __init__(self, args):
        self.args = args

    def format(self, completion, cur):
        """Return the text to print for ``completion`` of the word ``cur``"""
        raise NotImplementedError


class BashFormatter(ShellFormatter):
    """Formatter for the bash completion script.

    Accepts the value of ``$COMP_WORDBREAKS`` as its only argument. The output
    is newline delimited, as follows:

        KIND NOSPACE
        PREFIX
        VALUE
        CANDIDATE...

    where KIND is one of words, files, dirs, hosts or none, and NOSPACE is 1
    if no space should be appended after a sole candidate. For the files, dirs
    and hosts kinds, the script is expected to complete VALUE itself and then
    prepend PREFIX to each result.

    The script completes words with '=' and ':' kept together, but readline
    only replaces the text after the last such word break character, so that
    leading text is removed from the candidates and the prefix.
    """

    name = 'bash'
    default_wordbreaks = '"\'><=;|&(:'

    def format(self, completion, cur):
        wordbreaks = self.args[0] if self.args else self.default_wordbreaks
        cut = max(cur.rfind(c) for c in '=:' if c in wordbreaks) \
            if any(c in wordbreaks for c in '=:') else -1
        strip = cur[:cut + 1]

        prefix = completion.prefix
        prefix = prefix[len(strip):] if prefix.startswith(strip) else ''
        candidates = [c[len(strip):] for c in completion.candidates
                      if c.startswith(strip)]
        lines = [f"{completion.kind} {int(completion.nospace)}", prefix,
                 completion.value] + candidates
        return '\n'.join(lines) + '\n'


SHELLS = {
    fmt.name: fmt for fmt in (BashFormatter,)
}

# vim: set et ts=4 sw=4 :
