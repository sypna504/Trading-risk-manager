import grpc

class Validator:
    def __init__(self, context, request, features=None):
        self.context = context
        self.request = request
        self.features = features or {}
    
    def validate_symbol(self):
        if not self.request.symbol:
            self.context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "symbol is required",
            )

    def validate_interval(self):
        if not self.request.interval:
            self.context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "interval is required",
            )

    def validate_strategy(self):
        if not self.request.strategy:
            self.context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "strategy is required",
            )
    
    def validate_rsi_14(self):
        if self.features["rsi_14"]<0 or self.features["rsi_14"]>100:
            self.context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "rsi 14 must be in interval (0,100)"
            )
        
    def validate_volatility_24(self):
        if self.features["volatility_24"]<0:
            self.context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "volatility 25 must be non negative"
            )

    def validate_trend_strength(self):
        if self.features["trend_strength"]<0:
            self.context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "trend strength must be non negative"
            )
    
    def validate_ma_distance(self):
        pass
    
    def validate_p_win(self):
        if self.features["p_win"]<0 or self.features["p_win"]>1:
            self.context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "ma distance must be non negative"
            )
    
