# Security Policy for sos

## Overview

The `sos` project collects system diagnostic and configuration data across various Linux distributions and enterprise environments. Because `sos` typically operates with elevated privileges (`root` or `sudo`) and processes sensitive system information—including passwords, certificates, and IP addresses via `sos clean`—we take security and privacy bugs seriously.

---

## Supported Versions

Security fixes and backports are provided based on the following version lifecycle:

| Version / Branch | Supported | Notes |
| :--- | :--- | :--- |
| `main` | :white_check_mark: | Active development branch |
| `4.12.x` (Current Major) | :white_check_mark: | Active release stream |
| Distro-bundled versions | :white_check_mark: | Maintained via respective distribution security advisories (RHEL, Ubuntu, SUSE, etc.) |
| `< 4.12` | :x: | End of Life (EOL) — Please upgrade to a supported release |

---

## What Qualifies as a Security Vulnerability?

Please privately report any issue that compromises system security or data privacy, including, but not limited to:

* **Privilege Escalation:** Flaws allowing unprivileged local users to execute arbitrary code, write to unauthorized files during diagnostic collection,
send unauthorised data over the network.
* **Secrets Obfuscation Failures (`postproc`):** Bugs where secrets
  (passwords, private keys, API tokens) that should be masked by a
  plugin's `postproc()` phase appear in plaintext in the collected
  archive. These are treated as security vulnerabilities.

  > **Note:** Incomplete PII redaction by `sos clean` (IP addresses,
  > hostnames, etc.) is handled through the normal bug-reporting
  > process and is **not** considered a security vulnerability.
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

1. **Initial Acknowledgment:** You will receive confirmation of your report within **NN hours**.
2. **Triage & Severity Assessment:** Maintainers will evaluate the issue and confirm impact within **N days**.
3. **Fix Development:** Fixes will be developed and verified in a private security advisory repository.
4. **Coordinated Release:**
   * A patch release and GitHub Security Advisory (GHSA) will be published.
   * If applicable, CVE identifiers will be requested and vendor security teams (Red Hat, Canonical, SUSE) notified prior to public disclosure.
5. **Public Disclosure:** Once a fix is available and distributed, the advisory will be made public. Reporters who wish to be credited will be acknowledged in the GHSA unless they prefer to remain anonymous.

---

## Thank You

We appreciate responsible disclosure. Coordinated reporting allows us to protect users across all distributions before details become public. If you have reported a vulnerability and have not heard back within a reasonable time, please follow up via the same private channel.
