# Sanitize-report Phase 25/26/27 Engineering Checkpoint

## State

- Branch: `ardeoliv-sanitize-report`
- Current phase: Phase 28 diagnostic hardening
- Source test archive: private local fixture; not committed
- Source SHA256: recorded in private run logs; not committed
- Inventory: 0 unsupported regular objects; 3 expected FIFO omissions
- Focused baseline: 199 passed, 0 failures, 0 errors, 0 skipped

The source archive is a read-only test input and must remain byte-for-byte
unchanged.

## Architecture and security invariants

- Unknown artifacts fail closed.
- Extraction uses private staging, no-follow traversal, and safe internal
  symlink handling.
- Unsafe hardlinks and special objects are rejected or omitted only by an
  explicitly reviewed policy.
- Metadata application uses verified file descriptors; there is no unsafe
  path-following chmod fallback.
- One global sanitization session provides deterministic mappings.
- Secrets never enter mappings.
- Mappings are stabilized before output and cannot grow after freeze.
- Tree residual validation is mandatory.
- Final archive residual validation is independent and mandatory.
- Compressed transformed artifacts are decompressed and inspected before
  recompression; compressed bytes are not treated as a privacy blind spot.
- Omitted artifacts cannot reappear in the sanitized tree or archive.
- The mapping file is private and published with mode 0600.
- The normal CLI failure remains the generic message `report sanitization
  failed`.
- No artifact policy is broadened without explicit review.

## Implemented policies

### Phase 25 omissions

- POSIX-literal symlink-target sanitization with containment checks.
- Corosync authkey exact-path omission.
- SELinux compiled file-context cache omission for the two approved targeted
  cache paths.
- SELinux compiled kernel-policy omission for validated `policy.N` files and
  the approved active `policy.kern`.
- Process-environment omission for bounded canonical `proc/PID/environ` paths.
- DRM connector EDID omission.
- SELinux active-store omission for reviewed HLL payloads, derived CIL caches,
  linked/kernel policy artifacts, checksums, commit metadata, and language
  markers.
- ACPI firmware-table, systemd-coredump, runtime-reference, and approved
  timezone/TZif omission families.

### Phase 25 transformations

- Pacemaker `pe-input-N.bz2` bounded decode, constrained XML/credential
  handling, shared identity sanitization, residual validation, and
  deterministic recompression.
- Corosync `var/log/cluster/corosync.log-YYYYMMDD.gz` bounded strict-UTF-8
  sanitization, residual validation, and deterministic recompression.
- Approved Pacemaker and SSSD compressed-log handling remains path-scoped.
- The authoritative direct-CIL module uses bounded token-aware sanitization
  and remains distinct from derived CIL caches.

### Phase 26

- Archive-order extraction optimization with private, validated extraction and
  source immutability.

### Phase 27/28

- Residual known-original matching uses an in-repository multi-pattern literal
  matcher with reference-regex fallback where required. A representative
  benchmark improved from 7.366 seconds to 0.133 seconds (~55x).
- Residual errors carry only a safe category and relative path internally.
- Tree and top-level sanitizer wrappers preserve safe exception causes while
  the CLI remains generic.

## Specialized counters

Current tree counters include: `binary_files_omitted`,
`cluster_authkeys_omitted`, `timezone_files_omitted`,
`selinux_binary_contexts_omitted`, `selinux_binary_policies_omitted`,
`selinux_module_hll_payloads_omitted`, `selinux_module_cil_caches_omitted`,
`selinux_linked_policies_omitted`, `selinux_policy_store_metadata_omitted`,
`selinux_module_language_metadata_omitted`, `selinux_direct_cil_sanitized`,
`process_environments_omitted`, `pacemaker_scheduler_inputs_sanitized`,
`display_edids_omitted`, `corosync_logs_sanitized`,
`pacemaker_logs_sanitized`, `sssd_logs_omitted`, `acpi_tables_omitted`, and
`systemd_coredump_helpers_omitted`.

## Authoritative-run history and performance

- Prior authoritative run: 1:41:50, approximately 6105.75 seconds user CPU,
  99% CPU, no published output.
- Phase 27 retry: 33:40.37, 2015.36 seconds user CPU, 2.57 seconds system CPU,
  99% CPU, 568648 KB maximum RSS, no published output.
- Extraction after Phase 26: approximately 5.2 seconds on the real RHEL
  archive.

These are engineering baselines, not CI limits. The remaining failure was
reported generically at tree residual validation; safe internal exception
chaining now makes the cause inspectable without weakening fail-closed CLI
behavior.

## Current blocker and acceptance gates

The next step is a targeted tree-residual reproduction using a private staged
tree and frozen private mapping metadata. Do not run the full sanitizer until
the residual failure is reproduced and understood.

Before commit, require focused security/regression tests, a clean diff, a
complete unsupported-artifact inventory of zero, a successful authoritative
run, independent tree/archive residual validation, source SHA preservation,
private mapping publication, output structural validation, and final privacy
review.

## Explicit do-not-change invariants

Do not weaken residual matching, remove archive residual validation, follow
symlinks, use path-based chmod that can follow a race, expose mappings or
secrets, broaden artifact grammars, mutate the source archive, or change the
generic CLI error merely to expose diagnostics.
