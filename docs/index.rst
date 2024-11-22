SoS
===

Sos is an extensible, portable, support data collection tool primarily aimed at Linux distributions and other UNIX-like operating systems.

This is the SoS developer documentation, for user documentation refer to:

https://github.com/sosreport/sos/wiki

This project is hosted at:

https://github.com/sosreport/sos

For the latest version, to contribute, and for more information, please visit the project pages or join the mailing list.

To clone the current main (development) branch run:

.. code::

    git clone git@github.com:sosreport/sos.git

Reporting bugs
^^^^^^^^^^^^^^

Please report bugs via the mailing list or by opening an issue in the GitHub Issue Tracker

Mailing list
^^^^^^^^^^^^^

`sos-devel <https://www.redhat.com/mailman/listinfo/sos-devel>`_ is the mailing list for any sos-related questions and discussion. Patch submissions and reviews are welcome too.

Patches and pull requests
^^^^^^^^^^^^^^^^^^^^^^^^^

Patches can be submitted via the mailing list or as GitHub pull requests. If using GitHub please make sure your branch applies to the current main branch as a 'fast forward' merge (i.e. without creating a merge commit). Use the git rebase command to update your branch to the current main branch if necessary.

Documentation
=============

User and API `documentation <https://sos.readthedocs.org/en/latest/index.html>`_ is automatically generated using `Sphinx <https://www.sphinx-doc.org/>`_ and `Read the Docs <https://readthedocs.org/>`_.

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

    python3 setup.py install

Pre-built Packaging
^^^^^^^^^^^^^^^^^^^

Fedora/RHEL users install via dnf:

``dnf install sos``

Debian users install via apt:

``apt install sosreport``

Ubuntu (14.04 LTS and above) users install via apt:

``sudo apt install sosreport``

API
===

Core Reference
^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 4

   archive
   clusters
   parsers
   policies
   plugins
   reporting
   utilities
