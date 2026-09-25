#!/usr/bin/env sh
# Download the latest TI datasheets into this folder (file names without revision suffix).
set -e
cd "$(dirname "$0")"
for part in bq79616-q1 bq79600-q1 iso7721-q1 bq79631-q1 tps7a66-q1; do
  echo "Fetching $part"
  curl -fsSL -A "Mozilla/5.0" -o "$(echo "$part" | tr 'a-z' 'A-Z')_latest.pdf" \
    "https://www.ti.com/lit/ds/symlink/$part.pdf"
done
