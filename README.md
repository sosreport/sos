[![Build Status](https://travis-ci.org/sosreport/sos.svg?branch=master)](https://travis-ci.org/sosreport/sos)

This set of tools is designed to provide information to support organizations
in an extensible manner, allowing third parties, package maintainers, and
anyone else to provide plugins that will collect and report information that
is useful for supporting software packages.

This project is hosted at http://github.com/sosreport/sosreport For the latest
version, to contribute, and for more information, please visit there.

To access to the public source code repository for this project run:

```
git clone git://github.com/sosreport/sosreport.git
```

### Contributors please read

Because of our vibrant community and everyone does things a little differently we've setup a wiki page dedicated to [sosreport's contribution guidelines][0].

In order to get your requests merged in a timely manner these guidelines are mandatory.

### Manual Installation

```
to install locally (as root) ==> make install
to build an rpm ==> make rpm
to build a deb ==> make deb
```

### Pre-built Packaging

Fedora/RHEL users install via yum:

```
yum install sos
```

Debian(Sid) users install via apt:

```
apt-get install sosreport
```


Ubuntu(Saucy 13.10 and above) users install via apt:

```
sudo apt-get install sosreport
```

 [0]: https://github.com/sosreport/sosreport/wiki/Contribution-Guidelines
