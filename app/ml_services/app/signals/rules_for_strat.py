import pandas as pd
import numpy as np

STRATAGIES = ['breakout', 'mean_reversion']

class Strategies:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def determine_strategy(self):
        df = self.df

        if df["close"] > df["high_20"] and df["volume_z_20"]>0.5:
            strat_name = "breakout"

        if df["rsi_14"]<35 and df["price_z_20"]<-1:
            strat_name = "mean_reversion"
    