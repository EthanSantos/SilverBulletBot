from AlgorithmImports import *

class SilverBulletFuturesAlgorithm(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2022, 12, 1)
        self.SetEndDate(2023, 1, 15)    
        self.SetCash(100000)            
        
        # Add futures for S&P 500 (ES) and NASDAQ (NQ) with minute resolution
        self.es = self.AddFuture(Futures.Indices.SP500EMini, Resolution.Minute)
        self.nq = self.AddFuture(Futures.Indices.NASDAQ100EMini, Resolution.Minute)
        
        # Set filter for the futures contracts
        self.es.SetFilter(lambda x: x.Expiration(TimeSpan.FromDays(0), TimeSpan.FromDays(90)))
        self.nq.SetFilter(lambda x: x.Expiration(TimeSpan.FromDays(0), TimeSpan.FromDays(90)))
        
        self.current_contracts = {}
        self.indicators = {}
        self.in_session = False

        # Schedule function to run during PST trading hours
        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.At(14, 30), self.TradingSessionStart)  # 6:30am PST
        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.At(16, 0), self.TradingSessionEnd)    # 8:00am PST
        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.At(18, 30), self.TradingSessionStart)  # 10:30am PST
        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.At(20, 0), self.TradingSessionEnd)    # 12:00pm PST

    def TradingSessionStart(self):
        self.in_session = True
        self.Debug(f"Trading session started at {self.Time}")

    def TradingSessionEnd(self):
        self.in_session = False
        self.Debug(f"Trading session ended at {self.Time}")

    def OnData(self, data):
        if not self.in_session:
            return

        for chain in data.FutureChains.Values:
            contracts = sorted(chain, key=lambda x: x.Expiry)
            if len(contracts) == 0:
                continue

            front_contract = contracts[0]
            symbol = front_contract.Symbol

            if symbol not in self.indicators:
                self.indicators[symbol] = {
                    'sma': self.SMA(symbol, 14, Resolution.Minute),
                    'rsi': self.RSI(symbol, 14, MovingAverageType.Wilders, Resolution.Minute)
                }

            indicators = self.indicators[symbol]
            price = front_contract.LastPrice

            if not indicators['sma'].IsReady or not indicators['rsi'].IsReady:
                self.Debug(f"Indicators not ready for {symbol} at {self.Time}")
                continue

            self.Debug(f"Price: {price}, SMA: {indicators['sma'].Current.Value}, RSI: {indicators['rsi'].Current.Value} at {self.Time}")

            if self.IsSilverBulletSetup(symbol, indicators):
                if indicators['sma'].Current.Value < price and indicators['rsi'].Current.Value > 70:
                    self.LimitOrder(symbol, -1, price) 
                    self.Debug(f"Entering short position for {symbol} at {price}")
                elif indicators['sma'].Current.Value > price and indicators['rsi'].Current.Value < 30:
                    self.LimitOrder(symbol, 1, price) 
                    self.Debug(f"Entering long position for {symbol} at {price}")

    def IsSilverBulletSetup(self, symbol, indicators):
        return indicators['sma'].IsReady and indicators['rsi'].IsReady

    def OnOrderEvent(self, orderEvent):
        if orderEvent.Status == OrderStatus.Filled:
            self.Debug(f"Order filled at {orderEvent.FillPrice} for {orderEvent.Symbol}")

