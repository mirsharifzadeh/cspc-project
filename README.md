# Beijing Multi-Site Air-Quality Data Analysis

This project is designed for the cleaning, statistical analysis, hypothesis testing, and optimization of hourly air quality and meteorological data (2013–2017) collected from 12 monitoring stations across Beijing.

## Project Structure

```text
cspc-project/
├── data/               # Raw CSV files for the 12 monitoring stations (PRSA_Data_*.csv)
├── src/                # Python modules for data processing and analysis
│   ├── processing.py       # Data merging, sorting, and missing value imputation
│   ├── correlation.py      # Distribution (normality) tests and correlation analysis
│   ├── hypothesis_tests.py # Mann-Whitney U hypothesis testing and stratified correlations
│   └── optimization.py     # Numerical calculus, predictive modeling, weather regimes, and SLSQP optimization
├── results/            # Processed datasets, statistical tables, and visualizations
├── tests/              # Unit tests
├── environment.yml     # Conda environment dependencies
├── Snakefile           # Workflow automation using Snakemake
└── README.md           # Project documentation
```

## Stage 0: Data Preprocessing Methodology (`src/processing.py`)

To prevent spatial boundary leakage across different monitoring sites and preserve temporal continuity, the following preprocessing pipeline was implemented:

1. **Merging & Cleaning:** All 12 raw CSV files in `data/` are loaded, concatenated into a single unified `DataFrame`, and the redundant index column (`No`) is removed.
2. **Chronological Ordering:** A unified `datetime` column is constructed from `year`, `month`, `day`, and `hour`, and the dataset is sorted by `['station', 'datetime']`.
3. **Station-Wise Imputation (`groupby('station')`):**
   * **Numerical Sensor Features** (`PM2.5`, `PM10`, `SO2`, `NO2`, `CO`, `O3`, `TEMP`, `PRES`, `DEWP`, `RAIN`, `WSPM`): Imputed independently within each station using time-series `linear` interpolation, followed by `bfill` and `ffill` to handle boundary gaps.
   * **Categorical Feature** (`wd` — wind direction): Imputed within each station using forward-fill (`ffill`) and backward-fill (`bfill`).
4. **Quality Verification:** An `assert` check confirms zero remaining missing values (`NaN`) across the entire dataset before exporting the cleaned output to `results/cleaned_data.csv`.

## Setup and Execution

1. **Activate the Conda environment:**
   ```bash
   conda activate project
   ```

2. **Run the workflow via Snakemake:**
   Execute the following command from the project root directory to automate data preprocessing:
   ```bash
   snakemake --cores 1
   ```
   
## Stage 1: Normality Testing & Correlation Analysis (`src/correlation.py`)

### 1. Normality Assessment & Method Justification
Before computing relationships between variables, all 11 numerical parameters (`PM2.5`, `PM10`, `SO2`, `NO2`, `CO`, `O3`, `TEMP`, `PRES`, `DEWP`, `RAIN`, `WSPM`) were tested for Gaussian distribution using **D'Agostino's K² test** (`scipy.stats.normaltest`) alongside **skewness** measurements:
* **Result:** Every variable rejected the null hypothesis of normality (`p < 0.05`, `is_normal = False`).
* **Physical & Statistical Reasoning:**
  * **Right-Skewed Pollutants & Precipitation:** Concentrations such as `PM2.5` (`skew ≈ 2.02`), `CO` (`skew ≈ 2.63`), `SO2` (`skew ≈ 3.18`), and `RAIN` (`skew ≈ 30.06`) are bounded at zero and exhibit long right tails due to acute winter smog episodes and heavy rainfall events.
  * **Large Sample Sensitivity:** Meteorological variables (`TEMP`, `PRES`, `DEWP`) display near-zero skewness (`≈ ±0.10` to `-0.19`), yet still yield `p = 0.0` due to seasonal bimodality amplified by the large sample size (`N = 420,768`).
* **Methodological Choice:** Because parametric assumptions are violated across the dataset, **Spearman's rank correlation (ρ)** was selected over Pearson's linear correlation (`r`) as the primary metric, supported by non-parametric hypothesis tests in subsequent stages.

