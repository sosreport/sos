# Security Policy for sos

## Overview

The `sos` project collects system diagnostic and configuration data across various Linux distributions and enterprise environments. Because `sos` typically operates with elevated privileges (`root` or `sudo`) and processes sensitive system information—including passwords, certificates, and IP addresses via `sos clean`—we take security and privacy bugs seriously.

---

## Supported Versions

Security fixes and backports are provided based on the following version lifecycle:

| Version / Branch | Supported | Notes |
| :--- | :--- | :--- |
| `main` | :white_check_mark: | Active development branch |
| `4.x` (Current Major) | :white_check_mark: | Active release stream |
| Distro-bundled versions | :white_check_mark: | Maintained via respective distribution security advisories (RHEL, Ubuntu, SUSE, etc.) |
| `< 4.0` | :x: | End of Life (EOL) — Please upgrade to a supported release |

Only the latest tag within the current major release stream receives security backports. When a security fix cannot wait for the next minor release, a patch tag (for example `4.12.0.1`) may be created so that distributions can pick up the fix.

---

## What Qualifies as a Security Vulnerability?

Please privately report any issue that compromises system security, including, but not limited to:

* **Privilege Escalation:** Flaws allowing unprivileged local users to execute arbitrary code or write to unauthorized files during diagnostic collection.
* **Unauthorized Data Transmission:** Flaws that send data over the network without authorization or user consent.
* **Unsafe File Handling & Symlink Traversal:** Insecure creation or manipulation of temporary archives in `/tmp` or staging locations.
* **Credential Exposure in `sos upload`:** Hardcoded, logged, or unencrypted transfer of credentials during archive transport.

---

## Reporting a Vulnerability

**DO NOT report suspected security vulnerabilities through public GitHub issues, pull requests, or public mailing lists.**

### Preferred Reporting Method

Use GitHub's **Private Vulnerability Reporting**:
1. Go to the sosreport/sos Security Tab.
2. Click **"Report a vulnerability"**.
3. Fill in the details and submit privately to the core security maintainers.

---

## Obfuscation and Data Exposure Bugs

The obfuscation performed by `sos`, both the default secrets scrubbing during collection (`postproc()`) and the cleaning performed by `sos clean`, targets well-known forms of sensitive data in well-known locations, typically configuration files, on a best-effort basis. No guarantee of complete coverage is made: we cannot monitor every project `sos` has plugins for, and newly introduced fields or patterns may not be covered until reported. The collection of a file that contains plaintext secrets is not itself a vulnerability, since `sos` copies files as they exist on the system.

Obfuscation gaps and data exposure issues of this kind are therefore considered outside the security vulnerability procedure described in this document, including its response timelines and coordinated disclosure process.

However, since these bugs can still expose sensitive data, we ask that you:

* Report them privately via GitHub's Private Vulnerability Reporting rather than through public GitHub issues. These reports will not be tracked as security advisories and no CVE will be requested for them.
* Refrain from public disclosure until a fix is available.
* Include a proposed fix (pull request) where possible.

While we make no formal commitment under this policy for these issues, we do promise a quick turnaround in reviewing and merging fixes for them upstream.

---

## What to Include in Your Report

To help us triage and respond quickly, please include:
1. **Description:** A detailed explanation of the vulnerability and its potential impact.
2. **Affected Component:** Subsystem or plugin involved (e.g., `sos/cleaner/`, `sos/upload/`, `sos/policies/`, etc...).
3. **Environment:** Distribution name, version, and `sos` release version (`sos report --version`).
4. **Reproduction Steps:** A minimal proof-of-concept (PoC) or command sequence to reproduce the issue in the environment described above.
5. **sos Report (optional):** If you believe an actual or anonymised `sos report` archive would help clarify the issue or speed up diagnosis, you are welcome to attach one either from a real system or generated with mocked data.

---

## Response Timeline & Coordinated Disclosure

This project follows the **Coordinated Vulnerability Disclosure (CVD)** principles:

1. **Initial Acknowledgment:** You will receive confirmation of your report within **72 hours**.
2. **Triage & Severity Assessment:** Maintainers will evaluate the issue and confirm impact within **7 days**.
3. **Fix Development:** Fixes will be developed and verified in a private security advisory repository.
4. **Coordinated Release:**
   * A patch release and GitHub Security Advisory (GHSA) will be published.
   * If applicable, CVE identifiers will be requested and vendor security teams (Red Hat, Canonical, SUSE) notified prior to public disclosure.
5. **Public Disclosure:** Once a fix is available and distributed, the advisory will be made public. Reporters who wish to be credited will be acknowledged in the GHSA unless they prefer to remain anonymous.

---

## Thank You

We appreciate responsible disclosure. Coordinated reporting allows us to protect users across all distributions before details become public. If you have reported a vulnerability and have not heard back within a reasonable time, please follow up via the same private channel.
