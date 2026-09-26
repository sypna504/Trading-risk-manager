# Data contracts

- Market prediction timestamps must reference closed information only.
- News research uses only records whose publication/receipt/known/edit boundaries are <= prediction time.
- Geopolitical features require `known_at <= prediction_time`; scheduled event content is not visible before its statement publication.
- Paper entry uses next-bar open semantics and is separate from model outcome evaluation.
- `trade_allowed` remains the Quant Core result because MVP-6 news improvement is not proven on real OOS data.
