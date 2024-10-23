[![Build Status](https://api.cirrus-ci.com/github/sosreport/sos.svg?branch=main)](https://cirrus-ci.com/github/sosreport/sos) [![Documentation Status](https://readthedocs.org/projects/sos/badge/?version=main)](https://sos.readthedocs.io/en/main/?badge=main) [![sosreport](https://snapcraft.io/sosreport/badge.svg)](https://snapcraft.io/sosreport)


# SoS

Sos is an extensible, portable, support data collection tool primarily
aimed at Linux distributions and other UNIX-like operating systems.

This project is hosted at:

  * https://github.com/sosreport/sos

For the latest version, to contribute, and for more information, please visit
the project pages or join the mailing list.

To clone the current main (development) branch run:

```
git clone git://github.com/sosreport/sos.git
```

## Reporting bugs

Please report bugs via the mailing list or by opening an issue in the [GitHub
Issue Tracker][5]

## Chat

The SoS project has rooms in Matrix and in Libera.Chat.

Matrix Room: #sosreport:matrix.org

Libera.Chat: #sos

These rooms are bridged, so joining either is sufficient as messages from either will
appear in both.

The Freenode #sos room **is no longer used by this project**.

## Mailing list

The [sos-devel][4] list is the mailing list for any sos-related questions and
discussion. Patch submissions and reviews are welcome too.

## Patches and pull requests

Patches can be submitted via the mailing list or as GitHub pull requests. If
using GitHub please make sure your branch applies to the current main branch as a
'fast forward' merge (i.e. without creating a merge commit). Use the `git
rebase` command to update your branch to the current main if necessary.

Please refer to the [contributor guidelines][0] for guidance on formatting
patches and commit messages.

Before sending a [pull request][0], it is advisable to check your contribution
against the `flake8` linter, the unit tests, and the stage one avocado test suite:

```
# from within the git checkout
$ flake8 sos
$ nosetests -v tests/unittests/

# sudo PYTHONPATH=tests/ avocado run --test-runner=runner -t stageone tests/{cleaner,collect,report,vendor}_tests
```

For further test run stagetwo tests
```
# sudo PYTHONPATH=tests/ avocado run --test-runner=runner -t stagetwo tests/{cleaner,collect,report,vendor}_tests
```

If you want to check basic scrub tests
```
# sudo PYTHONPATH=tests/ avocado run --test-runner=runner -t scrub tests/{cleaner,collect,report,vendor}_tests
```

Note that the avocado test suite will generate and remove several reports over its
execution, but no changes will be made to your local system.

All contributions must pass the entire test suite before being accepted.

## Documentation

User and API [documentation][6] is automatically generated using [Sphinx][7]
and [Read the Docs][8].

To generate HTML documents locally, install dependencies using

```
pip install -r requirements.txt
```

and run

```
sphinx-build -b html docs <destination dir> 
```


### Wiki

For more in-depth information on the project's features and functionality, please
see [the GitHub wiki][9].

If you are interested in contributing an entirely new plugin, or extending sos to
support your distribution of choice, please see these wiki pages:

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
$ sudo ./bin/sos report 
```
The command `sosreport` is still available, as a legacy redirector,
and can be used like this:
```
$ sudo ./bin/sosreport 
```

To see a list of all available plugins and plugin options, run
```
$ sudo ./bin/sos report -l
```


To install locally (as root):
```
# python3 setup.py install
```


### Pre-built Packaging

Fedora/RHEL users install via yum:

```
# yum install sos
```

Debian users install via apt:

```
# apt install sosreport
```


Ubuntu (14.04 LTS and above) users install via apt:

```
# sudo apt install sosreport
```

### Snap Installation

```
# snap install sosreport --classic
```

 [0]: https://github.com/sosreport/sos/wiki/Contribution-Guidelines
 [1]: https://github.com/sosreport/sos/wiki/How-to-Write-a-Plugin
 [2]: https://github.com/sosreport/sos/wiki/How-to-Write-a-Policy
 [3]: https://github.com/sosreport/sos/wiki/Plugin-options
 [4]: https://www.redhat.com/mailman/listinfo/sos-devel
 [5]: https://github.com/sosreport/sos/issues?state=open
 [6]: https://sos.readthedocs.org/
 [7]: https://www.sphinx-doc.org/
 [8]: https://www.readthedocs.org/
 [9]: https://github.com/sosreport/sos/wiki
