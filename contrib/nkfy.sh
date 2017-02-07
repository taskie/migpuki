#!/bin/bash
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
    if [[ -f "$newfile" ]] && [[ ! -f "$bakfile" ]]; then
        echo "mv \"$newfile\" \"$bakfile\""
        mv "$newfile" "$bakfile"
    fi
    echo "nkf -E -w80 \"$oldfile\" > \"$newfile\""
    nkf -E -w80 "$oldfile" > "$newfile"
done
