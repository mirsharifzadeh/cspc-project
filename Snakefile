import glob

RAW_FILES = sorted(glob.glob("data/PRSA_Data_*.csv"))

rule all:
    input:
        "results/cleaned_data.csv"

rule preprocess:
    input:
        script = "src/processing.py",
        data = RAW_FILES
    output:
        "results/cleaned_data.csv"
    shell:
        "python {input.script}"