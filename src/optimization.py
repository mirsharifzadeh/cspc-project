from pathlib import Path
import numpy as np
import pandas as pd
from scipy.integrate import cumulative_trapezoid, trapezoid
from scipy.optimize import minimize
from scipy.stats import sem
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.tree import DecisionTreeRegressor
import matplotlib.pyplot as plt
import seaborn as sns

BASE_DIR=Path(__file__).resolve().parent.parent

RANDOM_STATE=42
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
TREE_DEPTHS=[3, 4, 5, 6, 8, 10, 12, 15, 20]
VAL_START=pd.Timestamp("2015-03-01")
TEST_START=pd.Timestamp("2016-03-01")
N_CLUSTERS=4
PRECURSORS=['SO2', 'NO2', 'CO']
TARGETS=[75, 100, 150]
MAX_CUT=0.8

def add_features(df):
    df=df.copy()
    df['season']=df['month'].map(SEASON_MAP)
    angle=np.deg2rad(df['wd'].map(WD_DEG))
    df['wd_sin']=np.sin(angle)
    df['wd_cos']=np.cos(angle)
    return df

def summarize(x):
    x=np.asarray(x, dtype=float)
    q1, med, q3=np.percentile(x, [25, 50, 75])
    se=sem(x)
    return {"n": len(x), "median": med, "q1": q1, "q3": q3, "iqr": q3 - q1,
            "mean": x.mean(), "se": se,
            "ci_low": x.mean() - 1.96*se, "ci_high": x.mean() + 1.96*se}

def rate_of_change(df, col="PM2.5"):
    rate=pd.Series(np.nan, index=df.index)
    for _, g in df.groupby('station'):
        rate.loc[g.index]=np.gradient(g[col].to_numpy(), g['t'].to_numpy())
    return rate

def cumulative_exposure(df, col="PM2.5"):
    cum=pd.Series(np.nan, index=df.index)
    for _, g in df.groupby('station'):
        cum.loc[g.index]=cumulative_trapezoid(g[col].to_numpy(), x=g['t'].to_numpy(), initial=0)/24
    return cum

def adjusted_r2(r2, n, p):
    return 1 - (1 - r2)*(n - 1)/(n - p - 1)

def evaluate(y_true, y_pred, p):
    mse=mean_squared_error(y_true, y_pred)
    r2=r2_score(y_true, y_pred)
    return {"mse": mse, "rmse": np.sqrt(mse), "mae": mean_absolute_error(y_true, y_pred),
            "r2": r2, "adj_r2": adjusted_r2(r2, len(y_true), p)}

def fit_models(X_train, y_train, X_test, y_test, X_fit, y_fit, X_val, y_val, split):
    scaler=StandardScaler().fit(X_train)
    Xtr=scaler.transform(X_train)
    Xte=scaler.transform(X_test)
    Xf=scaler.transform(X_fit)
    Xv=scaler.transform(X_val)
    linear=LinearRegression().fit(Xtr, y_train)
    poly=PolynomialFeatures(degree=2, include_bias=False).fit(Xtr)
    Ptr=poly.transform(Xtr)
    Pte=poly.transform(Xte)
    poly_lin=LinearRegression().fit(Ptr, y_train)
    val_mse={d: mean_squared_error(y_val, DecisionTreeRegressor(max_depth=d, random_state=RANDOM_STATE)
                                     .fit(Xf, y_fit).predict(Xv)) for d in TREE_DEPTHS}
    best_depth=min(val_mse, key=val_mse.get)
    tree=DecisionTreeRegressor(max_depth=best_depth, random_state=RANDOM_STATE).fit(Xtr, y_train)
    info={"split": split, "n_train": len(y_train), "n_test": len(y_test)}
    performance=[
        {"model": "linear", "best_depth": np.nan, **info, **evaluate(y_test, linear.predict(Xte), Xtr.shape[1])},
        {"model": "poly2_linear", "best_depth": np.nan, **info, **evaluate(y_test, poly_lin.predict(Pte), Ptr.shape[1])},
        {"model": "decision_tree", "best_depth": best_depth, **info, **evaluate(y_test, tree.predict(Xte), Xtr.shape[1])},
    ]
    coefficients=(
        [{"split": split, "model": "linear (standardized coef)", "feature": f, "value": v} for f, v in zip(MET_COLS, linear.coef_)]
        + [{"split": split, "model": "decision_tree (importance)", "feature": f, "value": v} for f, v in zip(MET_COLS, tree.feature_importances_)]
    )
    return performance, coefficients

