# migpuki

PukiWiki から脱出するためのツール群（Linux / macOS 用）

## convpuki.py

PukiWiki のデータとファイル名を UTF-8 等に変換する Python スクリプト

### 必須

* Python 3.5

### 使い方

以下の操作でカレントディレクトリに `pukiwiki-conv` ディレクトリが生成されます。

```
./convpuki.py <PukiWiki の index.php のあるディレクトリ>
```

### 注意

* Python 3 の decode での EUC_JP → UTF-8 の変換がうまくいかないことが稀によくある
    * とりあえずエラーを無視（`errors=replace`）して無理矢理続行する
* 変換に失敗した場合元のファイルを .euc_jp という拡張子で出力先にそのままコピーするのでそれを nkf のような別ソフトで各自変換してください
    * nkf でこのファイルを UTF-8 に一括変換する bash スクリプトを `contrib/nkfy.sh` として用意しておきました
    * `./nkfy.sh <convpuki.py の生成したディレクトリ>` のように使う

## gitify.py

convpuki で UTF-8 化した後の wiki / backup / cache データを Git リポジトリに変換する Python スクリプト

### 必須

* Python 3.5
* git

### 使い方

以下の操作でカレントディレクトリに `pukiwiki-repo` ディレクトリが生成されます。

```
./gitify.py <convpuki.py の生成した wiki, backup, cache のあるディレクトリ>
```

## 詳細な使い方

### convpuki.py

```
./convpuki.py [-h] [-v] [-o OUTDIR] [-n] [-e ENCODING] [-u NORMALIZE] basedir
```

* `-h`, `--help`: ヘルプを表示します
* `-v`, `--verbose`: 詳細なログを吐きます
* `-o`, `--outdir`: 出力ディレクトリ名を指定できます
    + デフォルト：pukiwiki-conv
* `-f`, `--encoding_from`: 入力文字コードを指定できます (euc\_jp / utf-8)
    + デフォルト：euc\_jp
* `-t`, `--encoding_to`: 出力文字コードを指定できます (utf-8 / euc\_jp)
    + デフォルト：utf-8
* `-C`, `--fileconv`: ファイル内容を文字コード変換します（デフォルト）
* `-c`, `--nofileconv`: ファイル内容を文字コード変換しません
* `-P`, `--pathconv`: ファイルパスを文字コード変換します（デフォルト）
* `-p`, `--nopathconv`: ファイルパスを文字コード変換しません
* `-x`, `--outhexpath`: ファイルパスを PukiWiki の `[0-9A-F]+` 形式に変換します
    + デフォルト：オフ
* `-u`, `--normalize`: 変換後ファイルパスの Unicode 正規化のタイプを指定できます (NFC / NFD / NFKC / NFKD)
    + デフォルト：NFC

### gitify.py

```
./gitify.py [-h] [-v] [-o OUTDIR] [-n NAME] [-e EMAIL] [-r] basedir
```

* `-h`, `--help`: ヘルプを表示します
* `-v`, `--verbose`: 詳細なログを吐きます
* `-o`, `--outdir`: 出力ディレクトリ名を指定できます
    + デフォルト：pukiwiki-repo
* `-d`, `--directcontents`: wiki コンテンツをリポジトリのディレクトリ直下に配置します
    + デフォルト：オフ
* `-n`, `--name`: リポジトリの author / committer の名前を指定できます
    + 指定しなければ local での設定はしません（git は global の `user.name` を見に行きます）
* `-e`, `--email`: リポジトリの author / committer のメールアドレスを指定できます
    + 指定しなければ local での設定はしません（git は global の `user.email` を見に行きます）
* `-r`, `--renamelog`: _RenameLog.{txt,gz}（:RenameLog）を使ってリネーム情報もコミットします（実験的）
    + デフォルト：オフ

## ライセンス

Apache License 2.0
