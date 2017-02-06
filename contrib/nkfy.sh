#!/bin/bash
set -eu

if (( $# < 1 )); then
    exit 1
fi

for oldfile in $(find "$1" -name '*.euc_jp')
do
    noextfile="${oldfile%%.euc_jp}"
    bakfile="$noextfile.bak"
    newfile="$noextfile.txt"
    if [[ -f "$newfile" ]] && [[ ! -f "$noextfile.bak" ]]; then
        echo "mv \"$newfile\" \"$bakfile\""
        mv "$newfile" "$bakfile"
    fi
    echo "nkf -E -w80 \"$oldfile\" > \"$newfile\""
    nkf -E -w80 "$oldfile" > "$newfile"
done
