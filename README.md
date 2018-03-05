[![Build Status](https://travis-ci.org/sosreport/sos.svg?branch=master)](https://travis-ci.org/sosreport/sos)

# SoS

Sos is an extensible, portable, support data collection tool primarily
aimed at Linux distributions and other UNIX-like operating systems.

This project is hosted at:

  * http://github.com/sosreport/sos

For the latest version, to contribute, and for more information, please visit
the project pages or join the mailing list.

To clone the current master (development) branch run:

```
git clone git://github.com/sosreport/sos.git
```
## Reporting bugs

Please report bugs via the mailing list or by opening an issue in the [GitHub
Issue Tracker][5]

## Mailing list

The [sos-devel][4] is the mailing list for any sos-related questions and
discussion. Patch submissions and reviews are welcome too.

## Patches and pull requests

Patches can be submitted via the mailing list or as GitHub pull requests. If
using GitHub please make sure your branch applies to the current master as a
'fast forward' merge (i.e. without creating a merge commit). Use the `git
rebase` command to update your branch to the current master if necessary.

Please refer to the [contributor guidelines][0] for guidance on formatting
patches and commit messages.

## Documentation

User and API [documentation][6] is automatically generated using [Sphinx][7]
and [Read the Docs][8].

To generate HTML documents locally, install dependencies using

```
pip install -r requirements.txt
```

and run

```
make
```

Please run `make test` before sending a [pull request][0], or run the
test suite manually using the `nosetests` command (ideally for the
set of Python versions currently supported by `sos` upstream).

### Wiki

* [How to write a plugin][1]
* [How to write a policy][2]
* [Plugin options][3]

To help get your changes merged quickly with as few revisions as possible
please refer to the [Contributor Guidelines][0] when submitting patches or
pull requests.

## Installation

### Manual Installation

You can simply run from the git checkout now:
```
$ sudo ./sosreport -a
```

Or, if you only have python3 installed:
```
$ sudo python3 ./sosreport -a
```

* Note: the `sosreport` command requires a configuration file: if no `sos.conf`
is present in the `/etc` directory (i.e. no system installation of sos exists),
use the `--config` option to provide one:
```
$ sudo python ./sosreport -a --config ./sos.conf
```

To install locally (as root):
```
# make install
```

To build an rpm:
```
$ make rpm
```

### Pre-built Packaging

Fedora/RHEL users install via yum:

```
yum install sos
```

Debian users install via apt:

```
apt install sosreport
```


Ubuntu (14.04 LTS and above) users install via apt:

```
sudo apt install sosreport
```

 [0]: https://github.com/sosreport/sos/wiki/Contribution-Guidelines
 [1]: https://github.com/sosreport/sos/wiki/How-to-Write-a-Plugin
 [2]: https://github.com/sosreport/sos/wiki/How-to-Write-a-Policy
 [3]: https://github.com/sosreport/sos/wiki/Plugin-options
 [4]: https://www.redhat.com/mailman/listinfo/sos-devel
 [5]: https://github.com/sosreport/sos/issues?state=open
 [6]: http://sos.readthedocs.org/en/latest/index.html#
 [7]: http://sphinx-doc.org/
 [8]: https://www.readthedocs.org/
