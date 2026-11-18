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

## Data Preprocessing Methodology (`src/processing.py`)

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