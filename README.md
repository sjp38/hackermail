hackermail
==========

hackermail is a mails management tool for hackers who collaborate using mailing
lists.  It requires no complicated setup but just `git`.  Using it, you can
fetch mailing list archives, read mails in those, and post replies or new
mails.

For now, hackermail supports public-inbox[1] managed mailing list archives and
manually exported mbox file contents.  Linux Kernel Mailing Lists (LKML)[2] are
good examples of the public-inbox managed mailing list archives.

[1] https://public-inbox.org/design_notes.html<br>
[2] https://www.kernel.org/lore.html


Demo
====

[![asciicast](https://asciinema.org/a/632442.svg)](https://asciinema.org/a/632442)


Getting Started
===============

List recent mails in Linux kernel DAMON subsystem mailing list
(https://lore.kernel.org/damon):

    $ ./hkml init --manifest ./manifests/lore.js
    $ ./hkml list damon --fetch

Open the fifth mail of the list:

    $ ./hkml open 5

Send a reply to the 5th mail:

    $ ./hkml reply 5

Forward the 5th mail to others:

    $ ./hkml forward 5

List entire mails of the 5th mail's thread of the list:

    $ ./hkml thread 5

Write and send a mail to the mailing list:

    $ ./hkml write --cc damon@lists.linux.dev

Export the [2, 5)-th mails on the list to 'exported.mbox' file:

    $ ./hkml export --range 2 5 exported.mbox

List mails in an .mbox file:

    $ ./hkml list exported.mbox

For more detail,

    $ ./hkml -h

or, refer to [USAGE.md](USAGE.md) file.
