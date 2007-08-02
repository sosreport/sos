%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

%define name sos
%define version 1.7
%define release 5

%define _localedir %_datadir/locale

Summary: A set of tools to gather troubleshooting information from a system
Name: %{name}
Version: %{version}
Release: %{release}%{?dist}
# The source for this package was pulled from upstream's svn.  Use the
# following commands to generate the tarball:
#  svn --username guest export https://sos.108.redhat.com/svn/sos/tags/r1-6 sos-1.6
#  tar -czvf sos-1.6.tar.gz sos-1.6
Source0: %{name}-%{version}.tar.gz
License: GPL
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch
Url: http://sos.108.redhat.com/
BuildRequires: python-devel
Requires: libxml2-python
Obsoletes: sysreport

%description
Sos is a set of tools that gathers information about system
hardware and configuration. The information can then be used for
diagnostic purposes and debugging. Sos is commonly used to help
support technicians and developers.

%prep
%setup -q

%build
python setup.py build

%install
rm -rf ${RPM_BUILD_ROOT}
python setup.py install --optimize 1 --root=$RPM_BUILD_ROOT
ln -s /usr/sbin/sosreport $RPM_BUILD_ROOT/usr/sbin/sysreport

%clean
rm -rf ${RPM_BUILD_ROOT}

