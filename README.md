# Beijing Multi-Site Air-Quality Data Analysis

This project is designed for the cleaning, statistical analysis, hypothesis testing, and optimization of hourly air quality and meteorological data (2013–2017) collected from 12 monitoring stations across Beijing.

## Project Structure

```text
cspc-project/
├── data/               # Raw CSV files for the 12 monitoring stations (PRSA_Data_*.csv)
├── src/                # Python modules for data processing and analysis
│   ├── processing.py       # Data merging, sorting, and missing value imputation
│   ├── correlation.py      # Distribution (normality) tests and correlation analysis (Planned)
│   ├── hypothesis_tests.py # Statistical hypothesis testing (Planned)
│   └── optimization.py     # Optimization models (Planned)
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