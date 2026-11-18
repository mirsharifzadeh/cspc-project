from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

def filling(s):
    return s.interpolate(method='linear').bfill().ffill()

def fillstr(s):
    return s.ffill().bfill()

input_data = sorted((BASE_DIR / "data").glob("PRSA_Data_*.csv"))

output_dir = BASE_DIR / "results"
output_dir.mkdir(parents=True, exist_ok=True)

input_df = []

for i in input_data:
    input_df.append(pd.read_csv(i))

main_df = pd.concat(input_df, ignore_index=True)
main_df = main_df.drop(columns=['No'])

main_df['datetime'] = pd.to_datetime(main_df[['year', 'month', 'day', 'hour']])
main_df = main_df.sort_values(['station', 'datetime'], ignore_index=True)

num_cols = ['PM2.5', 'PM10', 'SO2', 'NO2', 'CO', 'O3', 'TEMP', 'PRES', 'DEWP', 'RAIN', 'WSPM']

main_df[num_cols] = main_df.groupby('station')[num_cols].transform(filling)
main_df['wd'] = main_df.groupby('station')['wd'].transform(fillstr)

assert main_df.isna().sum().sum() == 0

main_df.to_csv(output_dir / "cleaned_data.csv", index=False)

