# astrbot_dw_ext_br_south_disaster

[English](README.md) | [简体中文](README.zh-CN.md) | [Português (Brasil)](README.pt-BR.md) | [日本語](README.ja-JP.md)

> 本文为译文。如有出入，以[英文版](README.md)为准。

本扩展用于 AstrBot 插件 [astrbot_plugin_disaster_warning](https://github.com/Pancakes-Labs/astrbot_plugin_disaster_warning)。
它发送 CEMADEN 针对巴西南部（南里奥格兰德州 RS、圣卡塔琳娜州 SC、巴拉那州 PR）的强降雨、洪涝和滑坡预警。
它还在消息中附加 NOAA CPC 的厄尔尼诺和拉尼娜背景数据。

> [!WARNING]
> 数据仅供参考，不是官方预警。请始终遵从巴西民防部门（Defesa Civil）和当地主管部门的指示。

> [!CAUTION]
> 本扩展以 Python 代码形式与宿主在同一进程中运行。安装本扩展，即表示您信任它可以访问宿主及宿主数据。

## 文档

[Wiki](https://github.com/h0ffmann/astrbot_dw_ext_br_south_disaster/wiki) 以相同语言提供更多信息。

## 要求

- 宿主必须具备扩展系统。该系统尚未包含在宿主的正式版本中。
- 宿主版本必须为 1.6.5 或更高。

## 安装

宿主的安装流程尚不可用。请按以下步骤手动安装：

1. 打开插件的数据目录。如果 `extensions` 目录不存在，请创建该目录。
2. 将本仓库放到 `extensions/br_south_disaster`。目录名必须与扩展 ID 相同。
3. 在插件配置的 `extensions.enabled_ids` 中添加 `br_south_disaster`。
4. 重载插件。

## 配置

在 `extensions.settings` 中填写设置。该值为 JSON 文本：

```json
{
  "enabled_ids": ["br_south_disaster"],
  "settings": "{\"br_south_disaster\": {\"language\": \"en\", \"rain_interval\": 600}}"
}
```

## 设置项

| 设置项 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `language` | `zh-CN` | 消息语言。可选值为 `zh-CN`、`en`、`pt-BR` 和 `ja-JP`。 |
| `alerts_interval` | `300` | 两次请求 CEMADEN 预警的间隔，单位为秒。 |
| `rain_interval` | `300` | 两次请求 CEMADEN 雨量站数据的间隔，单位为秒。 |
| `states` | `["RS", "SC", "PR"]` | 要监控的州列表。扩展忽略未知代码。如果没有已知代码，扩展使用全部州并写入一条警告。 |
| `rain_thresholds` | 见下文 | 决定雨量站预警级别的降雨量。 |

`rain_thresholds` 有三个键：`yellow`、`orange` 和 `red`。每个键包含 `acc1hr`（最近 1 小时降雨量，单位 mm）和 `acc24hr`（最近 24 小时降雨量，单位 mm）。两个值中任意一个达到阈值，雨量站即达到该级别。省略的键保持默认值。

| 键 | 级别 | `acc1hr` (mm) | `acc24hr` (mm) |
| :--- | :--- | :--- | :--- |
| `yellow` | 2 | 20 | 50 |
| `orange` | 3 | 30 | 100 |
| `red` | 4 | 60 | 150 |

要添加一个州，请在 `states.py` 中添加一行。

## 数据来源

| 来源 | 数据 | 更新频率 |
| :--- | :--- | :--- |
| [CEMADEN 预警](docs/CEMADEN%20API.md) | 各市的风险预警 | 扩展按 `alerts_interval` 读取 |
| [CEMADEN 雨量站](docs/CEMADEN%20API.md) | 各雨量站的降雨量，每个州一次请求 | 扩展按 `rain_interval` 读取 |
| [NOAA CPC ONI](docs/NOAA%20CPC%20ONI.md) | 海洋尼诺指数 | NOAA 每月发布一个新值 |

巴西数据源调查见 [docs/brazil-sources-survey.md](docs/brazil-sources-survey.md)。`docs/` 中的文档为英文。

## 测试

测试使用宿主的真实类，因此需要一份带有扩展系统的宿主检出。
请将 `DW_HOST_DIR` 设置为该检出的路径。如果未设置，测试会在本仓库旁查找 `astrbot_plugin_disaster_warning`。

```sh
DW_HOST_DIR=/path/to/astrbot_plugin_disaster_warning pytest
```

设置 `DW_LIVE_TESTS=1` 可运行实时测试。这些测试会调用真实的 CEMADEN 和 NOAA CPC 服务。

## 写作规则

英文文本须使用 ASD-STE100 简化技术英语。随仓库提供的技能位于 `.claude/skills/asd-ste100`。
以下命令可检查文件：

```sh
python3 .claude/skills/asd-ste100/scripts/ste-lint.py README.md
```

## 许可证

代码采用 [Mozilla Public License 2.0](LICENSE)。文件 `extension.png` 采用 CC-BY-4.0，详见 `meta.json`。
`.claude/skills/asd-ste100` 中的文件采用 MIT 许可证，详见 `.claude/skills/asd-ste100/LICENSE`。