### 2. Key Correlation Findings
The Spearman correlation matrix (`results/correlation_spearman.csv`) and heatmap (`results/graphs/correlation_heatmap.png`) reveal clear atmospheric and physical patterns:
* **Combustion & Traffic Cluster:** Strong positive correlations exist among `PM2.5`, `PM10` (`ρ = 0.89`), `CO` (`ρ = 0.82`), and `NO2` (`ρ = 0.66`), indicating shared emission sources such as vehicular exhaust and coal/fossil fuel combustion.
* **Photochemical Ozone Dynamics:** Surface ozone (`O3`) correlates positively with temperature (`TEMP`, `ρ = 0.58`) and negatively with `NO2` (`ρ = -0.61`), reflecting sunlight-driven photochemical reactions that consume `NO2` to generate `O3`.
* **Wind Dispersion Effect:** Wind speed (`WSPM`) shows consistent negative correlations with `NO2` (`ρ = -0.44`), `CO` (`ρ = -0.38`), and `PM2.5` (`ρ = -0.33`), confirming atmospheric dispersion and pollutant clearance during windy conditions.
* **Meteorological Consistency:** Temperature (`TEMP`) exhibits a strong inverse relationship with atmospheric pressure (`PRES`, `ρ = -0.82`) and a strong positive correlation with dew point (`DEWP`, `ρ = 0.82`).

### 3. Updated Snakemake Outputs
Running `snakemake --cores 1` now additionally generates:
* `results/normality_tests.csv` — D'Agostino K² statistics, p-values, and skewness coefficients.
* `results/correlation_spearman.csv` & `results/correlation_pearson.csv` — Full pairwise correlation matrices.
* `results/graphs/correlation_heatmap.png` — Annotated Spearman correlation heatmap.

## Stage 2: Numerical Calculus, Predictive Modeling, Weather Regimes & Precursor Optimization (`src/optimization.py`)

### 1. Numerical Differentiation & Exposure Integration
To quantify both short-term pollution buildup/clearance dynamics and long-term population exposure across the 12 monitoring stations without cross-station boundary artifacts, numerical calculus methods were applied within each station (`groupby('station')`):
- **Rate of Change (`np.gradient`):** Computed hourly finite-difference derivatives ($d[\text{PM}_{2.5}]/dt$ in $\mu\text{g}/(\text{m}^3\cdot\text{h})$) across each station's continuous time series and summarized by median, interquartile range (IQR), and 95% confidence intervals across seasons and sites (`results/pm25_rate_of_change.csv`, `results/graphs/pm25_rate_of_change.png`).
- **Cumulative & Seasonal Exposure (`cumulative_trapezoid` & `trapezoid`):** Integrated hourly $\text{PM}_{2.5}$ concentrations over time using the trapezoidal rule (converted from $\mu\text{g}\cdot\text{h}/\text{m}^3$ to $\mu\text{g}\cdot\text{day}/\text{m}^3$ by dividing by 24). Winter seasons were grouped across the December–February boundary (`season_year = year + (month == 12)`) to avoid multi-month integration gaps (`results/pm25_exposure.csv`, `results/graphs/cumulative_exposure.png`).

### 2. Predictive Modeling & Time-Series Validation Strategy
Because `PM2.5` exhibits strong right skewness (established in Stage 1), models were trained to predict $\log(1 + \text{PM}_{2.5})$ using gaseous precursors (`SO2`, `NO2`, `CO`, `O3`) and meteorological features (`TEMP`, `PRES`, `DEWP`, `RAIN`, `WSPM`, plus cyclical wind-direction components $\sin\theta, \cos\theta$):
- **Model Comparison:** Evaluated **Linear Regression**, **Polynomial Regression (degree 2)**, and **Decision Tree Regressors** (with `max_depth` tuned on a held-out validation fold) using `StandardScaler` fitted strictly on training partitions to prevent data leakage (`results/model_performance.csv`, `results/model_coefficients.csv`).
- **Random vs. Chronological Hold-Out Validation:** Compared standard random `80/20` splits against chronological splits (`VAL_START = 2015-03-01`, `TEST_START = 2016-03-01`), demonstrating that random splits inflate $R^2$ due to hourly autocorrelation whereas chronological testing measures true out-of-sample generalization across seasons.

### 3. Synoptic Weather Regime Clustering (`PCA` + `KMeans`)
To identify distinct atmospheric regimes governing air quality:
- **Dimensionality Reduction & Clustering:** Eight standardized meteorological and log-pollution features (`TEMP`, `PRES`, `DEWP`, `RAIN`, `WSPM`, wind-direction components, and $\log(1 + \text{PM}_{2.5})$) were projected onto **3 principal components (`PCA`)** and partitioned into **4 synoptic clusters (`KMeans`)** (`results/weather_regimes.csv`, `results/graphs/weather_regimes_pca.png`).
- **Physical Interpretation:** Separates cold, stagnant, high-pressure winter accumulation regimes (high $\text{PM}_{2.5}$, low wind speed) from well-ventilated northwesterly dispersion regimes and warm, humid summer photochemical regimes.

