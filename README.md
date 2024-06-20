hackermail
==========

hackermail is a mails management tool for hackers who collaborate using mailing
lists.  It requires no complicated setup but just `git`.  Using it, you can
fetch mailing list archives, read mails in those, and post replies or new
mails.

For now, hackermail supports
[public-inbox](https://public-inbox.org/design_notes.html) managed mailing list
archives and manually exported mbox file contents.  Linux Kernel Mailing Lists
[(LKML)](https://kernel.org/lore.html) are good examples of the public-inbox
managed mailing list archives.  Specifically, it is being used for, and aimed
to support development of [DAMON](https://damonitor.github.io) and general
parts of Linux kernel.


Demo
====

[![asciicast](https://asciinema.org/a/632442.svg)](https://asciinema.org/a/632442)
![interactive list](images/hkml_interactive_list_demo.gif)

(Note that the above demos are recorded on an old version of `hkml`.  Latest
version may have different features/interface.)


Getting Started
===============

List recent mails in Linux kernel DAMON subsystem mailing list
(https://lore.kernel.org/damon):

    $ ./hkml init --manifest ./manifests/lore.js
    $ ./hkml list damon --fetch

The first command is required to be executed only once for initialization.

The second command opens an interactive list of the mails.  From it, users can
do actions for mails including below.

- Opening a mail
- Listing complete thread of a mail
- Replying to a mail
- Forwarding a mail
- Continue writing a draft mail
- Managing tags of a mail
- Checking/applying patch mails
- Exporting mails

Press '?' for help, or read "Interactive Viewer"
[section](USAGE.md#interactive-viewer) of [USAGE.md](USAGE.md).

For more detail,

    $ ./hkml -h
    $ ./hkml list -h

or refer to [USAGE.md](USAGE.md) file.
