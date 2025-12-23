HacKerMaiL
==========

[![CI](https://github.com/sjp38/hackermail/actions/workflows/ci.yml/badge.svg)](https://github.com/sjp38/hackermail/actions/workflows/ci.yml)

HacKerMaiL (hkml) is a mails management tool for hackers who collaborate using
mailing lists.  It requires no complicated setup but just `git`.  Using it, you
can fetch mailing list archives, read mails in those, and post replies or new
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

    $ ./hkml list damon

For the first time, the command will ask you if you want to initialize the
setup and fetch the mails from the internet, with some questions.  For this
specific case (listing mails of a Linux kernel subsystem mailing list), you can
simply select default options and 'yes'.  Then, it will open an interactive
list of the mails.  From it, users can do actions for mails including below.

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

For more detail and complete list of features,

    $ ./hkml -h
    $ ./hkml list -h

or refer to [USAGE.md](USAGE.md) file.  For daily use of `hkml`, particularly,
you may want to know how to [manage tags](USAGE.md#tagging) of mails (useful
for managing 'sent' and 'drafts' mails) and how you can
[backup/syncronize](USAGE.md#synchronizing) those.


Additional Resources
====================

- SeongJae Park, __hkml: Mailing Tool for Simple Linux Kernel Development.__ In
  _Open Source Summit Japan_, Dec 2025.
  [Slides](https://static.sched.com/hosted_files/ossjapan2025/97/hkml_ossjp25.pdf?_gl=1*pb5adv*_gcl_au*MTU2MDAyNjMzMS4xNzYzMDE0NzE3*FPAU*MTU2MDAyNjMzMS4xNzYzMDE0NzE3),
  [Video](https://youtu.be/f09kvPvYMsM?si=lS6Cg3zkSG-_7wyX),
  [Link](https://sched.co/29FmF)
