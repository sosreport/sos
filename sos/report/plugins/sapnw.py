# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import glob
import os
import re
from sos.report.plugins import Plugin, RedHatPlugin


class Sapnw(Plugin, RedHatPlugin):
    """Collects diagnostic data on SAP NetWeaver instances, discovering
    instances across saphostctrl, /usr/sap/sapservices, systemd units, and
    /usr/sap directories, and collecting profiles, sappfpar parameters,
    sapcontrol instance/HA/enqueue status, and singleton work directory logs.
    """

    short_desc = 'SAP NetWeaver'
    plugin_name = 'sapnw'
    profiles = ('sap',)
    files = ('/usr/sap', '/sapmnt', '/etc/systemd/system/SAP*.service')

    def _is_valid_nw_sid(self, sid):
        """ Return True if sid has a valid NetWeaver SYS or sapmnt layout """
        # Skip DAA (SAP Diagnostics Agent SID); not a NetWeaver instance
        if not re.match(r'^[A-Z][A-Z0-9]{2}$', sid) or sid == 'DAA':
            return False
        return (
            self.path_isdir(f"/usr/sap/{sid}/SYS") or
            self.path_isdir(f"/sapmnt/{sid}")
        )

    def _is_hana_instance(self, sid, inst, inst_dir=None, profile_path=None):
        """ Return True if (sid, inst) is an SAP HANA instance """
        if inst_dir and inst_dir.strip().startswith('HDB'):
            return True
        if profile_path:
            prof_name = os.path.basename(profile_path.strip())
            if prof_name.startswith(f"{sid}_HDB"):
                return True
        return (
            self.path_isdir(f"/usr/sap/{sid}/HDB{inst}") or
            self.path_isdir(f"/hana/shared/{sid}/HDB{inst}")
        )

    def _register_instance(self, instances, sids, sid, inst,
                           inst_dir=None, vhost=None, profile_path=None):
        """ Register a discovered SAP NetWeaver instance """
        if not sid or not inst:
            return
        sid = sid.strip()
        inst = inst.strip()
        # Skip DAA (SAP Diagnostics Agent SID); not a NetWeaver instance
        if not re.match(r'^[A-Z][A-Z0-9]{2}$', sid) or sid == 'DAA':
            return
        if not re.match(r'^[0-9]{2}$', inst):
            return
        if self._is_hana_instance(sid, inst, inst_dir=inst_dir,
                                  profile_path=profile_path):
            return

        sids.add(sid)
        key = (sid, inst)
        if key not in instances:
            instances[key] = {
                'sid': sid,
                'inst': inst,
                'inst_dirs': set(),
                'vhosts': set(),
                'profiles': {},
            }
        entry = instances[key]
        if inst_dir:
            entry['inst_dirs'].add(inst_dir.strip())
        if vhost:
            entry['vhosts'].add(vhost.strip())
        if profile_path:
            prof_name = os.path.basename(profile_path.strip())
            entry['profiles'][prof_name] = profile_path.strip()

    @staticmethod
    def _match_profile_name(prof_name):
        """ Match SAP instance profile name <SID>_<INST_DIR><NR>_<HOST>
        while excluding backup/list suffixes (e.g. .1, .lst, .bak, .old) """
        if re.search(
            r'\.(?:[0-9]+|lst|bak|bkp|old|orig|sav|tmp|swp)$',
            prof_name, re.I
        ):
            return None
        return re.match(
            r'^([A-Z][A-Z0-9]{2})_([A-Z]+([0-9]{2}))_([^\s~]+)$',
            prof_name
        )

    def _parse_profile_token(self, pf_path, instances, sids):
        """ Parse a pf=<path> token and register instance metadata """
        prof_name = os.path.basename(pf_path.strip())
        match = self._match_profile_name(prof_name)
        if match:
            sid, inst_dir, inst, vhost = match.groups()
            self._register_instance(
                instances, sids, sid, inst,
                inst_dir=inst_dir, vhost=vhost, profile_path=pf_path
            )

    def _discover_instances(self):
        """ Discover SAP instances across hostctrl, sapservices, systemd,
        and filesystem directories """
        instances = {}
        sids = set()

        # 1. saphostctrl -function ListInstances
        inst_list = self.collect_cmd_output(
            "/usr/sap/hostctrl/exe/saphostctrl -function ListInstances",
            suggest_filename="SAPInstances"
        )
        if inst_list['status'] == 0 and inst_list['output']:
            for inst_line in inst_list['output'].splitlines():
                # Skip DAA (SAP Diagnostics Agent; not a NetWeaver instance)
                if ("DAA" not in inst_line and not
                        inst_line.startswith("No instances found")):
                    fields = inst_line.strip().split()
                    if len(fields) >= 8:
                        self._register_instance(
                            instances, sids,
                            fields[3], fields[5], vhost=fields[7]
                        )

        # 2. /usr/sap/sapservices
        if self.path_isfile("/usr/sap/sapservices"):
            try:
                with open(self.path_join("/usr/sap/sapservices"), 'r',
                          encoding='utf-8', errors='ignore') as sfile:
                    for line in sfile:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        pf_match = re.search(r'\bpf=(\S+)', line)
                        if pf_match:
                            self._parse_profile_token(
                                pf_match.group(1), instances, sids
                            )
                        svc_match = re.search(
                            r'\bSAP([A-Z][A-Z0-9]{2})_([0-9]{2})\b', line
                        )
                        if svc_match:
                            self._register_instance(
                                instances, sids,
                                svc_match.group(1), svc_match.group(2)
                            )
            except OSError as err:
                self._log_debug(f"Could not read /usr/sap/sapservices: {err}")

        # 3. /etc/systemd/system/SAP*.service and /usr/lib/systemd/system/
        unit_globs = (
            "/etc/systemd/system/SAP*.service",
            "/usr/lib/systemd/system/SAP*.service",
        )
        for uglob in unit_globs:
            for unit_path in sorted(glob.glob(self.path_join(uglob))):
                unit_name = os.path.basename(unit_path)
                umatch = re.match(
                    r'^SAP([A-Z][A-Z0-9]{2})_([0-9]{2})\.service$',
                    unit_name
                )
                if umatch:
                    self._register_instance(
                        instances, sids, umatch.group(1), umatch.group(2)
                    )
                try:
                    with open(unit_path, 'r', encoding='utf-8',
                              errors='ignore') as ufile:
                        for line in ufile:
                            line = line.strip()
                            pf_match = re.search(r'\bpf=(\S+)', line)
                            if pf_match:
                                self._parse_profile_token(
                                    pf_match.group(1), instances, sids
                                )
                            wd_match = re.search(
                                r'WorkingDirectory=/usr/sap/'
                                r'([A-Z][A-Z0-9]{2})/([A-Z]+([0-9]{2}))/work',
                                line
                            )
                            if wd_match:
                                self._register_instance(
                                    instances, sids,
                                    wd_match.group(1), wd_match.group(3),
                                    inst_dir=wd_match.group(2)
                                )
                except OSError as err:
                    self._log_debug(f"Could not read {unit_path}: {err}")

        # 4. Filesystem scan of local /usr/sap/<SID>/<INST_DIR> directories
        if self.path_isdir("/usr/sap"):
            for sid in sorted(self.listdir("/usr/sap")):
                sid = sid.strip()
                if not self._is_valid_nw_sid(sid):
                    continue
                sid_dir = f"/usr/sap/{sid}"
                if not self.path_isdir(sid_dir):
                    continue
                for entry in sorted(self.listdir(sid_dir)):
                    entry = entry.strip()
                    imatch = re.match(r'^([A-Z]+([0-9]{2}))$', entry)
                    if imatch and not entry.startswith('HDB'):
                        self._register_instance(
                            instances, sids,
                            sid, imatch.group(2), inst_dir=imatch.group(1)
                        )

        # Match discovered local instances against profile directories
        for (sid, inst), info in instances.items():
            for prof_dir in (f"/usr/sap/{sid}/SYS/profile",
                             f"/sapmnt/{sid}/profile"):
                if not self.path_isdir(prof_dir):
                    continue
                for line in sorted(self.listdir(prof_dir)):
                    prof = line.strip()
                    pmatch = self._match_profile_name(prof)
                    if not pmatch:
                        continue
                    p_sid, p_idir, p_inst, p_vhost = pmatch.groups()
                    if p_sid != sid or p_inst != inst:
                        continue
                    if p_idir.startswith('HDB'):
                        continue
                    if info['vhosts'] and p_vhost not in info['vhosts']:
                        continue
                    info['inst_dirs'].add(p_idir)
                    info['vhosts'].add(p_vhost)
                    if prof not in info['profiles']:
                        info['profiles'][prof] = f"{prof_dir}/{prof}"

        return instances, sids

    def collect_list_instances(self):
        """ Collect data on discovered SAP NetWeaver instances """
        instances, sids = self._discover_instances()

        for (sid, inst), info in sorted(instances.items()):
            lowsid = sid.lower()
            sidadm = f"{lowsid}adm"
            # Use 'su -' instead of runas= so <sid>adm's login profile is
            # sourced (setting PATH, LD_LIBRARY_PATH, and SAPSYSTEMNAME)
            prefix = f"su - {sidadm} -c"

            for prof_name, pf_path in sorted(info['profiles'].items()):
                resolved_pf = pf_path
                for candidate in (
                    f"/usr/sap/{sid}/SYS/profile/{prof_name}",
                    f"/sapmnt/{sid}/profile/{prof_name}",
                ):
                    if self.path_isfile(candidate):
                        resolved_pf = candidate
                        break

                self.add_cmd_output(
                    f'{prefix} "sappfpar all pf={resolved_pf}"',
                    suggest_filename=f"{prof_name}_parameters"
                )

            sapcontrol_funcs = [
                ("GetProcessList", f"{sid}_{inst}_GetProcList"),
                ("GetVersionInfo", f"{sid}_{inst}_GetVersInfo"),
                ("GetEnvironment", f"{sid}_{lowsid}adm_{inst}_userenv"),
                ("GetSystemInstanceList",
                 f"{sid}_{inst}_GetSystemInstanceList"),
                ("GetStartProfile", f"{sid}_{inst}_GetStartProfile"),
                ("HAGetFailoverConfig", f"{sid}_{inst}_HAGetFailoverConfig"),
                ("HACheckFailoverConfig",
                 f"{sid}_{inst}_HACheckFailoverConfig"),
                ("HACheckConfig", f"{sid}_{inst}_HACheckConfig"),
            ]
            is_enq = (
                not info['inst_dirs'] or
                any(d.startswith(('ASCS', 'SCS', 'ERS'))
                    for d in info['inst_dirs'])
            )
            if is_enq:
                sapcontrol_funcs.append(
                    ("EnqGetStatistic", f"{sid}_{inst}_EnqGetStatistic")
                )
            for func, fname in sapcontrol_funcs:
                self.add_cmd_output(
                    f'{prefix} "sapcontrol -nr {inst} -function {func}"',
                    suggest_filename=fname
                )

            for inst_dir in sorted(info['inst_dirs']):
                inst_path = f"/usr/sap/{sid}/{inst_dir}"
                if self.path_isdir(f"{inst_path}/work"):
                    self.add_dir_listing(
                        f"{inst_path}/work",
                        suggest_filename=f"{sid}_{inst_dir}_work_ls"
                    )
                if self.path_isdir(f"{inst_path}/sec"):
                    self.add_dir_listing(
                        f"{inst_path}/sec",
                        suggest_filename=f"{sid}_{inst_dir}_sec_ls"
                    )

        for sid in sorted(sids):
            self.collect_sid_data(sid)

        return bool(instances or sids)

    def collect_sid_data(self, sid):
        """ Collect SID-level profiles, singleton work logs, and SDK state """
        lowsid = sid.lower()
        sidadm = f"{lowsid}adm"

        self.add_cmd_output(
            f'su - {sidadm} -c "disp+work -v"',
            suggest_filename=f"{sid}_disp_work_version"
        )

        # Profiles and <sid>adm environment files
        self.add_copy_spec([
            f"/usr/sap/{sid}/SYS/profile/*",
            f"/sapmnt/{sid}/profile/*",
            f"/home/{sidadm}/.sapenv*",
            f"/home/{sidadm}/.dbenv*",
        ])

        # Bounded singleton-only work directory logs (no dev_w1..99 or *.old)
        work_singletons = (
            "available.log",
            "Available.log",
            "sapstartsrv.log",
            "dev_sapstart",
            "*cluster_connector*.log",
            "dev_ms",
            "dev_enq_server",
            "dev_enq_replicator",
            "dev_enqsrv",
            "dev_enqrepl",
            "dev_enqwork",
            "dev_enrepsrv",
            "dev_enrepsig",
            "dev_disp",
            "dev_icm",
            "dev_icm_sec",
            "dev_rd",
            "dev_w0",
        )
        self.add_copy_spec([
            f"/usr/sap/{sid}/*/work/{fname}" for fname in work_singletons
        ])

        # SSFS directory listing (permissions/ownership check only)
        ssfs_data = f"/usr/sap/{sid}/SYS/global/security/rsecssfs/data"
        if self.path_isdir(ssfs_data):
            self.add_dir_listing(
                ssfs_data,
                suggest_filename=f"{sid}_rsecssfs_data_ls"
            )

        # ABAP SDK / BigQuery Connector for SLT gcloud checks
        gcloud_dir = f"/home/{sidadm}/.config/gcloud"
        if self.path_isdir(gcloud_dir):
            self.add_dir_listing(
                gcloud_dir,
                suggest_filename=f"{sid}_{sidadm}_gcloud_ls"
            )
            gcloud_logs = f"{gcloud_dir}/logs"
            if self.path_isdir(gcloud_logs):
                self.add_cmd_output(
                    f"du -sh {gcloud_logs}",
                    suggest_filename=f"{sid}_{sidadm}_gcloud_logs_du"
                )

    def collect_list_dbs(self):
        """ Collect data all the installed DBs """
        # list installed sap dbs
        db_list = self.collect_cmd_output(
            "/usr/sap/hostctrl/exe/saphostctrl -function ListDatabases",
            suggest_filename="SAPDatabases"
        )

        if db_list['status'] != 0:
            return False

        found_db = False
        for line in db_list['output'].splitlines():
            if "Instance name" in line:
                fields = line.strip().split()
                dbadm = fields[2][:-1]
                dbtype = fields[8][:-1]
                sid = dbadm[3:].upper()

                if dbtype == 'db6':
                    # IBM DB2
                    found_db = True
                    self.add_cmd_output(
                        f"su - {dbadm} -c \"db2 get dbm cfg\"",
                        suggest_filename=f"{sid}_{dbadm}_db2_info"
                    )

                elif dbtype == 'sap':
                    # SAP MAXDB
                    found_db = True
                    sid = fields[2][:-1]
                    self.add_copy_spec(
                        f"/sapdb/{sid}/data/config/{sid}.pah"
                    )

                elif dbtype == 'ora':
                    # Oracle
                    found_db = True
                    sid = fields[2][:-1]
                    self.add_copy_spec(f"/oracle/{sid}/*/dbs/init.ora")

                elif dbtype == 'syb':
                    # Sybase
                    found_db = True
                    sid = fields[2][:-1]
                    self.add_copy_spec(f"/sybase/{sid}/ASE*/{sid}.cfg")

        return found_db

    def setup(self):
        self.add_forbidden_path([
            "/usr/sap/*/*/sec/*.pse",
            "/usr/sap/*/*/sec/*.PSE",
            "/usr/sap/*/*/sec/*.p12",
            "/usr/sap/*/*/sec/*.key",
            "/usr/sap/*/SYS/global/security/rsecssfs/data/*",
            "/usr/sap/*/SYS/global/security/rsecssfs/key/*",
            "/usr/sap/*/SYS/profile/*.bak",
            "/usr/sap/*/SYS/profile/*.bkp",
            "/usr/sap/*/SYS/profile/*.old",
            "/usr/sap/*/SYS/profile/*.orig",
            "/usr/sap/*/SYS/profile/*.sav*",
            "/usr/sap/*/SYS/profile/*.lst",
            "/usr/sap/*/SYS/profile/*~",
            "/usr/sap/*/SYS/profile/*.[0-9]*",
            "/sapmnt/*/profile/*.bak",
            "/sapmnt/*/profile/*.bkp",
            "/sapmnt/*/profile/*.old",
            "/sapmnt/*/profile/*.orig",
            "/sapmnt/*/profile/*.sav*",
            "/sapmnt/*/profile/*.lst",
            "/sapmnt/*/profile/*~",
            "/sapmnt/*/profile/*.[0-9]*",
            "/home/*adm/.config/gcloud/*credentials*",
            "/home/*adm/.config/gcloud/access_tokens*",
            "/home/*adm/.config/gcloud/legacy_credentials/*",
        ])

        has_nw = self.collect_list_instances()
        has_db = self.collect_list_dbs()

        if has_nw or has_db:
            self.add_copy_spec([
                "/usr/sap/sapservices",
                "/usr/sap/hostctrl/exe/host_profile",
                "/usr/sap/hostctrl/work/sapstartsrv.log",
                "/usr/sap/hostctrl/work/dev_saphostexec",
                "/etc/systemd/system/SAP.slice",
                "/etc/systemd/system/SAP*.service",
                "/etc/systemd/system/SAP*.service.d/*.conf",
                "/usr/lib/systemd/system/SAP*.service",
            ])

            self.add_cmd_output([
                "systemd-cgls -u SAP.slice",
                'systemctl status "SAP*" saphostagent.service',
                'systemctl list-units "SAP*" saphostagent.service',
            ])

    def postproc(self):
        prof_path = (
            r".*(/usr/sap/.*/SYS/profile/.*|/sapmnt/.*/profile/.*|"
            r"/usr/sap/hostctrl/exe/host_profile|"
            r"/home/.*adm/\.(sap|db)env.*)"
        )
        secret_keys = (
            r"(?:password|passwd|pass|cred|credentials|secret|"
            r"private_key|client_secret)"
        )
        secret_val = r'(?:"[^"\r\n]*"|\'[^\'\r\n]*\'|\S+)'
        # Example: dbs/hdb/password = MySecret -> dbs/hdb/password = ********
        # Example: setenv dbs_hdb_password Secret -> ... ********
        secret_regex = (
            fr"(?i)((?:[\w/.-]*{secret_keys}[ \t]*=[ \t]*|"
            fr"\bsetenv[ \t]+[\w/.-]*{secret_keys}[ \t]+)){secret_val}"
        )
        self.do_path_regex_sub(prof_path, secret_regex, r"\1********")
        self.do_paths_http_sub([prof_path])
        self.do_cmd_output_sub("sappfpar", secret_regex, r"\1********")
        self.do_cmd_output_sub(
            "GetStartProfile", secret_regex, r"\1********"
        )

# vim: et ts=4 sw=4
