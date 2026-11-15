"""Portfolio math: recommended mix, backtest, statistics and Monte Carlo projection."""
import numpy as np
import pandas as pd



def recommended_equity(p):
    """Recommended % in stocks today. The full rule (tolerance, capacity, human capital,
    age) lives in core/risk.py; this wrapper keeps older imports working."""
    from core.risk import recommended_equity as rec
    return rec(p)["equity"]


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


def stats(v, cash_real=None):
    """Summary statistics for a growth-of-$1 series (real). cash_real = monthly real
    T-bill returns for the same months, used for the Sharpe ratio."""
    full = pd.concat([pd.Series([1.0]), pd.Series(v.to_numpy())], ignore_index=True)
    monthly = full.pct_change().dropna()
    if cash_real is not None and len(cash_real) == len(monthly):
        ex = monthly.to_numpy() - np.asarray(cash_real)
        sharpe = ex.mean() * 12 / (ex.std() * np.sqrt(12)) if ex.std() > 0 else np.nan
    else:
        sharpe = np.nan
    return {
        "sharpe": sharpe,
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
    w_stock: a single stock weight, or one weight per year (a glide path).
    """
    rng = np.random.default_rng(seed)
    infl = 1 + rets["inflation"].to_numpy()
    s_real = (1 + rets["stocks"].to_numpy()) / infl - 1
    b_real = (1 + rets["bonds"].to_numpy()) / infl - 1

    n_months = years * 12
    n_blocks = int(np.ceil(n_months / block))
    starts = rng.integers(0, len(s_real) - block, size=(n_paths, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)).reshape(n_paths, -1)[:, :n_months]
    # w_stock may be one number (fixed mix) or one number per year (glide path)
    w = np.asarray(w_stock, dtype=float)
    w_month = np.repeat(np.resize(w, years), 12) if w.ndim else np.full(n_months, float(w))
    path_returns = w_month * s_real[idx] + (1 - w_month) * b_real[idx] - fee / 12

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

def cash_real(rets):
    """Monthly real return on T-bills (Fama-French risk-free rate deflated by CPI)."""
    return ((1 + rets["cash"]) / (1 + rets["inflation"]) - 1).to_numpy()


def in_vs_out_of_sample(rets, rule_equity, fee, rebalance):
    """Split history in half. 'Optimize' the stock/bond mix on the first half (best Sharpe
    ratio), then see how that choice, the recommended rule and 60/40 do on the unseen half."""
    years = rets.index.year
    split = int(years.min() + (years.max() - years.min()) // 2)
    first, second = rets[years <= split], rets[years > split]

    def sharpe_of(r, w):
        return stats(backtest(r, w, fee, rebalance), cash_real(r))["sharpe"]

    grid = np.arange(0, 101, 5) / 100
    best = float(grid[int(np.nanargmax([sharpe_of(first, w) for w in grid]))])
    rows = []
    for label, w in [(f"Optimized on {years.min()}-{split} ({best:.0%} stocks)", best),
                     (f"Recommended rule ({rule_equity:.0%} stocks)", rule_equity),
                     ("60/40 benchmark", 0.60)]:
        a = stats(backtest(first, w, fee, rebalance), cash_real(first))
        b = stats(backtest(second, w, fee, rebalance), cash_real(second))
        rows.append({"Strategy": label,
                     f"In-sample return ({years.min()}-{split})": f"{a['cagr']:.1%}",
                     "In-sample Sharpe": f"{a['sharpe']:.2f}",
                     f"Out-of-sample return ({split + 1}-{years.max()})": f"{b['cagr']:.1%}",
                     "Out-of-sample Sharpe": f"{b['sharpe']:.2f}"})
    return pd.DataFrame(rows), best, split
