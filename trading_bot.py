"""
DeepSeek Trading Prediction Bot
Forex, Commodities, and Crypto Trading Assistant
"""

import sqlite3
import pandas as pd
import numpy as np
import ollama
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import warnings
warnings.filterwarnings('ignore')

class TradingBot:
    """AI-powered trading prediction bot"""
    
    def __init__(self, db_path: str = "trading_data.db", model: str = "deepseek-r1:1.5b"):
        self.db_path = db_path
        self.model = model
        self.temperature = 0.3  # Lower for more consistent predictions
        
        # Market categories
        self.market_types = {
            'Forex': ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CAD'],
            'Commodities': ['XAU/USD', 'XAG/USD', 'USOIL', 'UKOIL', 'COPPER'],
            'Crypto': ['BTC/USD', 'ETH/USD', 'BNB/USD', 'SOL/USD', 'ADA/USD']
        }
        
        print(f"🤖 Trading Bot initialized with {model}")
        
    def _get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def get_market_data(self, symbol: str, timeframe: str = '1d', days: int = 100) -> pd.DataFrame:
        """Get historical market data with indicators"""
        conn = self._get_connection()
        
        query = f"""
        SELECT 
            p.*,
            i.rsi, i.macd, i.macd_signal, i.macd_histogram,
            i.sma_20, i.sma_50, i.ema_12, i.ema_26,
            i.bollinger_upper, i.bollinger_lower,
            i.volume_sma, i.atr
        FROM price_data p
        LEFT JOIN indicators i ON p.symbol = i.symbol AND p.timestamp = i.timestamp
        WHERE p.symbol = ? AND p.timeframe = ?
        ORDER BY p.timestamp DESC
        LIMIT ?
        """
        
        df = pd.read_sql_query(query, conn, params=(symbol, timeframe, days))
        conn.close()
        
        return df
    
    def get_current_price(self, symbol: str) -> Dict[str, Any]:
        """Get current price and market conditions"""
        df = self.get_market_data(symbol, '1h', 24)
        
        if df.empty:
            return {"error": "No data available"}
        
        latest = df.iloc[0]
        
        return {
            "symbol": symbol,
            "price": latest['close'],
            "change_24h": ((latest['close'] - df.iloc[-1]['close']) / df.iloc[-1]['close']) * 100,
            "high_24h": df['high'].max(),
            "low_24h": df['low'].min(),
            "volume": latest['volume'],
            "rsi": latest.get('rsi', 50),
            "macd": latest.get('macd', 0),
            "atr": latest.get('atr', 0),
            "timestamp": latest['timestamp']
        }
    
    def calculate_technical_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate technical analysis signals"""
        if df.empty or len(df) < 50:
            return {"signal": "neutral", "confidence": 0, "reasons": []}
        
        latest = df.iloc[0]
        prev = df.iloc[1] if len(df) > 1 else latest
        
        signals = []
        reasons = []
        
        # RSI signal
        rsi = latest.get('rsi', 50)
        if rsi < 30:
            signals.append(1)  # Oversold - Buy signal
            reasons.append(f"RSI oversold at {rsi:.1f}")
        elif rsi > 70:
            signals.append(-1)  # Overbought - Sell signal
            reasons.append(f"RSI overbought at {rsi:.1f}")
        else:
            signals.append(0)
        
        # MACD signal
        macd = latest.get('macd', 0)
        macd_signal = latest.get('macd_signal', 0)
        if macd > macd_signal:
            signals.append(1)  # Bullish
            reasons.append("MACD above signal line (bullish)")
        else:
            signals.append(-1)  # Bearish
            reasons.append("MACD below signal line (bearish)")
        
        # Moving average crossover
        sma_20 = latest.get('sma_20', latest['close'])
        sma_50 = latest.get('sma_50', latest['close'])
        if sma_20 > sma_50:
            signals.append(1)
            reasons.append("20 SMA above 50 SMA (bullish)")
        else:
            signals.append(-1)
            reasons.append("20 SMA below 50 SMA (bearish)")
        
        # Bollinger Bands
        bb_upper = latest.get('bollinger_upper', latest['close'] * 1.05)
        bb_lower = latest.get('bollinger_lower', latest['close'] * 0.95)
        price = latest['close']
        
        if price <= bb_lower:
            signals.append(1)
            reasons.append("Price near lower Bollinger Band (oversold)")
        elif price >= bb_upper:
            signals.append(-1)
            reasons.append("Price near upper Bollinger Band (overbought)")
        else:
            signals.append(0)
        
        # Volume confirmation
        volume_sma = latest.get('volume_sma', latest['volume'])
        if latest['volume'] > volume_sma * 1.2:
            signals.append(1 if sum(signals) > 0 else -1)
            reasons.append("High volume confirms trend")
        else:
            signals.append(0)
        
        # Calculate overall signal
        total_signal = sum(signals)
        max_signal = 5
        confidence = abs(total_signal) / max_signal * 100
        
        if total_signal > 1:
            signal = "BUY"
        elif total_signal < -1:
            signal = "SELL"
        else:
            signal = "NEUTRAL"
        
        return {
            "signal": signal,
            "confidence": confidence,
            "reasons": reasons,
            "total_signal": total_signal
        }
    
    def predict_with_ai(self, symbol: str, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Use DeepSeek to predict market movement"""
        
        # Prepare data summary for AI
        latest = market_data.iloc[0]
        prev_day = market_data.iloc[1] if len(market_data) > 1 else latest
        
        # Get technical signal
        tech_signal = self.calculate_technical_signal(market_data)
        
        # Prepare context
        context = f"""
Market: {symbol}
Current Price: ${latest['close']:.2f}
24h Change: {((latest['close'] - market_data.iloc[-1]['close']) / market_data.iloc[-1]['close']) * 100:.2f}%
RSI: {latest.get('rsi', 'N/A'):.1f}
MACD: {latest.get('macd', 0):.4f}
Volume: {latest['volume']:.0f}
Technical Signal: {tech_signal['signal']} (Confidence: {tech_signal['confidence']:.0f}%)

Technical Reasons:
{chr(10).join(f"- {r}" for r in tech_signal['reasons'][:3])}

Based on this data, predict:
1. Expected price movement direction (UP/DOWN/SIDEWAYS)
2. Confidence level (0-100%)
3. Key factors influencing this prediction
4. Suggested entry price
5. Target price (next 24h)
6. Stop loss level
7. Risk assessment (LOW/MEDIUM/HIGH)
8. Brief explanation

Format as JSON with keys: direction, confidence, factors, entry, target, stop_loss, risk, explanation
"""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": context}],
                options={"temperature": 0.3, "num_predict": 500}
            )
            
            # Parse AI response
            ai_text = response['message']['content']
            
            # Try to extract JSON
            try:
                import re
                json_match = re.search(r'\{.*\}', ai_text, re.DOTALL)
                if json_match:
                    ai_prediction = json.loads(json_match.group())
                else:
                    # Fallback
                    ai_prediction = {
                        "direction": "NEUTRAL",
                        "confidence": 50,
                        "factors": ["AI analysis in progress"],
                        "risk": "MEDIUM"
                    }
            except:
                # Simple parsing
                ai_prediction = {
                    "direction": "UP" if "UP" in ai_text.upper() else "DOWN" if "DOWN" in ai_text.upper() else "SIDEWAYS",
                    "confidence": 60,
                    "factors": [ai_text[:100]],
                    "risk": "MEDIUM"
                }
            
            return ai_prediction
            
        except Exception as e:
            return {
                "direction": tech_signal['signal'] if tech_signal['signal'] != "NEUTRAL" else "SIDEWAYS",
                "confidence": tech_signal['confidence'],
                "factors": tech_signal['reasons'],
                "risk": "MEDIUM",
                "error": str(e)
            }
    
    def analyze_market(self, symbol: str, timeframe: str = '1d') -> Dict[str, Any]:
        """Complete market analysis"""
        
        # Get market data
        df = self.get_market_data(symbol, timeframe, 100)
        
        if df.empty:
            return {"error": f"No data for {symbol}"}
        
        # Current price info
        current = self.get_current_price(symbol)
        
        # Technical analysis
        technical = self.calculate_technical_signal(df)
        
        # AI prediction
        ai_prediction = self.predict_with_ai(symbol, df)
        
        # Combine analysis
        analysis = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "current_price": current,
            "technical_analysis": technical,
            "ai_prediction": ai_prediction,
            "recommendation": self._generate_recommendation(technical, ai_prediction),
            "risk_metrics": self._calculate_risk_metrics(df)
        }
        
        return analysis
    
    def _generate_recommendation(self, technical: Dict, ai_prediction: Dict) -> Dict:
        """Generate trading recommendation"""
        
        # Combine signals
        tech_score = 1 if technical['signal'] == 'BUY' else -1 if technical['signal'] == 'SELL' else 0
        ai_score = 1 if ai_prediction.get('direction', '').upper() == 'UP' else -1 if ai_prediction.get('direction', '').upper() == 'DOWN' else 0
        
        total_score = tech_score + ai_score
        confidence = (technical['confidence'] + ai_prediction.get('confidence', 50)) / 2
        
        if total_score >= 1 and confidence > 60:
            action = "STRONG BUY"
            conviction = "HIGH"
        elif total_score >= 1:
            action = "BUY"
            conviction = "MEDIUM"
        elif total_score <= -1 and confidence > 60:
            action = "STRONG SELL"
            conviction = "HIGH"
        elif total_score <= -1:
            action = "SELL"
            conviction = "MEDIUM"
        else:
            action = "HOLD"
            conviction = "LOW"
        
        return {
            "action": action,
            "conviction": conviction,
            "confidence": confidence,
            "tech_signal": technical['signal'],
            "ai_direction": ai_prediction.get('direction', 'NEUTRAL'),
            "reasoning": f"Technical: {technical['signal']} ({technical['confidence']:.0f}%), AI: {ai_prediction.get('direction', 'NEUTRAL')} ({ai_prediction.get('confidence', 50):.0f}%)"
        }
    
    def _calculate_risk_metrics(self, df: pd.DataFrame) -> Dict:
        """Calculate risk metrics"""
        
        if len(df) < 20:
            return {"risk_level": "UNKNOWN"}
        
        returns = df['close'].pct_change().dropna()
        
        # Volatility
        volatility = returns.std() * np.sqrt(252) * 100
        
        # Maximum drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min() * 100
        
        # Sharpe ratio (simplified)
        sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        
        # Risk level
        if volatility > 50:
            risk_level = "VERY HIGH"
        elif volatility > 30:
            risk_level = "HIGH"
        elif volatility > 15:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return {
            "risk_level": risk_level,
            "volatility_annual": volatility,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe,
            "volatility_24h": returns.std() * 100
        }
    
    def get_top_opportunities(self) -> List[Dict]:
        """Find top trading opportunities across all markets"""
        
        opportunities = []
        
        for market_type, symbols in self.market_types.items():
            for symbol in symbols:
                try:
                    analysis = self.analyze_market(symbol, '1d')
                    if 'error' not in analysis:
                        opportunities.append({
                            "symbol": symbol,
                            "type": market_type,
                            "recommendation": analysis['recommendation']['action'],
                            "confidence": analysis['recommendation']['confidence'],
                            "current_price": analysis['current_price']['price'],
                            "risk": analysis['risk_metrics']['risk_level']
                        })
                except Exception as e:
                    continue
        
        # Sort by confidence
        opportunities.sort(key=lambda x: x['confidence'], reverse=True)
        
        return opportunities[:10]
    
    def simulate_trade(self, symbol: str, action: str, entry_price: float, 
                      stop_loss: float, take_profit: float, risk_percent: float = 2.0) -> Dict:
        """Simulate a trade with risk management"""
        
        current = self.get_current_price(symbol)
        
        # Calculate position size
        account_balance = 10000  # Assume $10,000 account
        risk_amount = account_balance * (risk_percent / 100)
        
        if action.upper() in ['BUY', 'STRONG BUY']:
            risk_per_unit = entry_price - stop_loss
            if risk_per_unit <= 0:
                return {"error": "Invalid stop loss"}
            
            position_size = risk_amount / risk_per_unit
            potential_profit = (take_profit - entry_price) * position_size
            potential_loss = (entry_price - stop_loss) * position_size
            
        else:  # SELL
            risk_per_unit = stop_loss - entry_price
            if risk_per_unit <= 0:
                return {"error": "Invalid stop loss"}
            
            position_size = risk_amount / risk_per_unit
            potential_profit = (entry_price - take_profit) * position_size
            potential_loss = (stop_loss - entry_price) * position_size
        
        # Risk-reward ratio
        risk_reward = potential_profit / potential_loss if potential_loss > 0 else 0
        
        return {
            "symbol": symbol,
            "action": action,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "position_size": position_size,
            "risk_amount": risk_amount,
            "potential_profit": potential_profit,
            "potential_loss": potential_loss,
            "risk_reward_ratio": risk_reward,
            "recommendation": "GOOD" if risk_reward >= 2 else "MODERATE" if risk_reward >= 1 else "POOR"
        }

