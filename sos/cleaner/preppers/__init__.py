# Copyright 2023 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import logging


class SoSPrepper():
    """
    A prepper is a way to prepare loaded mappings with selected items within
    an sos report prior to beginning the full obfuscation routine.

    This was previously handled directly within archives, however this is a bit
    cumbersome and doesn't allow for all the flexibility we could use in this
    effort.

    Preppers are separated from parsers but will leverage them in order to feed
    parser-matched strings from files highlighted by a Prepper() to the
    appropriate mapping for initial obfuscation.

    Preppers may specify their own priority in order to influence the order in
    which mappings are prepped. Further, Preppers have two ways to prepare
    the maps - either by generating a list of filenames or via directly pulling
    content out of select files without the assistance of a parser. A lower
    priority value means the prepper should run sooner than those with higher
    values.

    For the former approach, `Prepper._get_$parser_file_list()` should be used
    and should yield filenames that exist in target archives. For the latter,
    the `Prepper._get_items_for_$map()` should be used.

    Finally, a `regex_items` dict is available for storing individual regex
    items for parsers that rely on them. These items will be added after all
    files and other individual items are handled. This dict has keys set to
    parser/mapping names, and the values should be sets of items, so preppers
    should add to them like so:

        self.regex_items['hostname'].add('myhostname')
    """

    name = 'Undefined'
    priority = 100

    def __init__(self, options):
        self.regex_items = {
            'hostname': set(),
            'ip': set(),
            'ipv6': set(),
            'keyword': set(),
            'mac': set(),
            'username': set()
        }
        self.opts = options
        self.soslog = logging.getLogger('sos')
        self.ui_log = logging.getLogger('sos_ui')

    def _fmt_log_msg(self, msg):
        return f"[prepper:{self.name}] {msg}"

    def log_debug(self, msg):
        self.soslog.debug(self._fmt_log_msg(msg))

    def log_info(self, msg):
        self.soslog.info(self._fmt_log_msg(msg))

    def log_error(self, msg):
        self.soslog.error(self._fmt_log_msg(msg))

    def get_parser_file_list(self, parser, archive):
        """
        Helper that calls the appropriate Prepper method for the specified
        parser. This allows Preppers to be able to provide items for multiple
        types of parsers without needing to handle repetitious logic to
        determine which parser we're interested within each individual call.

        The convention to use is to define `_get_$parser_file_list()` methods
        within Preppers, e.g. `_get_hostname_file_list()` would be used to
        provide filenames for the hostname parser. If such a method is not
        defined within a Prepper for a given parser, we handle that here so
        that individual Preppers do not need to.

        :param parser: The _name_ of the parser to get a file list for
        :type parser:  ``str``

        :param archive: The archive we are operating on currently for the
                        specified parser
        :type archive:  ``SoSObfuscationArchive``

        :returns: A list of filenames within the archive to prep with
        :rtype: ``list``
        """
        _check = f"_get_{parser}_file_list"
        if hasattr(self, _check):
            return getattr(self, _check)(archive)
        return []

    def get_items_for_map(self, mapping, archive):
        """
        Similar to `get_parser_file_list()`, a helper for calling the specific
        method for generating items for the given `map`. This allows Preppers
        to be able to provide items for multiple types of maps, without the
        need to handle repetitious logic to determine which parser we're
        interested in within each individual call.

        :param mapping: The _name_ of the mapping to get items for
        :type mapping:  ``str``

        :param archive: The archive we are operating on currently for the
                        specified parser
        :type archive:  ``SoSObfuscationArchive``

        :returns: A list of distinct items to obfuscate without using a parser
        :rtype:   ``list``
        """
        _check = f"_get_items_for_{mapping}"
        if hasattr(self, _check):
            return getattr(self, _check)(archive)
        return []

# vim: set et ts=4 sw=4 :
