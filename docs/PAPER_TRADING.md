# Paper trading

Virtual positions are opened only from an already allowed decision. Entry uses the next available bar open plus simulated adverse slippage. Exit supports stop-loss, take-profit and timeout. If SL and TP are both touched in one OHLC bar, the configured conservative default is stop-loss. Fees and slippage are applied. Real orders are not implemented.
