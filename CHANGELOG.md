# Changelog

## Unreleased

- Add the DeepWiki settings in `.devin/wiki.json` and a badge in the README.
- Fix the time of rain gauge messages. The feed sends UTC. The extension read it as Brasília time, so messages showed a time 3 hours too late.
- A row with unexpected values no longer stops the other rows of a feed.
- A changed feed now gives an error in the log. It no longer looks like an empty feed.
- A bad `rain_thresholds` or interval value no longer stops the setup.
- A failed ENSO request now tries again after 1 hour, not 24 hours. The failure goes to the log.
- Add `just` and Nix tools, type checks, property tests and tests with the real host loader.
- Add the README in `zh-CN`, `pt-BR` and `ja-JP`.
- Add the vendored `asd-ste100` skill for contributors.

## 0.1.0

- First release in a separate repository.
- CEMADEN alerts for rain, flood and landslide in RS, SC and PR.
- CEMADEN rain gauge alerts with configurable thresholds.
- El Niño and La Niña data from NOAA CPC, as background data in the messages.
- Messages in `zh-CN`, `en`, `pt-BR` and `ja-JP`.
