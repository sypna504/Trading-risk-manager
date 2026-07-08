def predict_signal_quality(features: dict) -> dict:
    p_win = 0.5
    if features["rsi_14"] < 30:
        p_win += 0.05

    if features["volume_zscore"] > 1:
        p_win += 0.03

    if features["volatility_24"] > 0.03:
        p_win -= 0.07
    
    if features["return_24"] < -0.03:
        p_win -= 0.03

    if features["trend_strength"] < 0.2:
        p_win -= 0.03

    p_win = max(0.01, min(0.99, p_win))
    if p_win >= 0.6:
        risk_level = "low"
    elif p_win >= 0.5:
        risk_level = "medium"
    else:
        risk_level = "high"
    return {
        "p_win": p_win,
        "expected_return_pct": (p_win - 0.5) * 2,
        "risk_level": risk_level,
        "model_version": "heuristic_baseline_v1",
    }