### 4. Constrained Precursor Abatement Optimization (`SLSQP`)
To evaluate emission-control strategies for reducing mean $\text{PM}_{2.5}$ below target thresholds ($75, 100, 150\ \mu\text{g}/\text{m}^3$) across each station and city-wide (`"All"`):
- **Formulation:** Minimized total quadratic abatement effort $J(x) = x_{\text{SO}_2}^2 + x_{\text{NO}_2}^2 + x_{\text{CO}}^2$ using Sequential Least Squares Programming (`scipy.optimize.minimize(..., method="SLSQP")`), subject to bounds $0 \le x_i \le 0.80$ (maximum 80% precursor reduction) and the nonlinear inequality constraint $\widehat{\text{PM}}_{2.5}(x) \le \text{target}$ (`results/abatement_scenarios.csv`).

### 5. Updated Snakemake Outputs
Running `snakemake --cores 1` additionally generates:
- `results/pm25_rate_of_change.csv` & `results/graphs/pm25_rate_of_change.png` — Station and seasonal $d[\text{PM}_{2.5}]/dt$ summary statistics and distributions.
- `results/pm25_exposure.csv` & `results/graphs/cumulative_exposure.png` — Trapezoidal cumulative and seasonal $\text{PM}_{2.5}$ exposure integrals.
- `results/model_performance.csv` & `results/model_coefficients.csv` — Regression and decision-tree metrics ($R^2$, adjusted $R^2$, RMSE, MAE) across random and chronological splits.
- `results/weather_regimes.csv` & `results/graphs/weather_regimes_pca.png` — PCA + KMeans weather regime cluster profiles and spatial shares.
- `results/abatement_scenarios.csv` — Optimal precursor reduction percentages ($\text{SO}_2$, $\text{NO}_2$, $\text{CO}$) per target threshold and station.

---

## Stage 3: Statistical Hypothesis Testing & Stratified Correlation (`src/hypothesis_tests.py`)

### 1. Feature Engineering & Group Summaries
- **Derived Features (`add_features`):** Mapped months to seasons (`Spring`, `Summer`, `Autumn`, `Winter`), converted 16-point wind directions (`wd`) to cyclical components ($\sin\theta, \cos\theta$), and computed relative humidity ($\text{RH}$ in %) from `TEMP` and `DEWP` via the Magnus-Tetens approximation.
- **Descriptive Summaries (`summarize`):** Computed $n$, median, IQR, mean, standard error, and 95% confidence intervals across all seasons and meteorological regimes (`results/pm25_group_summary.csv`, `results/graphs/pm25_by_season.png`).

### 2. Mann-Whitney $U$ Hypothesis Tests
- **Pairwise & Regime Comparisons (`compare_groups`):** Conducted two-sided Mann-Whitney $U$ tests ($\alpha = 0.05$) with rank-biserial effect sizes ($r_{\text{rb}} = \frac{2U}{n_a n_b} - 1$) across all 6 seasonal pairs and 3 weather regimes—wind ($\text{WSPM} < 1.5$ vs. $\ge 3.0$), rain ($\text{RAIN} = 0$ vs. $> 0$), and humidity ($\text{RH} \le 25\text{th}$ vs. $\ge 75\text{th}$ percentile)—both pooled (`"All"`) and within each season (`results/mannwhitney_tests.csv`).

### 3. Stratified Correlation Analysis
- **Station & Season Correlations (`safe_corr`):** Computed Spearman ($\rho$) and Pearson ($r$) correlations with $p$-values between $\text{PM}_{2.5}$ and meteorological variables (`TEMP`, `PRES`, `DEWP`, `RAIN`, `WSPM`, `wd_sin`, `wd_cos`) grouped by `(station, season)` (`results/stratified_correlation.csv`, `results/graphs/stratified_spearman_heatmap.png`).

### 4. Updated Snakemake Outputs
Running `snakemake --cores 1` additionally generates:
- `results/pm25_group_summary.csv` & `results/graphs/pm25_by_season.png` — Seasonal and regime-level $\text{PM}_{2.5}$ summary statistics and seasonal boxplots.
- `results/mannwhitney_tests.csv` — Pairwise seasonal and weather regime Mann-Whitney $U$ statistics, $p$-values, and rank-biserial effect sizes.
- `results/stratified_correlation.csv` & `results/graphs/stratified_spearman_heatmap.png` — Station- and season-stratified Spearman/Pearson correlations and 4-panel seasonal heatmaps.