import pandas as pd
def load(path):
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    ren = {"DateTime": "dt", "Temperature": "T", "Humidity": "H", "Wind Speed": "W",
           "general diffuse flows": "GDF", "diffuse flows": "DF",
           "Zone 1 Power Consumption": "Z1", "Zone 2  Power Consumption": "Z2",
           "Zone 3  Power Consumption": "Z3"}
    df = df.rename(columns=ren)
    df["dt"] = pd.to_datetime(df["dt"], format="%m/%d/%Y %H:%M")
    df["date"] = df.dt.dt.date
    return df