def fit_season_models(sub):
    X=sub[MET_COLS]
    y=np.log1p(sub['PM2.5'])
    X_train, X_test, y_train, y_test=train_test_split(X, y, test_size=0.2, random_state=RANDOM_STATE)
    X_fit, X_val, y_fit, y_val=train_test_split(X_train, y_train, test_size=0.2, random_state=RANDOM_STATE)
    performance, coefficients=fit_models(X_train, y_train, X_test, y_test, X_fit, y_fit, X_val, y_val, "random_80_20")
    is_test=sub['datetime'] >= TEST_START
    is_val=(sub['datetime'] >= VAL_START) & ~is_test
    is_fit=sub['datetime'] < VAL_START
    perf_chrono, coef_chrono=fit_models(X[~is_test], y[~is_test], X[is_test], y[is_test],
                                        X[is_fit], y[is_fit], X[is_val], y[is_val], "chronological_last_year")
    return performance + perf_chrono, coefficients + coef_chrono

def predicted_mean_pm25(x, X, model, scaler):
    X_scn=X.copy()
    X_scn[PRECURSORS]=X[PRECURSORS]*(1 - np.asarray(x))
    return model.predict(scaler.transform(X_scn)).mean()

def solve_abatement(X, model, scaler, target, max_cut=MAX_CUT):
    constraint={"type": "ineq", "fun": lambda x: target - predicted_mean_pm25(x, X, model, scaler)}
    return minimize(lambda x: np.sum(x**2), x0=np.full(len(PRECURSORS), 0.1), method="SLSQP",
                    bounds=[(0, max_cut)]*len(PRECURSORS), constraints=[constraint])

