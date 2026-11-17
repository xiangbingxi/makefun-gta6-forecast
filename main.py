"""Forecast GTA VI's launch-day Twitch viewers hour by hour.

Entry for make.fun's gta6-twitch-ccu-forecast-01 ($250 in USDC).

Model: the day's shape comes from the comparables shipped in the case file
(38 past big launches in a practice case, 42 in the final). For each
comparable with a full release day and a real hour-1 print, take the
log-ratio curve ln(viewers_h / viewers_1) for hours 2..24, and regress it,
hour by hour, on ln(hour-1 print / 100k). A launch's hour-1 print already
says how much of its audience is awake at midnight UTC: small hour-1
launches rise several-fold into the evening, mega-launches barely rise at
all, and the regression carries that scale dependence into the forecast.
The spread at each hour is the residual standard deviation of that hour's
regression, so the five quantiles are the fitted median widened by how much
past launches actually scattered around the fit.

  q_tau(h) = p1 * exp(lr_h + z_tau * s_h), rounded to 2 decimals (half up)

where p1 is the case's hour-1 print, lr_h the fitted log-ratio at hour h,
s_h that hour's residual spread, and z_tau the standard normal's quantile
(-1.645, -0.674, 0, 0.674, 1.645). One guard: the evening peak (hours
13..24) is lifted to at least 1.28x hour 1, because the regression's
straight-line extrapolation would otherwise call the peak at or below
hour 1 for a ~1M-viewer hour 1, which no rolling-midnight console
launch in the data ever did.

On the four practice cases this scores a mean pinball loss of ~0.18,
against the house baseline's ~0.39 (practice answers fetched from
SullyGnome's public hourly averages, the same source the kit uses).

Runs as the grader runs it: python3 -P -s /bot/main.py, Python 3.13,
standard library only, no network. Reads every <id>.in in the input
directory (MAKEFUN_INPUT_DIR, else /input/) and writes <id>.out to the
output directory (MAKEFUN_OUTPUT_DIR, else /output/): exactly
{"hours": [{"hour": h, "q": [q05, q25, q50, q75, q95]}]} for hours 2..24.
Deterministic: no randomness, no wall-clock or hash-order dependence.
"""

import json
import math
import os
import statistics
import sys
from pathlib import Path

# The grader's -P leaves /bot off sys.path: put it back first, so `import model` finds a model.py shipped beside this file.
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

# The quantile levels the contest scores, in the order each row lists them.
LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
# The standard normal's quantile at each level.
Z = [-1.645, -0.674, 0, 0.674, 1.645]

# A comparable only enters the fit when its hour-1 print is a real
# measurement, not a near-empty category's sparse sampling: below 20,000
# the ratios explode (a 164-viewer hour 1 "rising" 2,000-fold) and are
# noise, not signal. Tier "comparable" only: early-access launches had
# their peak days before release day, and free-to-play "weak" launches
# are a different shape.
MIN_HOUR1 = 20000
# Fall back to a plain median curve when too few comparables qualify.
MIN_CURVES = 5
# Keep the fitted spread honest but bounded.
SPREAD_FLOOR = 0.12
SPREAD_CAP = 1.0
# Reference scale for the regression's x axis.
SCALE = 100000.0
# The evening peak of a rolling-midnight console launch never falls below
# its hour-1 print in the data: every console-only launch peaked at least
# 1.34x its hour 1 (the smallest, The Last of Us Part II at 365k). The
# regression, fitted on launches up to ~875k and dragged down at the top
# end by two PC launches whose hour 1 caught a simultaneous global PC
# wave GTA VI does not have, extrapolates to a peak at or below hour 1
# once the hour-1 print passes ~1M. That cannot be right for a launch
# whose biggest market (the US) only unlocks at 05:00Z, so lift the
# evening hours (13..24) until their peak log-ratio is at least this.
# It never binds on the practice cases; it only guards the final's scale.
EVENING_FLOOR = 0.25


