# pukiutils

## utf8ify.py

PukiWiki のデータとファイル名を UTF-8 に変換する Python スクリプト

### 必須

* Python 3.5
* nkf
* gzip

## gitify.py

utf8ify 後の wiki/backup データを Git リポジトリに変換する Python スクリプト

### 必須

* Python 3.5
* git

### 注意

* macOS (HFS+) で動かすと日本語ファイル名が NFD でアレなので各自で対処してください
    * Linux 上で動かした方がいいです
