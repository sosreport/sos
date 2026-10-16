# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

"""
Shell completion support for sos.

Shell completion scripts call the hidden ``_complete`` subcommand, which is
handled here rather than as a regular component, in the form of:

    sos _complete SHELL CWORD [SHELL_ARGS...] -- WORDS...

where WORDS are the words of the command line being completed (starting with
the sos executable itself), and CWORD is the index within WORDS of the word
being completed. The candidates are determined by walking the same argparse
parsers that sos uses to parse its command line, and are then formatted for
the requesting shell by one of the formatters in ``sos.completion.shells``.
"""

import io
import sys

from contextlib import redirect_stdout

from sos.completion.providers import (PROVIDERS, COMMA_DELIMITED, FILES,
                                      DIRS, HOSTS)
from sos.options import SosListOption


class Completion():
    """The shell-agnostic result of a completion request.

    :param kind:        One of ``WORDS``, ``FILES``, ``DIRS``, ``HOSTS`` or
                        ``NONE``
    :param candidates:  For ``WORDS``, the full replacement words for the
                        word being completed
    :param prefix:      For the shell-performed kinds, the leading part of the
                        word being completed that is not part of the value
    :param value:       For the shell-performed kinds, the text to complete
    :param nospace:     Do not append a space after a sole candidate
    """

    WORDS = 'words'
    NONE = 'none'

    def __init__(self, kind=WORDS, candidates=None, prefix='', value='',
                 nospace=False):
        self.kind = kind
        self.candidates = candidates or []
        self.prefix = prefix
        self.value = value
        self.nospace = nospace


def _takes_value(action):
    return action.nargs != 0


def _is_list(action):
    return (isinstance(action, SosListOption) or
            action.dest in COMMA_DELIMITED)


def _collapse(candidates, text, sep='.'):
    """Truncate candidates at the next ``sep`` after ``text`` so that
    hierarchical values are completed one level at a time.
    """
    collapsed = set()
    for cand in candidates:
        idx = cand.find(sep, len(text))
        collapsed.add(cand if idx == -1 else cand[:idx + 1])
    return sorted(collapsed)


class SoSCompleter():
    """Determine completion candidates for an sos command line, and print
    them in the format expected by the requesting shell.

    :param sos:     The ``SoS`` object, used for its fully built parser
    :param args:    The arguments given after ``_complete``
    """

    def __init__(self, sos, args):
        self.sos = sos
        self.args = args

    def execute(self):
        from sos.completion.shells import SHELLS
        try:
            shell = self.args[0]
            cword = int(self.args[1])
            sep = self.args.index('--')
            shell_args = self.args[2:sep]
            words = self.args[sep + 1:]
            formatter = SHELLS[shell](shell_args)
        except (IndexError, ValueError, KeyError):
            sys.stderr.write("usage: sos _complete SHELL CWORD [ARGS...] -- "
                             "WORDS...\n")
            sys.exit(1)
        while len(words) <= cword:
            words.append('')
        try:
            # some imports report failures on stdout, which must not be
            # mistaken for completion candidates
            with redirect_stdout(io.StringIO()):
                result = self.complete(words, cword)
        except Exception:  # pylint: disable=broad-except
            # never let a completion error spill onto the user's terminal
            result = Completion(Completion.NONE)
        sys.stdout.write(formatter.format(result, words[cword]))
        # bin/sos exits via os._exit(), which does not flush stdout
        sys.stdout.flush()

    def complete(self, words, cword):
        """Return a ``Completion`` for ``words[cword]``"""
        cur = words[cword]
        top = self.sos.parser
        components = self.sos.subparsers.choices
        idx = 1
        while idx < cword and words[idx].startswith('-'):
            idx += 1
        if idx == cword:
            if cur.startswith('-'):
                return self._options(top, cur)
            return self._words(sorted(components), cur)
        if words[idx] not in components:
            return Completion(Completion.NONE)
        return self._complete_component(components[words[idx]],
                                        words[idx + 1:cword], cur)

    def _complete_component(self, parser, preceding, cur):
        """Walk the words already given to the component to determine what
        the current word is expected to be.
        """
        pending = None
        positionals = 0
        end_of_opts = False
        for word in preceding:
            if pending:
                pending = None
            elif end_of_opts or word == '-' or not word.startswith('-'):
                positionals += 1
            elif word == '--':
                end_of_opts = True
            elif word.startswith('--') or self._lookup(parser, word):
                name, eq, _ = word.partition('=')
                action = self._lookup(parser, name)
                if action and _takes_value(action) and not eq:
                    pending = action
            else:
                pending = self._grouped_short_opts(parser, word)

        if pending:
            return self._values(pending, cur)
        if not end_of_opts and cur.startswith('--') and '=' in cur:
            name, _, value = cur.partition('=')
            action = self._lookup(parser, name)
            if action and _takes_value(action):
                return self._values(action, value, prefix=f"{name}=")
            return Completion(Completion.NONE)
        if not end_of_opts and cur.startswith('-'):
            return self._options(parser, cur)
        posargs = [a for a in parser._actions if not a.option_strings]
        if positionals < len(posargs):
            return self._values(posargs[positionals], cur)
        if not end_of_opts and not cur:
            return self._options(parser, cur)
        return Completion(Completion.NONE)

    @staticmethod
    def _lookup(parser, opt):
        """Find the action for an option string, allowing for unambiguous
        abbreviations of long options as argparse does.
        """
        # pylint: disable=protected-access
        opts = parser._option_string_actions
        if opt in opts:
            return opts[opt]
        if opt.startswith('--'):
            matches = {opts[o] for o in opts if o.startswith(opt)}
            if len(matches) == 1:
                return matches.pop()
        return None

    @staticmethod
    def _grouped_short_opts(parser, word):
        """Handle grouped short options such as ``-vvq`` or ``-t4``, and
        return the action still awaiting a value, if any.
        """
        # pylint: disable=protected-access
        opts = parser._option_string_actions
        for pos, char in enumerate(word[1:], start=2):
            action = opts.get(f"-{char}")
            if action is None:
                return None
            if _takes_value(action):
                return None if word[pos:] else action
        return None

    @staticmethod
    def _words(candidates, text, prefix='', hierarchical=False):
        matches = [c for c in candidates if c.startswith(text)]
        if hierarchical:
            matches = _collapse(matches, text)
        return Completion(
            candidates=[f"{prefix}{m}" for m in matches],
            nospace=any(m.endswith(('.', '=')) for m in matches)
        )

    def _options(self, parser, cur):
        opts = []
        for action in parser._actions:  # pylint: disable=protected-access
            longs = [o for o in action.option_strings if o.startswith('--')]
            if cur in ('', '-') and longs:
                opts.extend(longs)
            else:
                opts.extend(action.option_strings)
        return self._words(sorted(set(opts)), cur)

    def _values(self, action, text, prefix=''):
        """Complete a value for ``action``"""
        chosen = []
        if _is_list(action) and ',' in text:
            head, _, text = text.rpartition(',')
            chosen = head.split(',')
            prefix = f"{prefix}{head},"
        provider, hierarchical = PROVIDERS.get(action.dest, (None, False))
        if provider:
            candidates = provider(text)
        elif action.choices:
            candidates = [str(c) for c in action.choices]
        else:
            return Completion(Completion.NONE)
        if candidates in (FILES, DIRS, HOSTS):
            return Completion(candidates, prefix=prefix, value=text)
        candidates = [c for c in candidates if c not in chosen]
        return self._words(candidates, text, prefix, hierarchical)

# vim: set et ts=4 sw=4 :