def round2(x: float) -> float | int:
    """x rounded to 2 decimals, half up, as JavaScript's Math.round(x * 100) / 100 rounds it.

    A whole number comes back as an int, so json.dumps writes 1240 where JavaScript writes 1240 (not 1240.0).
    """
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def release_day_hours(comp: dict) -> dict | None:
    """A comparable's release-day hourly viewers, {hour 1..24: viewers}, or None.

    The day is the UTC date of day_start; hour h covers [h-1, h) UTC.
    Needs all 24 hours and a positive hour-1 print.
    """
    day = comp["day_start"][:10]
    hours = {}
    for row in comp["hourly"]:
        if row["from"].startswith(day):
            hours[int(row["from"][11:13]) + 1] = row["viewers"]
    if len(hours) != 24 or hours.get(1, 0) <= 0:
        return None
    return hours


def tier(comp: dict) -> str:
    """The tier the house's research note assigns ('comparable', 'early-access-contaminated', 'weak', ...)."""
    import re

    m = re.search(r"Tier: ([^.]+)", comp.get("unlock", ""))
    return m.group(1) if m else "?"


def fit_curves(case: dict) -> list:
    """The usable comparables as (log hour-1, {hour: log-ratio}) pairs."""
    curves = []
    for comp in case.get("comparables", []):
        if tier(comp) != "comparable":
            continue
        hours = release_day_hours(comp)
        if hours is None or hours[1] < MIN_HOUR1:
            continue
        p1 = hours[1]
        curves.append((math.log(p1 / SCALE), {h: math.log(hours[h] / p1) for h in range(2, 25)}))
    return curves


def linfit(xs: list, ys: list) -> tuple:
    """Least-squares y = a + b*x; returns (a, b, population sd of the residuals)."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = sxy / sxx if sxx else 0.0
    a = my - b * mx
    resid = [y - (a + b * x) for x, y in zip(xs, ys)]
    sd = statistics.pstdev(resid) if n > 2 else 0.5
    return a, b, sd


def median_curve(curves: list) -> tuple:
    """Per-hour median log-ratio and cross-launch spread, for the fallback."""
    med = {}
    spread = {}
    for h in range(2, 25):
        vals = sorted(lr[h] for _, lr in curves)
        n = len(vals)
        med[h] = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
        spread[h] = max(SPREAD_FLOOR, min(SPREAD_CAP, statistics.pstdev(vals)))
    return med, spread


def forecast_case(case: dict, name: str) -> dict:
    if case["levels"] != LEVELS:
        raise ValueError(f"{name} asks for levels {case['levels']}, not {LEVELS}")
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1, first["viewers"])

    curves = fit_curves(case)
    if len(curves) >= MIN_CURVES:
        xs = [x for x, _ in curves]
        x0 = math.log(p1 / SCALE)
        # Do not extrapolate the line past the launches it was fitted on.
        x0 = min(max(x0, min(xs)), max(xs))
        med = {}
        spread = {}
        for h in range(2, 25):
            a, b, sd = linfit(xs, [lr[h] for _, lr in curves])
            med[h] = a + b * x0
            spread[h] = max(SPREAD_FLOOR, min(SPREAD_CAP, sd))
        peak = max(med[h] for h in range(13, 25))
        if peak < EVENING_FLOOR:
            shift = EVENING_FLOOR - peak
            for h in range(13, 25):
                med[h] += shift
    elif curves:
        med, spread = median_curve(curves)
    else:
        # No usable comparables at all: the house baseline's persistence.
        med = {h: 0.0 for h in range(2, 25)}
        spread = {h: 0.15 * math.sqrt(h - 1) for h in range(2, 25)}

    hours = []
    for row in case["forecast"]:
        h = row["hour"]
        q = []
        for z in Z:
            v = round2(p1 * math.exp(med[h] + z * spread[h]))
            v = max(1.0, min(1e9, v))
            q.append(v)
        # Non-decreasing by construction (z rises, spread > 0); enforce it
        # anyway against rounding.
        for i in range(1, 5):
            q[i] = max(q[i], q[i - 1])
        hours.append({"hour": h, "q": q})
    return {"hours": hours}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Every case file, in name order, so two runs write the same bytes.
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