# Quick test
if __name__ == "__main__":
    bot = TradingBot()
    
    print("🤖 Trading Bot Test\n")
    
    # Test single symbol
    print("Analyzing Bitcoin...")
    analysis = bot.analyze_market("BTC/USD")
    
    print(f"\n📊 Analysis for {analysis['symbol']}:")
    print(f"Current Price: ${analysis['current_price']['price']:.2f}")
    print(f"24h Change: {analysis['current_price']['change_24h']:.2f}%")
    print(f"\nTechnical Signal: {analysis['technical_analysis']['signal']}")
    print(f"Confidence: {analysis['technical_analysis']['confidence']:.0f}%")
    print(f"Reasons:")
    for reason in analysis['technical_analysis']['reasons'][:3]:
        print(f"  • {reason}")
    
    print(f"\nAI Prediction: {analysis['ai_prediction'].get('direction', 'N/A')}")
    print(f"AI Confidence: {analysis['ai_prediction'].get('confidence', 50):.0f}%")
    
    print(f"\n📈 Recommendation: {analysis['recommendation']['action']}")
    print(f"Conviction: {analysis['recommendation']['conviction']}")
    print(f"Combined Confidence: {analysis['recommendation']['confidence']:.0f}%")
    
    print(f"\n⚠️ Risk Assessment: {analysis['risk_metrics']['risk_level']}")
    print(f"Volatility (Annual): {analysis['risk_metrics']['volatility_annual']:.1f}%")
    
    print("\n🏆 Top Opportunities:")
    opportunities = bot.get_top_opportunities()
    for opp in opportunities[:5]:
        print(f"  {opp['symbol']}: {opp['recommendation']} (Confidence: {opp['confidence']:.0f}%)")