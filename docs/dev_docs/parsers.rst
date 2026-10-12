``sos.cleaner.parsers`` ---  Parser Interface
=============================================

.. automodule:: sos.cleaner.parsers
    :members:
    :undoc-members:
    :show-inheritance:

Text input
----------

``sos clean-text`` runs the existing hostname, IPv4, IPv6 and MAC parsers
on UTF-8 text without creating or modifying an sosreport archive::

    sos clean-text file.txt --hostnames customerhost --domains customer.example
    cat file.txt | sos clean-text - --domains customer.example

Omitting the filename also reads stdin. Output contains only sanitized text;
diagnostics go to stderr. Line endings, whitespace and a missing final newline
are preserved. The input file is not modified.

Each invocation uses a private temporary cleaner cache, removed on exit.
``--tmp-dir`` selects its parent directory. This command neither loads nor
updates ``/etc/sos/cleaner/default_mapping`` and does not export mappings.

Names must be seeded explicitly with ``--hostnames`` or ``--domains``; these
options accept comma-separated lists and can be repeated. Existing cleaner
matching rules and exclusions apply, including short-name exclusions. Unknown
hostnames and usernames are not automatically discovered. Ordinary systemd
unit names and SELinux contexts are preserved unless a seeded identity matches
them. Address-like version numbers can still match the existing IP parsers;
this mode has no report-file context for applying archive path exclusions.

Invalid UTF-8, I/O errors and raised parser errors produce a non-zero exit
status. A failed line is not emitted, but previously emitted lines cannot be
retracted from a pipe; consumers must check the exit status.

.. autofunction:: sos.cleaner.text.sanitize_stream
