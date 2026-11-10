"""Portfolio math: recommended mix, backtest, statistics and Monte Carlo projection."""
import numpy as np
import pandas as pd

TRAINING_STAGES = ("Medical Student", "Resident", "Fellow")


def recommended_equity(p):
    """Recommended % in stocks.

    Rule: 120 - age, because a physician's future paychecks are large and
    steady (they behave like a bond), so the investment account can hold
    more stocks than a typical household. Trainees get +5 because nearly all
    of their wealth is still future earnings. Kept between 30% and 95%.
    """
    base = 120 - p.age
    if p.career_stage in TRAINING_STAGES:
        base += 5
    return int(np.clip(round(base / 5) * 5, 30, 95))


def backtest(rets, w_stock, fee=0.0, rebalance="Annual"):
    """Growth of $1 (after inflation and fees) for a stock/bond mix."""
    target = np.array([w_stock, 1 - w_stock])
    r = rets[["stocks", "bonds"]].to_numpy()
    months = rets.index
    holdings = target.copy()
    values = []
    for i in range(len(r)):
        holdings = holdings * (1 + r[i])
        total = holdings.sum() * (1 - fee / 12)
        holdings = holdings / holdings.sum() * total
        if rebalance == "Monthly" or (rebalance == "Annual" and months[i].month == 12):
            holdings = target * total
        values.append(total)
    nominal = pd.Series(values, index=months.to_timestamp())
    price_level = (1 + rets["inflation"]).cumprod().to_numpy()
    return nominal / price_level


def stats(v):
    """Summary statistics for a growth-of-$1 series."""
    full = pd.concat([pd.Series([1.0]), pd.Series(v.to_numpy())], ignore_index=True)
    monthly = full.pct_change().dropna()
    return {
        "cagr": full.iloc[-1] ** (12 / len(v)) - 1,
        "vol": monthly.std() * np.sqrt(12),
        "worst12": (full / full.shift(12) - 1).min(),
        "maxdd": (full / full.cummax() - 1).min(),
    }


def yearly_contributions(p, years, rate_training, rate_attending):
    """Dollars saved each year: low during training, higher once attending."""
    out = []
    for t in range(years):
        if t < p.training_years_left:
            out.append((p.current_income + p.spouse_income) * rate_training)
        else:
            out.append((p.expected_attending_income + p.spouse_income) * rate_attending)
    return np.array(out, dtype=float)


def simulate(rets, w_stock, fee, start_value, contributions, years,
             n_paths=2000, block=12, seed=42, forced=None):
    """Block-bootstrap Monte Carlo of real portfolio value.

    Draws random 12-month chunks of real history (keeps crashes and
    recoveries together), adds yearly contributions, and returns an array
    of shape (n_paths, years + 1) in today's dollars.
    """
    rng = np.random.default_rng(seed)
    port = w_stock * rets["stocks"].to_numpy() + (1 - w_stock) * rets["bonds"].to_numpy()
    real = (1 + port) / (1 + rets["inflation"].to_numpy()) - 1 - fee / 12

    n_months = years * 12
    n_blocks = int(np.ceil(n_months / block))
    starts = rng.integers(0, len(real) - block, size=(n_paths, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)).reshape(n_paths, -1)[:, :n_months]
    path_returns = real[idx]

    # Optional: replay a real historical crash starting at a given month
    if forced is not None:
        start, crash = forced
        end = min(n_months, start + len(crash))
        if 0 <= start < n_months:
            path_returns[:, start:end] = crash[:end - start]

    monthly_add = np.repeat(np.asarray(contributions, dtype=float) / 12, 12)
    wealth = np.empty((n_paths, years + 1))
    wealth[:, 0] = start_value
    w = np.full(n_paths, float(start_value))
    for m in range(n_months):
        w = np.maximum(0, w * (1 + path_returns[:, m]) + monthly_add[m])
        if (m + 1) % 12 == 0:
            wealth[:, (m + 1) // 12] = w
    return wealth