%files
%defattr(-,root,root,-)
%{_sbindir}/sosreport
/usr/sbin/sysreport
/usr/sbin/sysreport.legacy
/usr/share/sysreport
%{python_sitelib}/sos/
%{_mandir}/man1/sosreport.1*
%{_localedir}/*/LC_MESSAGES/sos.mo
%doc README TODO LICENSE ChangeLog

%changelog
* Mon Aug  9 2007 Navid Sheikhol-Eslami <navid at redhat dot com> - 1.7-5
- package obsoletes sysreport and creates a link pointing to sosreport
- added some commands in cluster and process plugins
- fixed html output (wrong links to cmds, thanks streeter)
- process: back down sleep if D state doesn't change
- Resolves: bz241277 Yum Plugin for sos
- Resolves: bz247520 Spelling mistake in sosreport output
- Resolves: bz247531 Feature: plugin to gather initial ramdisk scripts
- Resolves: bz248252 sos to support language localization
- Resolves: bz241282 Make SOS for RHEL 4

* Mon Aug  1 2007 Navid Sheikhol-Eslami <navid at redhat dot com> - 1.7-4
- catch KeyboardInterrupt when entering sosreport name
- added color output for increased readability
- list was sorted twice, removing latter .sort()

* Mon Jul 31 2007 Navid Sheikhol-Eslami <navid at redhat dot com> - 1.7-3
- added preliminary problem diagnosis support
- better i18n initialization
- better user messages
- more progressbar fixes
- catch and log python exceptions in report
- use python native commands to create symlinks
- limit concurrent running threads

* Mon Jul 28 2007 Navid Sheikhol-Eslami <navid at redhat dot com> - 1.7-2
- initial language localization support
- added italian translation

* Mon Jul 16 2007 Navid Sheikhol-Eslami <navid at redhat dot com> - 1.7-1
- split up command outputs in sub-directories (sos_command/plugin/command instead of sos_command/plugin.command)
- fixed doExitCode() calling thread.wait() instead of join()
- curses menu is disabled by default
- multithreading is enabled by default
- major progressbar changes (now has ETA)
- multithreading fixes
- plugins class descriptions shortened to fix better in --list-plugins
- rpm -Va in plugins/rpm.py sets eta_weight to 200 (plugin 200 longer than other plugins, for ETA calculation)
- beautified command output filenames in makeCommandFilename()

* Mon Jul 12 2007 Navid Sheikhol-Eslami <navid at redhat dot com> - 1.7-0
- curses menu disabled by default (enable with -c)
- sosreport output friendlier to the user (and similar to sysreport)
- smarter plugin listing which also shows options and disable/enabled plugins
- require root permissions only for actual sosreport generation
- fix in -k where option value was treated as string instead of int
- made progressbar wider (60 chars)
- selinux plugin is enabled only if selinux is also enabled on the system
- made some errors less verbose to the user
- made sosreport not copy files pointed by symbolic links (same as sysreport, we don't need /usr/bin/X or /sbin/ifup)
- copy links as links (cp -P)
- added plugin get_description() that returns a short decription for the plugin
- guess sosreport name from system's name

* Mon Jul  5 2007 Navid Sheikhol-Eslami <navid at redhat dot com> - 1.6-5
- Yet more fixes to make package Fedora compliant.

* Mon Jul  5 2007 Navid Sheikhol-Eslami <navid at redhat dot com> - 1.6-4
- More fixes to make package Fedora compliant.

* Mon Jul  2 2007 Navid Sheikhol-Eslami <navid at redhat dot com> - 1.6-3
- Other fixes to make package Fedora compliant.

* Mon Jul  2 2007 Navid Sheikhol-Eslami <navid at redhat dot com> - 1.6-2
- Minor fixes.

* Mon Jul  2 2007 Navid Sheikhol-Eslami <navid at redhat dot com> - 1.6-1
- Beautified output of --list-plugins.
- GPL licence is now included in the package.
- added python-devel requirement for building package
- Resolves: bz241282 fixed incompatibility with python from RHEL4

* Fri May 25 2007 Steve Conklin <sconklin at redhat dot com> - 1.5-1
- Bumped version

* Fri May 25 2007 Steve Conklin <sconklin at redhat dot com> - 1.4-2
- Fixed a backtrace on nonexistent file in kernel plugin (thanks, David Robinson)

* Mon Apr 30 2007 Steve Conklin <sconklin at redhat dot com> - 1.4-1
- Fixed an error in option handling
- Forced the file generated by traceroute to not end in .com
- Fixed a problem with manpage
- Added optional traceroute collection to networking plugin
- Added clalance's patch to gather iptables info.
- Fixes to the device-mapper plugin
- Fixed a problem with installation of man page

* Mon Apr 16 2007 Steve Conklin <sconklin at redhat dot com> - 1.3-3
- including patches to fix the following:
- Resolves: bz219745 sosreport needs a man page
- Resolves: bz219667 sosreport does not terminate cleanly on ^C
- Resolves: bz233375 Make SOS flag the situation when running on a fully virtu...
- Resolves: bz234873 rhel5 sos needs to include rpm-va by default
- Resolves: bz219669 sosreport multi-threaded option sometimes fails
- Resolves: bz219671 RFE for sosreport - allow specification of plugins to be run
- Resolves: bz219672 RFE - show progress while sosreport is running
- Resolves: bz219673 Add xen information gathering to sosreport
- Resolves: bz219675 Collect information related to the new driver update model
- Resolves: bz219877 'Cancel' button during option selection only cancels sele...

* Tue Feb 20 2007 John Berninger <jwb at redhat dot com> - 1.3-2
- Add man page

* Fri Dec 15 2006 Steve Conklin <sconklin at redhat dot com> - 1.3-1
- really fixed bz_219654

* Fri Dec 15 2006 Steve Conklin <sconklin at redhat dot com> - 1.2-1
- fixed a build problem

* Fri Dec 15 2006 Steve Conklin <sconklin at redhat dot com> - 1.1-1
- Tighten permissions of tmp directory so only readable by creator bz_219657
- Don't print message 'Problem at path ...'  bz_219654
- Removed useless message bz_219670
- Preserve file modification times bz_219674
- Removed unneeded message about files on copyProhibitedList bz_219712

* Wed Aug 30 2006 Steve Conklin <sconklin at redhat dot com> - 1.0-1
- Seperated upstream and RPM versioning

* Mon Aug 21 2006 Steve Conklin <sconklin at redhat dot com> - 0.1-11
- Code cleanup, fixed a regression in threading

* Mon Aug 14 2006 Steve Conklin <sconklin at redhat dot com> - 0.1-10
- minor bugfixes, added miltithreading option, setup now quiet

* Mon Jul 17 2006 Steve Conklin <sconklin at redhat dot com> - 0.1-9
- migrated to svn on 108.redhat.com, fixed a problem with command output linking in report

* Mon Jun 19 2006 Steve Conklin <sconklin at redhat dot com> - 0.1-6
- Added LICENSE file containing GPL

* Wed May 31 2006 Steve Conklin <sconklin at redhat dot com> - 0.1-5
- Added fixes to network plugin and prepped for Fedora submission

* Wed May 31 2006 John Berninger <jwb at redhat dot com> - 0.1-4
- Reconsolidated subpackages into one package per discussion with sconklin

* Mon May 22 2006 John Berninger <jwb at redhat dot com> - 0.1-3
- Added ftp, ldap, mail, named, samba, squid SOS plugins
- Fixed various errors in kernel and hardware plugins

* Mon May 22 2006 John Benringer <jwb at redhat dot com> - 0.1-2
- split off cluster plugin into subpackage
- correct file payload lists

* Mon May 22 2006 John Berninger <jwb at redhat dot com> - 0.1-1
- initial package build
