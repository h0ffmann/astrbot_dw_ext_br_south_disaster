# astrbot_dw_ext_br_south_disaster

[English](README.md) | [简体中文](README.zh-CN.md) | [Português (Brasil)](README.pt-BR.md) | [日本語](README.ja-JP.md)

> この文書は翻訳です。内容に差異がある場合は、[英語版](README.md)を正とします。

この拡張機能は、AstrBot プラグイン [astrbot_plugin_disaster_warning](https://github.com/Pancakes-Labs/astrbot_plugin_disaster_warning) 用です。
ブラジル南部（リオグランデ・ド・スル州 RS、サンタカタリーナ州 SC、パラナ州 PR）の大雨、洪水、土砂災害に関する CEMADEN の警報を送信します。
メッセージには、NOAA CPC のエルニーニョとラニーニャの背景データを追加します。

> [!WARNING]
> データは参考情報です。公式の警報ではありません。必ず民間防衛当局（Defesa Civil）と地元当局の指示に従ってください。

> [!CAUTION]
> この拡張機能は Python コードとしてホストと同じプロセスで動作します。インストールすると、ホストとホストのデータへのアクセスを信頼することになります。

## ドキュメント

[Wiki](https://github.com/h0ffmann/astrbot_dw_ext_br_south_disaster/wiki) には、同じ言語で詳しい情報があります。

## 要件

- ホストに拡張システムが必要です。このシステムは、ホストのリリース版にはまだ含まれていません。
- ホストのバージョンは 1.6.5 以上である必要があります。

## インストール

ホストのインストール機能はまだ利用できません。次の手順で手動でインストールしてください。

1. プラグインのデータディレクトリを開きます。`extensions` ディレクトリがない場合は作成します。
2. このリポジトリを `extensions/br_south_disaster` に置きます。ディレクトリ名は拡張機能の ID と同じにする必要があります。
3. プラグイン設定の `extensions.enabled_ids` に `br_south_disaster` を追加します。
4. プラグインを再読み込みします。

## 設定方法

設定は `extensions.settings` に記述します。この値は JSON テキストです。

```json
{
  "enabled_ids": ["br_south_disaster"],
  "settings": "{\"br_south_disaster\": {\"language\": \"en\", \"rain_interval\": 600}}"
}
```

## 設定項目

| 設定項目 | 既定値 | 説明 |
| :--- | :--- | :--- |
| `language` | `zh-CN` | メッセージの言語です。値は `zh-CN`、`en`、`pt-BR`、`ja-JP` です。 |
| `alerts_interval` | `300` | CEMADEN の警報を取得する間隔（秒）です。 |
| `rain_interval` | `300` | CEMADEN の雨量計データを取得する間隔（秒）です。 |
| `states` | `["RS", "SC", "PR"]` | 監視する州のリストです。不明なコードは無視します。既知のコードがない場合は、すべての州を使用し、警告を記録します。 |
| `rain_thresholds` | 下記を参照 | 雨量計の警報レベルを決める雨量です。 |

`rain_thresholds` には `yellow`、`orange`、`red` の 3 つのキーがあります。各キーには `acc1hr`（直近 1 時間の雨量、mm）と `acc24hr`（直近 24 時間の雨量、mm）があります。どちらかの値がしきい値に達すると、雨量計はそのレベルになります。省略したキーは既定値のままです。

| キー | レベル | `acc1hr` (mm) | `acc24hr` (mm) |
| :--- | :--- | :--- | :--- |
| `yellow` | 2 | 20 | 50 |
| `orange` | 3 | 30 | 100 |
| `red` | 4 | 60 | 150 |

州を追加するには、`states.py` に 1 行追加します。

## データソース

| ソース | データ | 更新頻度 |
| :--- | :--- | :--- |
| [CEMADEN 警報](docs/CEMADEN%20API.md) | 市町村ごとのリスク警報 | `alerts_interval` ごとに取得します |
| [CEMADEN 雨量計](docs/CEMADEN%20API.md) | 雨量計ごとの雨量（州ごとに 1 回取得） | `rain_interval` ごとに取得します |
| [NOAA CPC ONI](docs/NOAA%20CPC%20ONI.md) | 海洋ニーニョ指数 | NOAA が毎月 1 回、新しい値を公開します |

ブラジルのデータソースの調査は [docs/brazil-sources-survey.md](docs/brazil-sources-survey.md) にあります。`docs/` の文書は英語です。

## 開発

テストはホストの実際のクラスを使用します。`just setup` は、固定バージョンのホストを `.host/` に取得します。
[just](https://github.com/casey/just) と [uv](https://github.com/astral-sh/uv) が必要です。Nix を使う場合は、`nix develop` でこれらのツールを利用できます。

```sh
just setup
just check
```

`just check` は、フォーマット、コード規則、型、複雑度、テストの確認を実行します。CI も同じコマンドを実行します。
`just` を実行すると、すべてのコマンドを確認できます。`just live` は、実際の CEMADEN と NOAA CPC のサービスを呼び出すテストを実行します。
別のホストのコピーを使うには、`DW_HOST_DIR` を設定します。

## 記述ルール

英語の文章は ASD-STE100 Simplified Technical English で記述してください。同梱のスキルは `.claude/skills/asd-ste100` にあります。
次のコマンドでファイルを確認できます。

```sh
python3 .claude/skills/asd-ste100/scripts/ste-lint.py README.md
```

## ライセンス

コードは [Mozilla Public License 2.0](LICENSE) の下で提供されます。`extension.png` は CC-BY-4.0 です。`meta.json` を参照してください。
`.claude/skills/asd-ste100` のファイルは MIT ライセンスです。`.claude/skills/asd-ste100/LICENSE` を参照してください。
