# astrbot_dw_ext_br_south_disaster

This extension is for the AstrBot plugin [astrbot_plugin_disaster_warning](https://github.com/Pancakes-Labs/astrbot_plugin_disaster_warning).
It sends CEMADEN rain, flood and landslide alerts for the South of Brazil (RS, SC and PR).
It adds El Niño and La Niña data from NOAA CPC to the messages.

> [!WARNING]
> The data is for reference only. It is not an official warning. Always obey the instructions of the Defesa Civil and of your local authorities.

> [!CAUTION]
> The extension runs as Python code in the same process as the host. When you install it, you trust it with the host and with the host data.

## Requirements

- The host must have the extension system. This system is not yet in a release of the host.
- The host version must be 1.6.5 or higher.

## Installation

The install flow of the host is not yet available. Do these steps to install by hand:

1. Open the data directory of the plugin. Make an `extensions` directory if it does not exist.
2. Put this repository in `extensions/br_south_disaster`. The directory name must be the same as the extension id.
3. Add `br_south_disaster` to `extensions.enabled_ids` in the plugin configuration.
4. Reload the plugin.

## Configuration

Put the settings in `extensions.settings`. This value is JSON text:

```json
{
  "enabled_ids": ["br_south_disaster"],
  "settings": "{\"br_south_disaster\": {\"language\": \"en\", \"rain_interval\": 600}}"
}
```

## Settings

| Setting | Default | Description |
| :--- | :--- | :--- |
| `language` | `zh-CN` | The language of the messages. The values are `zh-CN`, `en`, `pt-BR` and `ja-JP`. |
| `alerts_interval` | `300` | The time between two requests for CEMADEN alerts, in seconds. |
| `rain_interval` | `300` | The time between two requests for CEMADEN rain gauges, in seconds. |
| `states` | `["RS", "SC", "PR"]` | The list of states to monitor. The extension ignores an unknown code. If no code is known, it uses all states and writes a warning. |
| `rain_thresholds` | See below | The rain totals that set the level of a rain gauge alert. |

`rain_thresholds` has three keys: `yellow`, `orange` and `red`. Each key has `acc1hr` (rain in the last 1 hour, in mm) and `acc24hr` (rain in the last 24 hours, in mm). A gauge meets a level when one of the two values reaches the threshold. A key that you omit keeps its default.

| Key | Level | `acc1hr` (mm) | `acc24hr` (mm) |
| :--- | :--- | :--- | :--- |
| `yellow` | 2 | 20 | 50 |
| `orange` | 3 | 30 | 100 |
| `red` | 4 | 60 | 150 |

To add a state, add one line to `states.py`.

## Data sources

| Source | Data | Update frequency |
| :--- | :--- | :--- |
| [CEMADEN alerts](docs/CEMADEN%20API.md) | Risk alerts for each municipality | The extension reads the feed at each `alerts_interval` |
| [CEMADEN rain gauges](docs/CEMADEN%20API.md) | Rain totals for each gauge, one request for each state | The extension reads the feed at each `rain_interval` |
| [NOAA CPC ONI](docs/NOAA%20CPC%20ONI.md) | The Oceanic Niño Index | NOAA publishes one new value each month |

The survey of the Brazilian sources is in [docs/brazil-sources-survey.md](docs/brazil-sources-survey.md).

## Tests

The tests use the real classes of the host. Thus, they need a checkout of the host with the extension system.
Set `DW_HOST_DIR` to the path of the checkout. If you do not set it, the tests look for `astrbot_plugin_disaster_warning` next to this repository.

```sh
DW_HOST_DIR=/path/to/astrbot_plugin_disaster_warning pytest
```

Set `DW_LIVE_TESTS=1` to run the live tests. They call the real CEMADEN and NOAA CPC services.

## License

The code is under the [Mozilla Public License 2.0](LICENSE). The file `extension.png` is under CC-BY-4.0. See `meta.json`.
