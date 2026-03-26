"""
DeepSeek Trading Bot Dashboard
Interactive trading assistant with live predictions
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from trading_bot import TradingBot
from datetime import datetime, timedelta
import time

# Page config
st.set_page_config(
    page_title="DeepSeek Trading Bot",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 1rem;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    .signal-buy {
        background: linear-gradient(135deg, #00c853 0%, #00e676 100%);
        padding: 0.5rem;
        border-radius: 0.5rem;
        text-align: center;
        font-weight: bold;
        color: white;
    }
    .signal-sell {
        background: linear-gradient(135deg, #d50000 0%, #ff1744 100%);
        padding: 0.5rem;
        border-radius: 0.5rem;
        text-align: center;
        font-weight: bold;
        color: white;
    }
    .signal-neutral {
        background: linear-gradient(135deg, #757575 0%, #9e9e9e 100%);
        padding: 0.5rem;
        border-radius: 0.5rem;
        text-align: center;
        font-weight: bold;
        color: white;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .risk-high {
        color: #ff1744;
        font-weight: bold;
    }
    .risk-medium {
        color: #ff9100;
        font-weight: bold;
    }
    .risk-low {
        color: #00c853;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize bot
@st.cache_resource
def init_bot():
    return TradingBot()

bot = init_bot()

# Sidebar
with st.sidebar:
    st.markdown("### 🤖 DeepSeek Trading Bot")
    st.markdown("---")
    
    # Market selection
    market_type = st.selectbox(
        "Market Type",
        ["All", "Forex", "Commodities", "Crypto"]
    )
    
    # Get symbols based on selection
    if market_type == "All":
        symbols = []
        for symbols_list in bot.market_types.values():
            symbols.extend(symbols_list)
    else:
        symbols = bot.market_types.get(market_type, [])
    
    selected_symbol = st.selectbox("Symbol", symbols)
    
    # Timeframe
    timeframe = st.selectbox(
        "Timeframe",
        ["1h", "4h", "1d"],
        help="1h = 1 hour, 4h = 4 hours, 1d = daily"
    )
    
    st.markdown("---")
    
    # Risk settings
    st.markdown("### ⚙️ Risk Management")
    risk_percent = st.slider(
        "Risk per trade (%)",
        min_value=0.5,
        max_value=5.0,
        value=2.0,
        step=0.5
    )
    
    account_balance = st.number_input(
        "Account Balance ($)",
        value=10000,
        step=1000
    )
    
    st.markdown("---")
    
    # Auto-refresh
    auto_refresh = st.checkbox("Auto-refresh (30s)")
    
    st.markdown("---")
    
    # Info
    st.info("""
    **How it works:**
    1. Technical analysis (RSI, MACD, MAs)
    2. AI prediction with DeepSeek
    3. Combined recommendation
    4. Risk assessment
    """)

# Main content
st.markdown('<div class="main-header">', unsafe_allow_html=True)
st.title("📈 DeepSeek AI Trading Assistant")
st.markdown("AI-powered predictions for Forex, Commodities, and Crypto")
st.markdown('</div>', unsafe_allow_html=True)

# Auto-refresh logic
if auto_refresh:
    placeholder = st.empty()
    time.sleep(30)
    st.rerun()

# Get analysis
with st.spinner(f"Analyzing {selected_symbol} with DeepSeek..."):
    analysis = bot.analyze_market(selected_symbol, timeframe)

if "error" in analysis:
    st.error(analysis["error"])
else:
    # Current price section
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Current Price",
            f"${analysis['current_price']['price']:.2f}",
            f"{analysis['current_price']['change_24h']:.2f}%"
        )
    
    with col2:
        st.metric("24h High", f"${analysis['current_price']['high_24h']:.2f}")
        st.metric("24h Low", f"${analysis['current_price']['low_24h']:.2f}")
    
    with col3:
        st.metric("Volume", f"{analysis['current_price']['volume']:.0f}")
        st.metric("RSI", f"{analysis['current_price'].get('rsi', 50):.1f}")
    
    with col4:
        risk_class = f"risk-{analysis['risk_metrics']['risk_level'].lower().replace(' ', '-')}"
        st.markdown(f"**Risk Level**")
        st.markdown(f'<div class="{risk_class}">{analysis["risk_metrics"]["risk_level"]}</div>', 
                   unsafe_allow_html=True)
        st.metric("Volatility", f"{analysis['risk_metrics']['volatility_24h']:.1f}%")
    
    # Signal section
    st.markdown("### 🎯 Trading Signal")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        signal_class = f"signal-{analysis['technical_analysis']['signal'].lower()}"
        st.markdown(f'<div class="{signal_class}">Technical: {analysis["technical_analysis"]["signal"]}</div>', 
                   unsafe_allow_html=True)
        st.markdown(f"Confidence: {analysis['technical_analysis']['confidence']:.0f}%")
    
    with col2:
        ai_direction = analysis['ai_prediction'].get('direction', 'NEUTRAL').lower()
        signal_class = f"signal-{ai_direction}"
        st.markdown(f'<div class="{signal_class}">AI: {analysis["ai_prediction"].get("direction", "NEUTRAL")}</div>', 
                   unsafe_allow_html=True)
        st.markdown(f"Confidence: {analysis['ai_prediction'].get('confidence', 50):.0f}%")
    
    with col3:
        rec = analysis['recommendation']['action'].lower().replace(' ', '-')
        signal_class = f"signal-{rec}"
        st.markdown(f'<div class="{signal_class}">RECOMMENDATION: {analysis["recommendation"]["action"]}</div>', 
                   unsafe_allow_html=True)
        st.markdown(f"Conviction: {analysis['recommendation']['conviction']}")
        st.markdown(f"Combined Confidence: {analysis['recommendation']['confidence']:.0f}%")
    
    # Technical reasons
    with st.expander("🔍 Technical Analysis Details"):
        st.markdown("**Key Signals:**")
        for reason in analysis['technical_analysis']['reasons']:
            st.markdown(f"• {reason}")
        
        st.markdown("\n**AI Analysis:**")
        for factor in analysis['ai_prediction'].get('factors', []):
            st.markdown(f"• {factor}")
        
        if 'explanation' in analysis['ai_prediction']:
            st.markdown(f"\n**AI Explanation:** {analysis['ai_prediction']['explanation']}")
    
    # Price chart
    st.markdown("### 📊 Price Chart with Indicators")
    
    df = bot.get_market_data(selected_symbol, timeframe, 100)
    
    if not df.empty:
        fig = make_subplots(rows=3, cols=1, 
                           shared_xaxes=True,
                           vertical_spacing=0.05,
                           row_heights=[0.6, 0.2, 0.2])
        
        # Candlestick chart
        fig.add_trace(go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Price'
        ), row=1, col=1)
        
        # Add moving averages
        fig.add_trace(go.Scatter(
            x=df['timestamp'], y=df['sma_20'],
            name='SMA 20', line=dict(color='orange', width=1)
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(
            x=df['timestamp'], y=df['sma_50'],
            name='SMA 50', line=dict(color='blue', width=1)
        ), row=1, col=1)
        
        # RSI
        fig.add_trace(go.Scatter(
            x=df['timestamp'], y=df['rsi'],
            name='RSI', line=dict(color='purple', width=1)
        ), row=2, col=1)
        
        # Add RSI levels
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        
        # Volume
        colors = ['red' if row['open'] > row['close'] else 'green' for _, row in df.iterrows()]
        fig.add_trace(go.Bar(
            x=df['timestamp'], y=df['volume'],
            name='Volume', marker_color=colors
        ), row=3, col=1)
        
        fig.update_layout(
            title=f"{selected_symbol} - {timeframe.upper()} Chart",
            yaxis_title="Price",
            xaxis_title="Date",
            template="plotly_white",
            height=800
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Trade simulator
    st.markdown("### 💰 Trade Simulator")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        action = st.selectbox(
            "Action",
            ["BUY", "SELL"],
            help="Based on recommendation"
        )
    
    with col2:
        entry_price = st.number_input(
            "Entry Price",
            value=float(analysis['current_price']['price']),
            step=0.01
        )
    
    with col3:
        risk_reward = st.slider(
            "Risk:Reward Ratio",
            min_value=0.5,
            max_value=5.0,
            value=2.0,
            step=0.5
        )
    
    # Calculate stop loss and take profit
    if action == "BUY":
        stop_loss = entry_price - (entry_price * (risk_percent / 100))
        take_profit = entry_price + ((entry_price - stop_loss) * risk_reward)
    else:
        stop_loss = entry_price + (entry_price * (risk_percent / 100))
        take_profit = entry_price - ((stop_loss - entry_price) * risk_reward)
    
    # Simulate trade
    simulation = bot.simulate_trade(
        selected_symbol, action, entry_price,
        stop_loss, take_profit, risk_percent
    )
    
    if "error" not in simulation:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Position Size", f"{simulation['position_size']:.4f} units")
            st.metric("Risk Amount", f"${simulation['risk_amount']:.2f}")
        
        with col2:
            st.metric("Stop Loss", f"${simulation['stop_loss']:.2f}")
            st.metric("Take Profit", f"${simulation['take_profit']:.2f}")
        
        with col3:
            st.metric("Potential Loss", f"${simulation['potential_loss']:.2f}")
            st.metric("Potential Profit", f"${simulation['potential_profit']:.2f}")
        
        with col4:
            st.metric("Risk:Reward", f"1:{simulation['risk_reward_ratio']:.1f}")
            rec_class = "🟢" if simulation['recommendation'] == "GOOD" else "🟡" if simulation['recommendation'] == "MODERATE" else "🔴"
            st.metric("Setup Quality", f"{rec_class} {simulation['recommendation']}")
    
    # Top opportunities
    st.markdown("### 🏆 Top Trading Opportunities")
    
    opportunities = bot.get_top_opportunities()
    
    if opportunities:
        opp_df = pd.DataFrame(opportunities)
        opp_df['confidence'] = opp_df['confidence'].round(0)
        
        # Color coding
        def color_recommendation(val):
            if 'BUY' in val:
                return 'background-color: #00c85320'
            elif 'SELL' in val:
                return 'background-color: #ff174420'
            return ''
        
        st.dataframe(
            opp_df.style.applymap(color_recommendation, subset=['recommendation']),
            use_container_width=True
        )

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>⚠️ <strong>Risk Warning:</strong> Trading involves substantial risk of loss. This AI assistant is for educational purposes only.</p>
    <p>🤖 Powered by DeepSeek-R1:1.5B | 📊 Technical Analysis + AI Predictions | 🔒 100% Local</p>
</div>
""", unsafe_allow_html=True)