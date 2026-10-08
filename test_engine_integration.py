import pandas as pd
import numpy as np
import config
from price_action_engine import PriceActionEngine

# Test with a mock dataframe
dates = pd.date_range("2026-01-01", periods=50, freq="B")
prices = [100.0 + i * 0.5 for i in range(50)]
df = pd.DataFrame({
    "Open": prices,
    "High": [p + 0.5 for p in prices],
    "Low": [p - 0.5 for p in prices],
    "Close": [p + 0.2 for p in prices],
    "Volume": [1000000] * 50
}, index=dates)

res = PriceActionEngine.analyze_setups(df)
print("Columns in result:", res.columns.tolist())
print("Result shape:", res.shape)
