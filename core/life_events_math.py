"""Turns life events into a year-by-year savings plan, and replays real crashes."""
import numpy as np
import pandas as pd

# Real historical periods replayed month by month (from the CRSP / FRED data)
CRASHES = {
    "2008 financial crisis": ("2007-10", "2009-09"),
    "2000 dot-com crash": ("2000-01", "2002-12"),
    "2020 COVID crash": ("2020-01", "2020-12"),
    "2022 stocks and bonds fall together": ("2022-01", "2022-12"),
}


def crash_returns(rets, name, w_stock, fee):
    """Monthly real portfolio returns during a historical crash."""
    start, end = CRASHES[name]
    r = rets.loc[pd.Period(start, "M"):pd.Period(end, "M")]
    port = w_stock * r["stocks"] + (1 - w_stock) * r["bonds"]
    return ((1 + port) / (1 + r["inflation"]) - 1 - fee / 12).to_numpy()


def build_plan(p, ev, save_train, save_att):
    """Yearly savings (contributions) and physician income, given active events.

    ev holds only the events that are switched on, e.g.
    {"fellowship": {...}, "house": {...}}.
    """
    years = max(1, p.target_retire_age - p.age)
    fel = ev.get("fellowship")
    train_end = p.training_years_left + (fel["years"] if fel else 0)
    attending = fel["new_income"] if fel else p.expected_attending_income

    contrib, income = [], []
    for t in range(years):
        age = p.age + t
        if t < p.training_years_left:
            md, rate = p.current_income, save_train
        elif t < train_end:
            md, rate = fel["pay"], save_train
        else:
            md, rate = attending, save_att

        if "parttime" in ev and age >= ev["parttime"]["age"]:
            md *= ev["parttime"]["pct"]
        if "jobloss" in ev and age == ev["jobloss"]["age"]:
            md *= 1 - ev["jobloss"]["months"] / 12
        if "disability" in ev and age >= ev["disability"]["age"]:
            md *= ev["disability"]["benefit"]  # 0 if uninsured

        save = rate * (md + p.spouse_income)

        if "kids" in ev:
            k = ev["kids"]
            for i in range(k["n"]):
                born = k["age"] + 2 * i
                if 0 <= age - born < 18:
                    save -= k["cost"]
        if "house" in ev and age == ev["house"]["age"]:
            save -= ev["house"]["down"]
        if "inheritance" in ev and age == ev["inheritance"]["age"]:
            save += ev["inheritance"]["amount"]

        contrib.append(save)
        income.append(md)
    return np.array(contrib, dtype=float), np.array(income, dtype=float), years