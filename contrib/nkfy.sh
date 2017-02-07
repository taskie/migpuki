#!/bin/bash
# requires: nkf, gzip
set -eu

if (( $# < 1 )); then
    echo "please specify basedir"
    echo "usage: $0 basedir"
    exit 1
fi

for oldfile in $(find "$1" -name '*.euc_jp')
do
    newfile="${oldfile%%.euc_jp}"
    bakfile="$newfile.bak"
    # create backup file
    if [[ -f "$newfile" ]] && [[ ! -f "$bakfile" ]]; then
        echo "mv \"$newfile\" \"$bakfile\""
        mv "$newfile" "$bakfile"
    fi
    if [[ -z "${newfile%%*.gz}" ]]; then
        echo "gz -cd \"$oldfile\" | nkf -E -w80 | gz -c > \"$newfile\""
        gzip -cd "$oldfile" | nkf -E -w80 | gzip -c > "$newfile"
    else
        echo "nkf -E -w80 \"$oldfile\" > \"$newfile\""
        nkf -E -w80 "$oldfile" > "$newfile"
    fi
done
