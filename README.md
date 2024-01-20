hackermail
==========

hackermail is a mail client for hackers who collaborate using mailing lists.
It requires no complicated setup but just `git`.  Using it, you can fetch
mailing list archives, read mails in those, and post new mails or replies.

For now, hackermail supports public-inbox[1] managed mailing list archives and
manually exported mbox file contents.  Linux Kernel Mailing Lists (LKML)[2] are
good examples of the public-inbox managed mailing list archives.

[1] https://public-inbox.org/design_notes.html<br>
[2] https://www.kernel.org/lore.html


Getting Started
===============

List mails in Linux kernel memory management subsystem mailing list
(https://lore.kernel.org/linux-mm) which were sent within last three days:

    $ ./hkml init --manifest ./manifests/lore.js
    $ ./hkml list linux-mm --fetch

Open the fifth mail:

    $ ./hkml open 5

Send a reply to the 5th mail:

    $ ./hkml reply 5

Write and send a mail to the mailing list:

    $ ./hkml write --cc linux-mm@kvack.org

Export the [2, 5)-th mails on the list to 'exported.mbox' file:

    $ ./hkml export --range 2 5 exported.mbox

List mails in an .mbox file:

    $ ./hkml list exported.mbox

For more detail,

    $ ./hkml -h

For more detailed usages, please refer to [USAGE.md](USAGE.md) file.
