SoS
===

Sos is an extensible, portable, support data collection tool primarily aimed at Linux distributions and other UNIX-like operating systems.

This project is hosted at:

http://github.com/sosreport/sos

For the latest version, to contribute, and for more information, please visit the project pages or join the mailing list.

To clone the current master (development) branch run:

.. code::

    git clone git://github.com/sosreport/sos.git

Reporting bugs
^^^^^^^^^^^^^^

Please report bugs via the mailing list or by opening an issue in the GitHub Issue Tracker

Mailing list
^^^^^^^^^^^^^

`sos-devel <https://www.redhat.com/mailman/listinfo/sos-devel>`_ is the mailing list for any sos-related questions and discussion. Patch submissions and reviews are welcome too.

Patches and pull requests
^^^^^^^^^^^^^^^^^^^^^^^^^

Patches can be submitted via the mailing list or as GitHub pull requests. If using GitHub please make sure your branch applies to the current master as a 'fast forward' merge (i.e. without creating a merge commit). Use the git rebase command to update your branch to the current master if necessary.

Documentation
=============

User and API `documentation <http://sos.readthedocs.org/en/latest/index.html#>`_ is automatically generated using `Sphinx <http://sphinx-doc.org/>`_ and `Read the Docs <https://www.readthedocs.org/>`_.

Wiki
^^^^

 `How to write a plugin <https://github.com/sosreport/sos/wiki/How-to-Write-a-Plugin>`_

 `How to write a policy <https://github.com/sosreport/sos/wiki/How-to-Write-a-Policy>`_

 `Plugin options <https://github.com/sosreport/sos/wiki/Plugin-options>`_

To help get your changes merged quickly with as few revisions as possible please refer to the `Contributor Guidelines <https://github.com/sosreport/sos/wiki/Contribution-Guidelines>`_ when submitting patches or pull requests.

Installation
============

Manual Installation
^^^^^^^^^^^^^^^^^^^

.. code::

    to install locally (as root) ==> make install
    to build an rpm ==> make rpm
    to build a deb ==> make deb

Pre-built Packaging
^^^^^^^^^^^^^^^^^^^

Fedora/RHEL users install via yum:

``yum install sos``

Debian(Sid) users install via apt:

``apt-get install sosreport``

Ubuntu(Saucy 13.10 and above) users install via apt:

``sudo apt-get install sosreport``

API
===

Plugin Reference
^^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 2

   plugins


Core Reference
^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 2

   archive
   policies
   reporting
   utilities
