# Copyright (C) 2016 Red Hat, Inc., Michal Srb <michal@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import hashlib
import json
import os
import re
import zipfile
from functools import partial
from sos.plugins import Plugin, RedHatPlugin


class Jars(Plugin, RedHatPlugin):
    """Collect information about available Java archives."""

    plugin_name = "jars"
    version = "1.0.0"
    profiles = ("java",)
    option_list = [
        ("append_locations", "colon-separated list of additional JAR paths",
         "fast", "")
    ]

    # There is no standard location for JAR files and scanning
    # the whole filesystem could be very slow. Therefore we only
    # scan directories in which JARs can be typically found.
    jar_locations = (
        "/usr/share/java",  # common location for JARs
        "/usr/lib/java",    # common location for JARs containing native code
        "/opt",             # location for RHSCL and 3rd party software
        "/usr/local",       # used by sysadmins when installing SW locally
        "/var/lib"          # Java services commonly explode WARs there
    )

    def setup(self):
        results = {"jars": []}
        jar_paths = []

        locations = list(Jars.jar_locations)
        extra_locations = self.get_option("append_locations")
        if extra_locations:
            locations += extra_locations.split(":")

        # find all JARs in given locations
        for location in locations:
            for dirpath, _, filenames in os.walk(location):
                for filename in filenames:
                    path = os.path.join(dirpath, filename)
                    if Jars.is_jar(path):
                        jar_paths.append(path)

        # try to extract information about found JARs
        for jar_path in jar_paths:
            maven_id = Jars.get_maven_id(jar_path)
            jar_id = Jars.get_jar_id(jar_path)
            if maven_id or jar_id:
                record = {"path": jar_path,
                          "sha1": jar_id,
                          "maven_id": maven_id
                          }
                results["jars"].append(record)

        results_str = json.dumps(results, indent=4, separators=(",", ": "))
        self.add_string_as_file(results_str, "jars.json")

    @staticmethod
    def is_jar(path):
        """Check whether given file is a JAR file.

        JARs are ZIP files which usually include a manifest
        at the canonical location 'META-INF/MANIFEST.MF'.
        """
        if os.path.isfile(path) and zipfile.is_zipfile(path):
            try:
                with zipfile.ZipFile(path) as f:
                    if "META-INF/MANIFEST.MF" in f.namelist():
                        return True
            except IOError:
                pass
        return False

    @staticmethod
    def get_maven_id(jar_path):
        """Extract Maven coordinates from a given JAR file, if possible.

        JARs build by Maven (most popular Java build system) contain
        'pom.properties' file. We can extract Maven coordinates
         from there.
        """
        props = {}
        try:
            with zipfile.ZipFile(jar_path) as f:
                r = re.compile("META-INF/maven/[^/]+/[^/]+/pom.properties$")
                result = [x for x in f.namelist() if r.match(x)]
                if len(result) != 1:
                    return None
                with f.open(result[0]) as props_f:
                    for line in props_f.readlines():
                        line = line.strip()
                        if not line.startswith(b"#"):
                            try:
                                (key, value) = line.split(b"=")
                                key = key.decode('utf8').strip()
                                value = value.decode('utf8').strip()
                                props[key] = value
                            except ValueError:
                                return None
        except IOError:
            pass
        return props

    @staticmethod
    def get_jar_id(jar_path):
        """Compute JAR id.

        Returns sha1 hash of a given JAR file.
        """
        jar_id = ""
        try:
            with open(jar_path, mode="rb") as f:
                m = hashlib.sha1()
                for buf in iter(partial(f.read, 4096), b''):
                    m.update(buf)
            jar_id = m.hexdigest()
        except IOError:
            pass
        return jar_id
