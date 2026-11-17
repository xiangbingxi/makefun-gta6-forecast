# GTA VI Twitch Forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/xiangbingxi/makefun-gta6-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/xiangbingxi/makefun-gta6-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Forecasts how many people will be watching Grand Theft Auto VI live on
Twitch in each hour of its release day (2026-11-19 UTC), as five quantiles
per hour. Entry for make.fun's `gta6-twitch-ccu-forecast-01` bounty.

## How it works

The program reads the case file the grader gives it — hour 1's print and
the comparables, 38 past big launches' hourly Twitch curves (42 in the
final) — and fits the day's shape from them. For each comparable with a
full release day and a real hour-1 print, it takes the log-ratio curve
`ln(viewers_h / viewers_1)` for hours 2..24 and regresses it, hour by
hour, on `ln(hour-1 print / 100k)`. A launch's hour-1 print already says
how much of its audience is awake at midnight UTC: small hour-1 launches
rise several-fold into the evening, mega-launches barely rise at all, and
the regression carries that scale dependence into the forecast. The
spread at each hour is the residual standard deviation of that hour's
regression, so the five quantiles are the fitted median widened by how
much past launches actually scattered around the fit.

```
q_tau(h) = p1 * exp(lr_h + z_tau * s_h)
```

One guard: the evening peak (hours 13..24) is lifted to at least 1.28x
hour 1. The regression's straight-line extrapolation would otherwise call
the peak at or below hour 1 for a ~1M-viewer hour 1, which no
rolling-midnight console launch in the data ever did (the smallest peak
was The Last of Us Part II at 1.34x).

## Practice result

Scored on the four practice launches (Wolverine, Red Dead Redemption 2,
God of War Ragnarök, Spider-Man 2) against SullyGnome's public hourly
averages, the same source the kit uses:

| case | this entry | house baseline |
| --- | --- | --- |
| p00 Wolverine | 0.243 | 0.744 |
| p01 Red Dead Redemption 2 | 0.164 | 0.287 |
| p02 God of War Ragnarök | 0.137 | 0.215 |
| p03 Spider-Man 2 | 0.180 | 0.303 |
| **mean pinball loss** | **0.181** | **0.387** |

## Run locally

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=<kit>/input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Python 3.13, standard library only, no network. Deterministic: two runs
write byte-identical outputs. About 0.03 s per case.

## Files

- `main.py` — the whole entry (the only entrypoint)
- `LICENSE` — MIT
- `.makefun/owner.json` — the payout wallet for the entry

---

<sub>Entered on [make.fun](https://make.fun/?ref=efzg7wym&utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>
