# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import glob
import json
import os
import re

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class CephRGW(Plugin, RedHatPlugin, UbuntuPlugin):
    """
    This plugin is for capturing information from Ceph RGW nodes.

    Every collection here is a `radosgw-admin` call, and those require working
    CephX credentials. Rather than assuming an identity of `rgw.<hostname>` -
    which is almost never correct under cephadm, where daemon names take the
    form `rgw.<service>.<host>.<suffix>` - this plugin discovers the real
    client identities from the on-disk daemon directories and then validates
    each candidate auth path before collecting anything.

    Candidates are tried most- to least-capable: an admin keyring on the host
    (best for cluster-wide queries), then the RGW container using the daemon's
    own keyring, then that same keyring used from the host. If none of them
    authenticate, the command collection is skipped with a single log message
    rather than writing an identical auth failure into every file.
    """

    short_desc = 'CEPH rgw'

    plugin_name = 'ceph_rgw'
    profiles = ('storage', 'virt', 'container', 'webserver', 'ceph')
    containers = ('ceph-(.*)?rgw.*',)
    files = ('/var/lib/ceph/radosgw/*',
             '/var/lib/ceph/*/rgw.*',
             '/var/snap/microceph/common/data/radosgw/*')

    def setup(self):
        all_logs = self.get_option("all_logs")
        cmds = ['bucket limit check',
                'bucket list',
                'bucket stats',
                'datalog list',
                'datalog status',
                'gc list',
                'lc list',
                'log list',
                'metadata sync status',
                'period list',
                'realm list',
                'reshard list',
                'sync error list',
                'sync status',
                'zone list',
                'zone placement list',
                'zonegroup list',
                'zonegroup placement list',
                ]

        microceph = self.policy.package_manager.pkg_by_name('microceph')
        if microceph:
            if all_logs:
                self.add_copy_spec([
                    "/var/snap/microceph/common/logs/*ceph-radosgw*.log*",
                ])
            else:
                self.add_copy_spec([
                    "/var/snap/microceph/common/logs/*ceph-radosgw*.log",
                ])
            self.add_forbidden_path([
                "/var/snap/microceph/common/**/*keyring*",
                "/var/snap/microceph/current/**/*keyring*",
                "/var/snap/microceph/common/state/*",
            ])
        else:
            # cephadm writes logs under /var/log/ceph/<fsid>/, packaged
            # installs write them directly to /var/log/ceph/
            if not all_logs:
                self.add_copy_spec('/var/log/ceph/**/ceph-client.rgw*.log',
                                   tags='ceph_rgw_log')
            else:
                self.add_copy_spec('/var/log/ceph/**/ceph-client.rgw*.log*',
                                   tags='ceph_rgw_log')

            self.add_forbidden_path([
                "/etc/ceph/*keyring*",
                "/var/lib/ceph/*keyring*",
                "/var/lib/ceph/*/*keyring*",
                "/var/lib/ceph/*/*/*keyring*",
                "/var/lib/ceph/osd",
                "/var/lib/ceph/mon",
                # Excludes temporary ceph-osd mount location like
                # /var/lib/ceph/tmp/mnt.XXXX from sos collection.
                "/var/lib/ceph/tmp/*mnt*",
                "/etc/ceph/*bindpass*"
            ])

        # Find an identity that can actually talk to the cluster before
        # running anything. Without this every command below returns the same
        # "unable to find a keyring" error on a cephadm node.
        container, args, zones = self._resolve_rgw_auth(microceph)
        if args is None:
            self._log_warn(
                "No working radosgw-admin credentials found on this host, "
                "skipping RGW admin command collection. These queries can be "
                "run from a host holding client.admin, for example "
                "'cephadm shell -- radosgw-admin sync status'."
            )
            return

        rgw_admin = ' '.join(['radosgw-admin'] + args)
        # Name the files after the subcommand alone. The discovered identity,
        # keyring path and container exec prefix together run past NAME_MAX,
        # and truncating those would leave the per-zone collections below
        # sharing a single filename.
        for cmd in cmds:
            self.add_cmd_output(
                f'{rgw_admin} {cmd}', container=container,
                suggest_filename=f"radosgw-admin_{cmd.replace(' ', '_')}")

        self._add_zone_details(rgw_admin, container, zones)

    def _get_keyring_entity(self, keyring):
        """Read the CephX entity name out of a keyring file.

        Only the ``[client.foo]`` section header is parsed - the key itself is
        never read, and keyrings stay excluded from the archive by
        ``add_forbidden_path()``.

        :param keyring:     Path to the keyring file to inspect
        :type keyring:      ``str``

        :returns:   The client name without its ``client.`` prefix, or None
        :rtype:     ``str`` or ``None``
        """
        try:
            with open(keyring, 'r', encoding='utf-8') as kfile:
                for line in kfile:
                    match = re.match(r'\[client\.(.+)\]', line.strip())
                    if match:
                        return match.group(1)
        except (OSError, UnicodeDecodeError) as err:
            self._log_debug(f"Could not read entity name from {keyring}: "
                            f"{err}")
        return None

    def _get_rgw_daemons(self):
        """Discover the RGW daemons deployed on this host.

        Identities come from the keyring entity name, falling back to the
        daemon directory name - never from the hostname, which does not match
        the daemon name under cephadm.

        :returns:   Discovered daemons as (client name, keyring path) pairs
        :rtype:     ``list`` of ``tuples``
        """
        daemons = []
        for pattern in ('/var/lib/ceph/*/rgw.*',     # cephadm
                        '/var/lib/ceph/radosgw/*'):  # packaged install
            for ddir in sorted(glob.glob(self.path_join(pattern))):
                keyring = self.path_join(ddir, 'keyring')
                if not self.path_exists(keyring):
                    continue
                name = self._get_keyring_entity(keyring)
                if not name:
                    # e.g. 'rgw.crashoverride.node1.xspqmz' under cephadm,
                    # or 'ceph-rgw.node1' for a packaged install
                    name = os.path.basename(ddir)
                    if '-' in name and not name.startswith(('rgw.',
                                                            'radosgw.')):
                        name = name.split('-', 1)[1]
                if (name, keyring) not in daemons:
                    daemons.append((name, keyring))
        return daemons

    def _get_auth_candidates(self, microceph):
        """Build the ordered list of auth paths worth trying, most capable
        first.

        :param microceph:   Is this a microceph deployment?
        :type microceph:    ``bool``

        :returns:   Candidates as (container name or None, radosgw-admin args)
        :rtype:     ``list`` of ``tuples``
        """
        if microceph:
            return [(None, ['--id', 'radosgw.gateway'])]

        # An admin keyring on the host answers cluster-wide queries best, so
        # try the default identity before falling back to a daemon's own key
        candidates = [(None, [])]

        cname = None
        for regex in self.containers:
            cons = self.get_all_containers_by_regex(regex)
            if cons:
                cname = cons[0][1]
                break

        daemons = self._get_rgw_daemons()
        if cname:
            for name, _ in daemons:
                # cephadm bind-mounts the daemon directory to a different
                # location inside the container - /var/lib/ceph/radosgw/
                # ceph-<name> - which CephX does not search, so the keyring
                # has to be named explicitly there
                candidates.append((cname, [
                    '--id', name,
                    '--keyring', f'/var/lib/ceph/radosgw/ceph-{name}/keyring',
                ]))
                candidates.append((cname, ['--id', name]))
            if not daemons:
                candidates.append((cname, []))
        candidates += [(None, ['--id', name, '--keyring', keyring])
                       for name, keyring in daemons]
        return candidates

    def _resolve_rgw_auth(self, microceph):
        """Find an auth path that radosgw-admin actually accepts.

        Each candidate is probed with a `zone list`, whose output is handed
        back so that it does not need to be run a second time.

        :param microceph:   Is this a microceph deployment?
        :type microceph:    ``bool``

        :returns:   (container name or None, radosgw-admin args, zone list
                    output), all None if no candidate authenticated
        :rtype:     ``tuple``
        """
        for container, args in self._get_auth_candidates(microceph):
            cmd = ' '.join(['radosgw-admin'] + args + ['zone list'])
            res = self.exec_cmd(cmd, container=container)
            if res['status'] == 0:
                return (container, args, res['output'])
            self._log_debug(f"'{cmd}' failed in container '{container}' with "
                            f"status {res['status']}, trying next identity")
        return (None, None, None)

    def _add_zone_details(self, rgw_admin, container, zones):
        """Collect the full definition of every zone and zonegroup.

        :param rgw_admin:   The authenticated radosgw-admin invocation
        :type rgw_admin:    ``str``

        :param container:   Container to run in, or None to run on the host
        :type container:    ``str`` or ``None``

        :param zones:       Output of the `zone list` used to probe auth
        :type zones:        ``str``
        """
        zgroups = self.exec_cmd(f'{rgw_admin} zonegroup list',
                                container=container)
        for output, key, subcmd, opt in (
                (zones, 'zones', 'zone get', '--rgw-zone'),
                (zgroups['output'] if zgroups['status'] == 0 else None,
                 'zonegroups', 'zonegroup get', '--rgw-zonegroup')):
            if output is None:
                continue
            try:
                names = json.loads(output)[key]
            except (ValueError, KeyError) as err:
                self._log_error(f'Error while getting get rgw '
                                f'{key[:-1]} list: {err}')
                continue
            for name in names:
                self.add_cmd_output(
                    f'{rgw_admin} {subcmd} {opt}={name}', container=container,
                    suggest_filename=(f"radosgw-admin_"
                                      f"{subcmd.replace(' ', '_')}_{name}"))

    def postproc(self):
        """ Obfuscate secondary zone access keys """

        # Match only the quoted value. A greedy match to end-of-line also eats
        # the trailing comma, which leaves `zone get` output that no longer
        # parses as JSON.
        rsub = r'("access_key":|"secret_key":)\s*"[^"]*"'
        self.do_cmd_output_sub("radosgw-admin", rsub, r'\1 "**********"')


# vim: set et ts=4 sw=4 :
