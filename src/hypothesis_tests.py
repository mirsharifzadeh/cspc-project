from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, pearsonr, sem, spearmanr
import matplotlib.pyplot as plt
import seaborn as sns

BASE_DIR=Path(__file__).resolve().parent.parent

ALPHA=0.05
SEASONS=["Spring", "Summer", "Autumn", "Winter"]
SEASON_MAP={3: "Spring", 4: "Spring", 5: "Spring",
            6: "Summer", 7: "Summer", 8: "Summer",
            9: "Autumn", 10: "Autumn", 11: "Autumn",
            12: "Winter", 1: "Winter", 2: "Winter"}
WD_DEG={"N": 0.0, "NNE": 22.5, "NE": 45.0, "ENE": 67.5,
        "E": 90.0, "ESE": 112.5, "SE": 135.0, "SSE": 157.5,
        "S": 180.0, "SSW": 202.5, "SW": 225.0, "WSW": 247.5,
        "W": 270.0, "WNW": 292.5, "NW": 315.0, "NNW": 337.5}
MET_COLS=['TEMP', 'PRES', 'DEWP', 'RAIN', 'WSPM', 'wd_sin', 'wd_cos']


def relative_humidity(temp, dewp, a=17.625, b=243.04):
    rh=100*np.exp(a*dewp/(b+dewp)-a*temp/(b+temp))
    return np.clip(rh, 0, 100)


def add_features(df):
    df=df.copy()
    df['season']=df['month'].map(SEASON_MAP)
    angle=np.deg2rad(df['wd'].map(WD_DEG))
    df['wd_sin']=np.sin(angle)
    df['wd_cos']=np.cos(angle)
    df['RH']=relative_humidity(df['TEMP'], df['DEWP'])
    return df


def summarize(x):
    x=np.asarray(x, dtype=float)
    q1, med, q3=np.percentile(x, [25, 50, 75])
    se=sem(x)
    return {"n": len(x), "median": med, "q1": q1, "q3": q3, "iqr": q3-q1,
            "mean": x.mean(), "se": se,
            "ci_low": x.mean()-1.96*se, "ci_high": x.mean()+1.96*se}


def compare_groups(a, b):
    a=np.asarray(a, dtype=float)
    b=np.asarray(b, dtype=float)
    u, p=mannwhitneyu(a, b, alternative="two-sided", method="asymptotic")
    sa, sb=summarize(a), summarize(b)
    return {"n_a": sa["n"], "n_b": sb["n"],
            "median_a": sa["median"], "median_b": sb["median"],
            "iqr_a": sa["iqr"], "iqr_b": sb["iqr"],
            "u_stat": u, "p_val": p,
            "rank_biserial": 2*u/(len(a)*len(b))-1,
            "significant": p<ALPHA}


def safe_corr(func, x, y):
    if x.nunique()<2 or y.nunique()<2:
        return np.nan, np.nan
    stat, p=func(x, y)
    return stat, p


def main():
    output_dir=BASE_DIR/"results"
    graph_dir=output_dir/"graphs"
    graph_dir.mkdir(parents=True, exist_ok=True)

    df=pd.read_csv(BASE_DIR/"results"/"cleaned_data.csv")
    df=add_features(df)

    rh_lo, rh_hi=df['RH'].quantile([0.25, 0.75])

    summary_rows=[]
    test_rows=[]

    for season in SEASONS:
        row={"context": "All", "group": season}
        row.update(summarize(df.loc[df['season']==season, 'PM2.5']))
        summary_rows.append(row)

    for i in range(len(SEASONS)):
        for j in range(i+1, len(SEASONS)):
            a, b=SEASONS[i], SEASONS[j]
            row={"test": "season", "context": "All", "group_a": a, "group_b": b}
            row.update(compare_groups(df.loc[df['season']==a, 'PM2.5'], df.loc[df['season']==b, 'PM2.5']))
            test_rows.append(row)

    for context in ["All"]+SEASONS:
        sub=df if context=="All" else df[df['season']==context]
        regimes={
            "wind": ("stagnant (WSPM<1.5)", sub['WSPM']<1.5, "windy (WSPM>=3.0)", sub['WSPM']>=3.0),
            "rain": ("dry (RAIN=0)", sub['RAIN']==0, "rainy (RAIN>0)", sub['RAIN']>0),
            "humidity": ("low RH", sub['RH']<=rh_lo, "high RH", sub['RH']>=rh_hi)
        }
        for regime, (name_a, mask_a, name_b, mask_b) in regimes.items():
            pm_a=sub.loc[mask_a, 'PM2.5']
            pm_b=sub.loc[mask_b, 'PM2.5']
            if len(pm_a)<2 or len(pm_b)<2:
                continue
            r_a={"context": context, "group": f"{regime}: {name_a}"}
            r_a.update(summarize(pm_a))
            r_b={"context": context, "group": f"{regime}: {name_b}"}
            r_b.update(summarize(pm_b))
            summary_rows.extend([r_a, r_b])

            t_row={"test": regime, "context": context, "group_a": name_a, "group_b": name_b}
            t_row.update(compare_groups(pm_a, pm_b))
            test_rows.append(t_row)

    pd.DataFrame(summary_rows).to_csv(output_dir/"pm25_group_summary.csv", index=False)
    pd.DataFrame(test_rows).to_csv(output_dir/"mannwhitney_tests.csv", index=False)

    corr_rows=[]
    for (station, season), g in df.groupby(['station', 'season']):
        for col in MET_COLS:
            rho, p_s=safe_corr(spearmanr, g['PM2.5'], g[col])
            r, p_p=safe_corr(pearsonr, g['PM2.5'], g[col])
            corr_rows.append({"station": station, "season": season, "variable": col, "n": len(g),
                              "spearman_rho": rho, "spearman_p": p_s, "spearman_significant": p_s<ALPHA,
                              "pearson_r": r, "pearson_p": p_p, "pearson_significant": p_p<ALPHA})

    corr_df=pd.DataFrame(corr_rows)
    corr_df.to_csv(output_dir/"stratified_correlation.csv", index=False)

    plt.figure(figsize=(8, 6))
    sns.boxplot(data=df, x="season", y="PM2.5", order=SEASONS, showfliers=False)
    plt.title("PM2.5 by Season (all stations)")
    plt.savefig(graph_dir/"pm25_by_season.png", dpi=300, bbox_inches="tight")
    plt.close()

    fig, axes=plt.subplots(2, 2, figsize=(14, 11), sharey=True)
    for ax, season in zip(axes.ravel(), SEASONS):
        pivot=corr_df[corr_df['season']==season].pivot(index="station", columns="variable", values="spearman_rho")
        sns.heatmap(pivot[MET_COLS], annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1, cbar=False, ax=ax)
        ax.set_title(season)
        ax.set_xlabel("")
    fig.suptitle("Spearman Correlation of PM2.5 with Meteorology by Station and Season")
    plt.savefig(graph_dir/"stratified_spearman_heatmap.png", dpi=300, bbox_inches="tight")
    plt.close()


if __name__=="__main__":
    main()