def main():
    output_dir=BASE_DIR/"results"
    graph_dir=output_dir/"graphs"
    graph_dir.mkdir(parents=True, exist_ok=True)
    df=pd.read_csv(BASE_DIR/"results"/"cleaned_data.csv")
    df['datetime']=pd.to_datetime(df['datetime'])
    df=df.sort_values(['station', 'datetime'], ignore_index=True)
    df=add_features(df)
    df['t']=(df['datetime'] - df['datetime'].min()).dt.total_seconds()/3600
    df['season_year']=df['year'] + (df['month'] == 12)
    df['dPM25_dt']=rate_of_change(df)
    regimes={"stagnant (WSPM<1.5)": df['WSPM'] < 1.5,
             "windy (WSPM>=3.0)": df['WSPM'] >= 3.0,
             "rainy (RAIN>0)": df['RAIN'] > 0,
             "dry (RAIN=0)": df['RAIN'] == 0}
    rate_rows=[]
    for season in ["All"] + SEASONS:
        in_season=pd.Series(True, index=df.index) if season == "All" else df['season'] == season
        for name, mask in regimes.items():
            rate_rows.append({"season": season, "regime": name, **summarize(df.loc[in_season & mask, 'dPM25_dt'])})
    rate_df=pd.DataFrame(rate_rows)
    rate_df.to_csv(output_dir/"pm25_rate_of_change.csv", index=False)
    plt.figure(figsize=(10, 6))
    sns.barplot(data=rate_df, x="season", y="mean", hue="regime", errorbar=None)
    plt.axhline(0, color="black", linewidth=0.8)
    plt.ylabel("Mean d[PM2.5]/dt (ug/m3 per hour)")
    plt.title("PM2.5 Rate of Change by Season and Meteorological Regime")
    plt.savefig(graph_dir/"pm25_rate_of_change.png", dpi=300, bbox_inches="tight")
    plt.close()
    exposure_rows=[]
    for (station, season, season_year), g in df.groupby(['station', 'season', 'season_year']):
        exposure_rows.append({"station": station, "season": season,
                              "hours": g['t'].iloc[-1] - g['t'].iloc[0],
                              "exposure_ug_h_m3": trapezoid(g['PM2.5'].to_numpy(), x=g['t'].to_numpy())})
    exposure_df=pd.DataFrame(exposure_rows).groupby(['station', 'season'], as_index=False).sum()
    exposure_df["mean_pm25"]=exposure_df["exposure_ug_h_m3"]/exposure_df["hours"]
    exposure_df.to_csv(output_dir/"pm25_exposure.csv", index=False)
    df['cum_exposure']=cumulative_exposure(df)
    plt.figure(figsize=(11, 6))
    sns.lineplot(data=df[df['hour'] == 0], x="datetime", y="cum_exposure", hue="station", estimator=None, linewidth=1)
    plt.ylabel("Cumulative PM2.5 exposure (ug.day/m3)")
    plt.title("Cumulative PM2.5 Exposure by Station")
    plt.legend(fontsize=7, ncol=2)
    plt.savefig(graph_dir/"cumulative_exposure.png", dpi=300, bbox_inches="tight")
    plt.close()
    performance_rows=[]
    coefficient_rows=[]
    for season in SEASONS:
        performance, coefficients=fit_season_models(df[df['season'] == season])
        performance_rows+=[{"season": season, **row} for row in performance]
        coefficient_rows+=[{"season": season, **row} for row in coefficients]
    pd.DataFrame(performance_rows).to_csv(output_dir/"model_performance.csv", index=False)
    pd.DataFrame(coefficient_rows).to_csv(output_dir/"model_coefficients.csv", index=False)
    df['log_pm25']=np.log1p(df['PM2.5'])
    cluster_features=MET_COLS + ['log_pm25']
    Z=StandardScaler().fit_transform(df[cluster_features])
    pca=PCA(n_components=3, random_state=RANDOM_STATE)
    pcs=pca.fit_transform(Z)
    df['regime']=KMeans(n_clusters=N_CLUSTERS, n_init=10, random_state=RANDOM_STATE).fit_predict(pcs)
    profile=df.groupby('regime')[['TEMP', 'PRES', 'DEWP', 'RAIN', 'WSPM', 'PM2.5']].mean()
    profile.insert(0, "n", df['regime'].value_counts().sort_index())
    profile=profile.join(pd.crosstab(df['regime'], df['season'], normalize="index")[SEASONS].add_prefix("share_"))
    profile.to_csv(output_dir/"weather_regimes.csv")
    sample=df.sample(20000, random_state=RANDOM_STATE)
    plt.figure(figsize=(8, 6))
    sns.scatterplot(x=pcs[sample.index, 0], y=pcs[sample.index, 1], hue=sample['regime'], palette="tab10", s=6, alpha=0.5)
    plt.xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.1%} variance)")
    plt.ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.1%} variance)")
    plt.title("Synoptic Weather Regimes (PCA + KMeans)")
    plt.savefig(graph_dir/"weather_regimes_pca.png", dpi=300, bbox_inches="tight")
    plt.close()
    stagnant_winter=df[(df['season'] == "Winter") & (df['WSPM'] < 1.5)]
    scopes=[("All", stagnant_winter)] + list(stagnant_winter.groupby('station'))
    abatement_rows=[]
    for scope, sub in scopes:
        X=sub[PRECURSORS + MET_COLS]
        scaler=StandardScaler().fit(X)
        model=LinearRegression().fit(scaler.transform(X), sub['PM2.5'])
        baseline=predicted_mean_pm25(np.zeros(len(PRECURSORS)), X, model, scaler)
        floor=predicted_mean_pm25(np.full(len(PRECURSORS), MAX_CUT), X, model, scaler)
        for target in TARGETS:
            res=solve_abatement(X, model, scaler, target)
            achieved=predicted_mean_pm25(res.x, X, model, scaler)
            abatement_rows.append({"scope": scope, "n": len(sub), "model_r2": model.score(scaler.transform(X), sub['PM2.5']),
                                   "target": target, "baseline_pm25": baseline, "min_achievable_pm25": floor,
                                   "achieved_pm25": achieved,
                                   **{f"cut_{p}": c for p, c in zip(PRECURSORS, res.x)},
                                   "target_met": achieved <= target + 1e-6, "success": res.success, "message": res.message})
    pd.DataFrame(abatement_rows).to_csv(output_dir/"abatement_scenarios.csv", index=False)

if __name__ == "__main__":
    main()