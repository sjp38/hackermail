#!/bin/bash

bindir=$(dirname "$0")

wget https://lore.kernel.org/manifest.js.gz
gzip -d manifest.js.gz
"$bindir/hkml" manifest convert_public_inbox_manifest \
	--public_inbox_manifest ./manifest.js \
	--site https://lore.kernel.org > "$bindir/manifests/lore.js"
