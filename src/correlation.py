from pathlib import Path
import pandas as pd
from scipy.stats import normaltest, skew
import matplotlib.pyplot as plt
import seaborn as sns

BASE_DIR = Path(__file__).resolve().parent.parent

output_dir = BASE_DIR / "results"

df = pd.read_csv(BASE_DIR / "results" / "cleaned_data.csv")
num_cols = ['PM2.5', 'PM10', 'SO2', 'NO2', 'CO', 'O3', 'TEMP', 'PRES', 'DEWP', 'RAIN', 'WSPM']

normality_results = []

for col in num_cols:
    stat, p = normaltest(df[col])
    skew_val = skew(df[col])
    normality_results.append({"name":col, "stats":stat, "p_val":p, "skewness":skew_val, "is_normal":p >= 0.05})


normality_df = pd.DataFrame(normality_results)
normality_df.to_csv(output_dir / "normality_tests.csv", index=False)

correlation_sprm_df = df[num_cols].corr(method="spearman")
correlation_prsn_df = df[num_cols].corr(method="pearson")

correlation_sprm_df.to_csv(output_dir / "correlation_spearman.csv")
correlation_prsn_df.to_csv(output_dir / "correlation_pearson.csv")

plt.figure(figsize=(10, 8))
sns.heatmap(correlation_sprm_df, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1)
plt.title("Spearman Correlation MAtrix")
plt.savefig(output_dir / "graphs" / "correlation_heatmap.png", dpi=300, bbox_inches="tight")
plt.close()