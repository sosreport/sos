# Copyright (C) 2020 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import json
import os

from sos.options import SoSOptions

PRESETS_PATH = "/etc/sos/presets.d"

#: Constants for on-disk preset fields
DESC = "desc"
NOTE = "note"
OPTS = "args"


class PresetDefaults():
    """Preset command line defaults to allow for quick reference to sets of
    commonly used options

    :param name: The name of the new preset
    :type name: ``str``

    :param desc: A description for the new preset
    :type desc: ``str``

    :param note: Note for the new preset
    :type note: ``str``

    :param opts: Options set for the new preset
    :type opts: ``SoSOptions``
    """
    #: Preset name, used for selection
    name = None
    #: Human readable preset description
    desc = None
    #: Notes on preset behaviour
    note = None
    #: Options set for this preset
    opts = SoSOptions()

    #: ``True`` if this preset if built-in or ``False`` otherwise.
    builtin = True

    def __str__(self):
        """Return a human readable string representation of this
            ``PresetDefaults`` object.
        """
        return ("name=%s desc=%s note=%s opts=(%s)" %
                (self.name, self.desc, self.note, str(self.opts)))

    def __repr__(self):
        """Return a machine readable string representation of this
            ``PresetDefaults`` object.
        """
        return ("PresetDefaults(name='%s' desc='%s' note='%s' opts=(%s)" %
                (self.name, self.desc, self.note, repr(self.opts)))

    def __init__(self, name="", desc="", note=None, opts=SoSOptions()):
        """Initialise a new ``PresetDefaults`` object with the specified
            arguments.

            :returns: The newly initialised ``PresetDefaults``
        """
        self.name = name
        self.desc = desc
        self.note = note
        self.opts = opts

    def write(self, presets_path):
        """Write this preset to disk in JSON notation.

        :param presets_path: the directory where the preset will be written
        :type presets_path: ``str``
        """
        if self.builtin:
            raise TypeError("Cannot write built-in preset")

        # Make dictionaries of PresetDefaults values
        odict = self.opts.dict()
        pdict = {self.name: {DESC: self.desc, NOTE: self.note, OPTS: odict}}

        if not os.path.exists(presets_path):
            os.makedirs(presets_path, mode=0o755)

        with open(os.path.join(presets_path, self.name), "w") as pfile:
            json.dump(pdict, pfile)

    def delete(self, presets_path):
        """Delete a preset from disk

        :param presets_path: the directory where the preset is saved
        :type presets_path: ``str``
        """
        os.unlink(os.path.join(presets_path, self.name))


NO_PRESET = 'none'
NO_PRESET_DESC = 'Do not load a preset'
NO_PRESET_NOTE = 'Use to disable automatically loaded presets'

GENERIC_PRESETS = {
    NO_PRESET: PresetDefaults(name=NO_PRESET, desc=NO_PRESET_DESC,
                              note=NO_PRESET_NOTE, opts=SoSOptions())
}


# vim: set et ts=4 sw=4 :
