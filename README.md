# migpuki

PukiWiki から脱出するためのツール群（Linux / macOS 用）

## utf8ify.py

PukiWiki のデータとファイル名を UTF-8 に変換する Python スクリプト

### 必須

* Python 3.5

### 使い方

以下の操作でカレントディレクトリに `utf8` ディレクトリが生成されます。

```
./utf8ify.py <EUC 版 PukiWiki の index.php のあるディレクトリ>
```

### 注意

* Python 3 の decode での EUC_JP → UTF-8 の変換がうまくいかないことが稀によくある
    * とりあえずエラーを無視（`errors=replace`）して無理矢理続行する
    * 変換失敗した場合元のファイルを .euc_jp という拡張子で出力先にそのままコピーするのでそれを nkf のような別ソフトで各自変換してください

## gitify.py

utf8ify 後の wiki/backup データを Git リポジトリに変換する Python スクリプト

### 必須

* Python 3.5
* git

### 使い方

以下の操作でカレントディレクトリに `wiki-repo` ディレクトリが生成されます。

```
./gitify.py <utf8ify.py の生成した wiki, backup のあるディレクトリ>
```

### 注意

* macOS (HFS+) で動かすと日本語ファイル名が NFD でアレで git がアレなので各自で対処してください
    * `core.precomposeunicode = true` がオンなのにちゃんと動いてない気がする
        * なんもわからん
    * とにかく Linux 上で動かした方がいいです

## 詳細な使い方

### utf8ify.py

```
./utf8ify.py [-h] [-v] [-o OUTDIR] [-n] [-e ENCODING] [-u NORMALIZE] basedir
```

* `-h`, `--help`: ヘルプを表示します
* `-v`, `--verbose`: 詳細なログを吐きます
* `-o`, `--outdir`: 出力ディレクトリ名を指定できます
    + デフォルト：utf8
* `-n`, `--noconvert`: ファイル内容を文字コード変換しません
    + デフォルト：オフ（ファイル内容を文字コード変換します）
* `-e`, `--encoding`: 入力文字コードを指定できます (euc\_jp / utf\_8)
    + デフォルト：euc\_jp
    + EUC 版しかテストしてません
* `-u`, `--normalize`: 変換後ファイルパスの Unicode 正規化のタイプを指定できます (NFC / NFD / NFKC / NFKD)
    + デフォルト：NFC

### gitify.py

```
./gitify.py [-h] [-v] [-o OUTDIR] [-n NAME] [-e EMAIL] [-r] basedir
```

* `-h`, `--help`: ヘルプを表示します
* `-v`, `--verbose`: 詳細なログを吐きます
* `-o`, `--outdir`: 出力ディレクトリ名を指定できます
    + デフォルト：wiki-repo
* `-n`, `--name`: リポジトリの author / committer の名前を指定できます
    + 指定しなければ local での設定はしません（git は global の `user.name` を見に行きます）
* `-e`, `--email`: リポジトリの author / committer のメールアドレスを指定できます
    + 指定しなければ local での設定はしません（git は global の `user.email` を見に行きます）
* `-r`, `--renamelog`: _RenameLog.{txt,gz}（:RenameLog）を使ってリネーム情報もコミットします（実験的）
    + デフォルト：オフ

## ライセンス

Apache License 2.0
