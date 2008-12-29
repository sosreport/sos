%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

%define _localedir %_datadir/locale

Summary: A set of tools to gather troubleshooting information from a system
Name: sos
Version: 1.8
Release: 5%{?dist}
Group: Application/Tools
Source0: https://fedorahosted.org/releases/s/o/sos/%{name}-%{version}.tar.gz
License: GPLv2
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch
Url: http://fedorahosted.org/sos
BuildRequires: python-devel
Requires: libxml2-python
Provides: sysreport = 1.4.3-13
Obsoletes: sysreport

%description
Sos is a set of tools that gathers information about system
hardware and configuration. The information can then be used for
diagnostic purposes and debugging. Sos is commonly used to help
support technicians and developers.

%prep
%setup -q

%build
%{__python} setup.py build

%install
rm -rf ${RPM_BUILD_ROOT}
install -D -m644 gpgkeys/rhsupport.pub ${RPM_BUILD_ROOT}/usr/share/sos/rhsupport.pub
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT
ln -s /usr/sbin/sosreport $RPM_BUILD_ROOT/usr/sbin/sysreport

%clean
rm -rf ${RPM_BUILD_ROOT}

%files
%defattr(-,root,root,-)
%{_bindir}/rh-upload-core
%{_sbindir}/sosreport
%{_sbindir}/sysreport
%{_sbindir}/sysreport.legacy
/usr/share/sysreport
/usr/share/sos/rhsupport.pub
%{python_sitelib}/sos/
%{_mandir}/man1/sosreport.1.gz
%{_localedir}/*/LC_MESSAGES/sos.mo
%doc README README.rh-upload-core TODO LICENSE ChangeLog
%config %{_sysconfdir}/sos.conf

%changelog
* Mon Dec 29 2008 Adam Stokes <ajs at redhat dot com> - 1.8-5
- removed source defines as python manifest handles this

* Fri Dec 19 2008 Adam Stokes <ajs at redhat dot com> - 1.8-4
- spec cleanup, fixed license, source
- reworked Makefile to build properly

* Thu Oct 23 2008 Adam Stokes <astokes at redhat dot com> - 1.8-1
- Resolves: bz459845 collect krb5.conf
- Resolves: bz457880 include output of xm list and xm list --long
- Resolves: bz457919 add support for openswan and ipsec-tools
- Resolves: bz456378 capture elilo configuration
- Resolves: bz445007 s390 support
- Resolves: bz371251 hangs when running with a xen kernel where xend has not been started
- Resolves: bz452705 Add /root/anaconda-ks-cfg to sosreport archive
- Resolves: bz445510 Do not rely on env to execute python
- Resolves: bz446868 add support for emc devices
- Resolves: bz453797 fails to generate fdisk -l
- Resolves: bz433183 does not collect ext3 information
- Resolves: bz444838 systool is passed deprecated arguments
- Resolves: bz455096 add %{INSTALLTIME:date} to rpm --qf collection
- Resolves: bz332211 avoid hazardous filenames

* Wed Nov 21 2007 Navid Sheikhol-Eslami <navid at redhat dot com> - 1.8-0
- Resolves: bz368261 sosGetCommandOutput() does not block on hung processes
- Resolves: bz361861 work-around missing traceback.format_exc() in RHEL4
- Resolves: bz394781 device-mapper: use /sbin/lvm_dump to collect dm related info
- Resolves: bz386691 unattended --batch option
- Resolves: bz371251 sos could hang when accessing /sys/hypervisor/uuid
- selinux: always collect sestatus
- added many languages
- added --debug option which causes exceptions not to be trapped
- updated to sysreport-1.4.3-13.el5
- ftp upload to dropbox with --upload
- cluster: major rewrite to support different versions of RHEL
- cluster: check rg_test for errors
- minor changes in various plug-ins (yum, networking, process, kernel)
- fixed some exceptions in threads which were not properly trapped
- veritas: don't run rpm -qa every time
- using rpm's python bindings instead of external binary
- corrected autofs and ldap plugin that were failing when debug option was not found in config file.
- implemented built-in checkdebug() that uses self.files and self.packages to make the decision
- missing binaries are properly detected now.
- better doExitCode handling
- fixed problem with rpm module intercepting SIGINT
- error when user specifies an invalid plugin or plugin option
- named: fixed indentation
- replaced isOptionEnabled() with getOption()
- tune2fs and fdisk were not always run against the correct devices/mountpoint
- added gpg key to package
- updated README with new svn repo and contributors
- updated manpage
- better signal handling
- caching of rpm -q outputs
- report filename includes rhnUsername if available
- report encryption via gpg and support pubkey
- autofs: removed redundant files
- filesys: better handling of removable devices
- added sosReadFile() returns a file's contents
- return after looping inside a directory
- collect udevinfo for each block device
- simply collect output of fdisk -l in one go
- handle sysreport invocation properly (warn if shell is interactive, otherwise spawn sysreport.legacy)
- progress bar don't show 100% until finished() is called
- Resolves: bz238778 added lspci -t
- now runs on RHEL3 as well (python 2.2)
- replaced commonPrefix() with faster code
- filesys: one fdisk -l for all
- selinux: collect fixfilex check output
- devicemapper: collect udevinfo for all block devices
- cluster: validate node names according to RFC 2181
- systemtap: cleaned up and added checkenabled() method
- added kdump plugin
- added collection of /etc/inittab
- Resolves: bz332151 apply regex to case number in sysreport for RHEL4
- Resolves: bz332211 apply regex to case number in sysreport for RHEL5
- Resolves: bz400111 sos incorrectly reports cluster data in SMP machine

* Wed Aug 13 2007 Navid Sheikhol-Eslami <navid at redhat dot com> - 1.7-8
- added README.rh-upload-core

* Mon Aug 13 2007 Navid Sheikhol-Eslami <navid at redhat dot com> - 1.7-7
- Resolves: bz251927 SOS errata needs to be respin to match 4.6 code base
- added extras/rh-upload-core script from David Mair <dmair@redhat.com>

* Mon Aug  9 2007 Navid Sheikhol-Eslami <navid at redhat dot com> - 1.7-6
- more language fixes
- added arabic, italian and french
- package prepared for release
- included sysreport as sysreport.legacy

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
