import glob

RAW_FILES = sorted(glob.glob("data/PRSA_Data_*.csv"))

rule all:
    input:
        "results/cleaned_data.csv",
        "results/normality_tests.csv",
        "results/correlation_spearman.csv",
        "results/correlation_pearson.csv",
        "results/graphs/correlation_heatmap.png"

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