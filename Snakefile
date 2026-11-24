import glob

RAW_FILES = sorted(glob.glob("data/PRSA_Data_*.csv"))

rule all:
    input:
        "results/cleaned_data.csv",
        "results/normality_tests.csv",
        "results/correlation_spearman.csv",
        "results/correlation_pearson.csv",
        "results/graphs/correlation_heatmap.png",
        "results/pm25_rate_of_change.csv",
        "results/pm25_exposure.csv",
        "results/model_performance.csv",
        "results/model_coefficients.csv",
        "results/weather_regimes.csv",
        "results/abatement_scenarios.csv",
        "results/graphs/pm25_rate_of_change.png",
        "results/graphs/cumulative_exposure.png",
        "results/graphs/weather_regimes_pca.png"

rule preprocess:
    input:
        script = "src/processing.py",
        data = RAW_FILES
    output:
        "results/cleaned_data.csv"
    shell:
        "python {input.script}"

rule correlation:
    input:
        script = "src/correlation.py",
        data = "results/cleaned_data.csv"
    output:
        "results/normality_tests.csv",
        "results/correlation_spearman.csv",
        "results/correlation_pearson.csv",
        "results/graphs/correlation_heatmap.png"
    shell:
        "python {input.script}"

rule optimization:
    input:
        script = "src/optimization.py",
        data = "results/cleaned_data.csv"
    output:
        "results/pm25_rate_of_change.csv",
        "results/pm25_exposure.csv",
        "results/model_performance.csv",
        "results/model_coefficients.csv",
        "results/weather_regimes.csv",
        "results/abatement_scenarios.csv",
        "results/graphs/pm25_rate_of_change.png",
        "results/graphs/cumulative_exposure.png",
        "results/graphs/weather_regimes_pca.png"
    shell:
        "python {input.script}"