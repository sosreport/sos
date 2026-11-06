# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from collections import deque
import os
import re
from sos.report.plugins import Plugin, RedHatPlugin


class Saphana(Plugin, RedHatPlugin):
    """Collects diagnostic data on SAP HANA databases, including custom .ini
    and Backint configuration files, HDB/hdbsrvutil/hdbcons/hdbnsutil state,
    sapcontrol instance and HA status, HDBSettings.sh Python support scripts,
    HA/DR hook (susHanaSR/SAPHanaSR/ChkSrv) trace entries, and trace
    directory listings.
    """

    short_desc = 'SAP HANA'
    plugin_name = 'saphana'
    profiles = ('sap',)
    files = ('/hana', '/usr/sap/*/HDB[0-9][0-9]')
    trace_dirs = ()

    def setup(self):
        self.trace_dirs = []
        # Exclude SSFS encrypted stores/keys and PSE/PKCS#12 private keystores
        self.add_forbidden_path([
            "/hana/shared/*/global/security/rsecssfs/data/*",
            "/hana/shared/*/global/security/rsecssfs/key/*",
            "/usr/sap/*/SYS/global/security/rsecssfs/data/*",
            "/usr/sap/*/SYS/global/security/rsecssfs/key/*",
            "/usr/sap/*/*/sec/*.pse",
            "/usr/sap/*/*/sec/*.PSE",
            "/usr/sap/*/*/sec/*.p12",
            "/usr/sap/*/*/sec/*.key",
        ])

        sids = set()

        for base in ("/hana/shared", "/usr/sap"):
            if not self.path_isdir(base):
                continue
            for sid in self.listdir(base):
                sid = sid.strip()
                if not re.match(r'^[A-Z][A-Z0-9]{2}$', sid):
                    continue
                sid_path = f"{base}/{sid}"
                if not self.path_isdir(sid_path):
                    continue
                if self.path_isdir(f"{sid_path}/global/hdb"):
                    sids.add(sid)
                    continue
                for entry in self.listdir(sid_path):
                    if re.match(r'^HDB[0-9]{2}$', entry.strip()):
                        sids.add(sid)
                        break

        if sids:
            self.add_cmd_output([
                "SAPHanaSR-showAttr",
                "systemd-cgls -u SAP.slice",
                'systemctl status "SAP*" saphostagent.service',
                'systemctl list-units "SAP*" saphostagent.service',
            ])

        for sid in sorted(sids):
            sidadm = f'{sid.lower()}adm'
            # Use 'su -' instead of runas= so <sid>adm's login profile is
            # sourced (setting PATH, LD_LIBRARY_PATH, and DIR_INSTANCE)
            prefix = f'su - {sidadm} -c'

            self.add_copy_spec([
                f"/hana/shared/{sid}/global/hdb/custom/config/*.ini",
                f"/hana/shared/{sid}/global/hdb/custom/config/DB_*/*.ini",
                f"/usr/sap/{sid}/SYS/global/hdb/custom/config/*.ini",
                f"/usr/sap/{sid}/SYS/global/hdb/custom/config/DB_*/*.ini",
                f"/hana/shared/{sid}/global/hdb/opt/backint/parameters.json",
                f"/hana/shared/{sid}/global/hdb/opt/backint/*/parameters.json",
                f"/hana/shared/{sid}/global/hdb/opt/hdbbackint/*.utl",
                f"/hana/shared/{sid}/global/hdb/opt/hdbconfig/*",
                f"/usr/sap/{sid}/SYS/global/hdb/opt/backint/parameters.json",
                f"/usr/sap/{sid}/SYS/global/hdb/opt/backint/*/parameters.json",
                f"/usr/sap/{sid}/SYS/global/hdb/opt/hdbbackint/*.utl",
                f"/usr/sap/{sid}/SYS/global/hdb/opt/hdbconfig/*",
            ])

            self.add_cmd_output(f'{prefix} "HDB info"',
                                suggest_filename=f"{sid}_HDB_info")

            self.add_cmd_output(f'{prefix} "hdbsrvutil -v"',
                                suggest_filename=f"{sid}_version")

            self.add_cmd_output(f'{prefix} \'hdbcons "mm l -s -S -p"\'',
                                suggest_filename=f"{sid}_memusage")

            repl_cmd = (f'{prefix} \'hdbcons -e hdbindexserver '
                        '"replication info"\'')
            self.add_cmd_output(repl_cmd,
                                suggest_filename=f"{sid}_replicainfo")

            self.add_cmd_output(f'{prefix} "hdbnsutil -sr_state"',
                                suggest_filename=f"{sid}_sr_state")

            self.add_cmd_output(
                f'{prefix} "hdbnsutil -sr_stateConfiguration"',
                suggest_filename=f"{sid}_sr_stateConfiguration"
            )

            insts = set()
            for base in (f"/hana/shared/{sid}", f"/usr/sap/{sid}"):
                if self.path_isdir(base):
                    for entry in self.listdir(base):
                        entry = entry.strip()
                        if re.match(r'^HDB[0-9]{2}$', entry):
                            insts.add(entry[-2:])

            for inst in sorted(insts):
                self.get_inst_info(sid, sidadm, inst)

    def get_inst_info(self, sid, sidadm, inst):
        """ Collect the given instance info """
        prefix = f'su - {sidadm} -c'

        proc_cmd = f'{prefix} "sapcontrol -nr {inst} -function GetProcessList"'
        proc = self.collect_cmd_output(
            proc_cmd, suggest_filename=f"{sid}_{inst}_status"
        )

        for func in (
            "GetSystemInstanceList",
            "GetVersionInfo",
            "HAGetFailoverConfig",
            "HACheckConfig",
        ):
            self.add_cmd_output(
                f'{prefix} "sapcontrol -nr {inst} -function {func}"',
                suggest_filename=f"{sid}_{inst}_{func}"
            )

        py_dirs = (
            f"/usr/sap/{sid}/HDB{inst}/exe/python_support",
            f"/hana/shared/{sid}/HDB{inst}/exe/python_support",
        )
        if any(self.path_isdir(p) for p in py_dirs):
            py_scripts = [
                ("landscapeHostConfiguration.py", "landscapeConfig"),
                ("systemReplicationStatus.py", "systemReplicationStatus"),
            ]
            if proc['status'] in (0, 3):
                py_scripts.append(("systemOverview.py", "systemOverview"))

            for script, suffix in py_scripts:
                self.add_cmd_output(
                    f'{prefix} "HDBSettings.sh {script}"',
                    suggest_filename=f"{sid}_{inst}_{suffix}"
                )

        self.collect_trace_listing(sid, inst)

    def collect_trace_listing(self, sid, inst):
        """ List trace directories without copying bulk .trc files """
        inst_root = None
        for candidate in (f"/usr/sap/{sid}/HDB{inst}",
                          f"/hana/shared/{sid}/HDB{inst}"):
            if self.path_isdir(candidate):
                inst_root = candidate
                break

        if not inst_root:
            return

        for entry in sorted(self.listdir(inst_root)):
            trace_dir = f"{inst_root}/{entry}/trace"
            if not self.path_isdir(trace_dir):
                continue
            self.trace_dirs.append((sid, inst, entry, trace_dir))
            self.add_copy_spec([
                f"{trace_dir}/nameserver_*sushana*.trc",
                f"{trace_dir}/nameserver_*saphanasr*.trc",
                f"{trace_dir}/nameserver_*chksrv*.trc",
                f"{trace_dir}/nameserver_*tkover*.trc",
            ])
            self.add_dir_listing(
                trace_dir,
                suggest_filename=f"{sid}_HDB{inst}_{entry}_trace_ls"
            )
            for sub in sorted(self.listdir(trace_dir)):
                sub_dir = f"{trace_dir}/{sub}"
                if sub.startswith("DB_") and self.path_isdir(sub_dir):
                    self.add_dir_listing(
                        sub_dir,
                        suggest_filename=(
                            f"{sid}_HDB{inst}_{entry}_trace_{sub}_ls"
                        )
                    )

    def collect(self):
        """ Extract HA/DR provider (susHanaSR/SAPHanaSR/ChkSrv) events from
        nameserver trace files without copying multi-GB raw .trc files """
        if not self.trace_dirs:
            return

        ns_trc_re = re.compile(
            r'^nameserver_[^.]+\.3[0-9]{4}\.[0-9]{3}\.trc$'
        )
        ha_dr_re = re.compile(
            r'ha_dr_|sushana|saphanasr|suschksrv|sustkover|chksrv|'
            r'srconnectionchanged|srservicestatechanged|'
            r'pretakeover|posttakeover',
            re.I
        )

        for sid, inst, entry, trace_dir in self.trace_dirs:
            if not self.path_isdir(trace_dir):
                continue
            candidates = []
            for fname in self.listdir(trace_dir):
                fname = fname.strip()
                if not ns_trc_re.match(fname):
                    continue
                full_path = self.path_join(f"{trace_dir}/{fname}")
                try:
                    mtime = os.path.getmtime(full_path)
                except OSError:
                    mtime = 0
                candidates.append((mtime, fname, full_path))

            candidates.sort()
            matched = deque(maxlen=5000)
            for _, fname, full_path in candidates[-20:]:
                try:
                    with open(full_path, 'r', encoding='utf-8',
                              errors='ignore') as tfile:
                        for line in tfile:
                            if ha_dr_re.search(line):
                                matched.append(f"{fname}:{line}")
                except OSError as err:
                    self._log_debug(f"Could not read {full_path}: {err}")
                    continue

            if matched:
                out_name = (
                    f"{sid}_HDB{inst}_{entry}_nameserver_sushanasr_trc"
                )
                with self.collection_file(out_name) as cfile:
                    cfile.write("".join(matched))

    def postproc(self):
        ini_path = (
            r".*(/hana/shared|/usr/sap)/.*/global/hdb/custom/config/.*\.ini$"
        )
        ini_keys = (
            r"(?:password|passwd|pass|secret|private_key|private_key_id|"
            r"client_secret|encryption_key|kms_key|kms_key_name)"
        )
        ini_val = r'(?:"[^"\r\n]*"|\'[^\'\r\n]*\'|\S+)'
        # Example: password = mysecret -> password = ********
        ini_regex = (
            fr"(?i)(^[ \t]*#?[ \t]*[\w/.-]*{ini_keys}[ \t]*=[ \t]*){ini_val}"
        )
        self.do_path_regex_sub(ini_path, ini_regex, r"\1********")

        opt_path = (
            r".*(/hana/shared|/usr/sap)/.*/global/hdb/opt/"
            r"(hdbconfig/.*|.*\.(json|utl))$"
        )
        # Example: "encryption_key": "secret" -> "encryption_key": "********"
        json_regex = fr'(?i)("[\w/.-]*{ini_keys}"[ \t]*:[ \t]*)"[^"]*"'
        # Example: PASSWORD mysecret -> PASSWORD ********
        utl_regex = (
            fr"(?i)(^[ \t]*#?[ \t]*[\w/.-]*{ini_keys}"
            fr"(?:[ \t]*=[ \t]*|[ \t]+)){ini_val}"
        )
        self.do_path_regex_sub(opt_path, json_regex, r'\1"********"')
        self.do_path_regex_sub(opt_path, utl_regex, r"\1********")

        self.do_paths_http_sub([ini_path, opt_path])

# vim: et ts=4 sw=4
