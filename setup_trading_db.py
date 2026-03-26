"""
Setup trading database with historical market data
Supports Forex, Commodities, and Crypto
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def create_trading_database():
    """Create a comprehensive trading database"""
    
    conn = sqlite3.connect('trading_data.db')
    cursor = conn.cursor()
    
    # Create markets table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS markets (
        symbol TEXT PRIMARY KEY,
        name TEXT,
        type TEXT,
        currency TEXT,
        min_lot REAL,
        max_lot REAL,
        spread REAL,
        is_active BOOLEAN
    )
    ''')
    
    # Create price data table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS price_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        timestamp DATETIME,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume REAL,
        timeframe TEXT,
        FOREIGN KEY (symbol) REFERENCES markets(symbol)
    )
    ''')
    
    # Create indicators table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS indicators (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        timestamp DATETIME,
        rsi REAL,
        macd REAL,
        macd_signal REAL,
        macd_histogram REAL,
        sma_20 REAL,
        sma_50 REAL,
        ema_12 REAL,
        ema_26 REAL,
        bollinger_upper REAL,
        bollinger_lower REAL,
        volume_sma REAL,
        atr REAL,
        FOREIGN KEY (symbol) REFERENCES markets(symbol)
    )
    ''')
    
    # Create predictions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        timestamp DATETIME,
        predicted_direction TEXT,
        confidence REAL,
        target_price REAL,
        stop_loss REAL,
        timeframe TEXT,
        model_used TEXT,
        actual_outcome TEXT,
        FOREIGN KEY (symbol) REFERENCES markets(symbol)
    )
    ''')
    
    # Insert markets
    markets = [
        # Forex
        ('EUR/USD', 'Euro US Dollar', 'Forex', 'USD', 0.01, 100, 0.0001, True),
        ('GBP/USD', 'British Pound US Dollar', 'Forex', 'USD', 0.01, 100, 0.0001, True),
        ('USD/JPY', 'US Dollar Japanese Yen', 'Forex', 'JPY', 0.01, 100, 0.01, True),
        ('AUD/USD', 'Australian Dollar US Dollar', 'Forex', 'USD', 0.01, 100, 0.0001, True),
        ('USD/CAD', 'US Dollar Canadian Dollar', 'Forex', 'CAD', 0.01, 100, 0.0001, True),
        
        # Commodities
        ('XAU/USD', 'Gold', 'Commodity', 'USD', 0.01, 100, 0.5, True),
        ('XAG/USD', 'Silver', 'Commodity', 'USD', 0.01, 100, 0.05, True),
        ('USOIL', 'WTI Crude Oil', 'Commodity', 'USD', 0.1, 1000, 0.05, True),
        ('UKOIL', 'Brent Crude Oil', 'Commodity', 'USD', 0.1, 1000, 0.05, True),
        ('COPPER', 'Copper', 'Commodity', 'USD', 1, 1000, 0.01, True),
        
        # Crypto
        ('BTC/USD', 'Bitcoin', 'Crypto', 'USD', 0.001, 10, 10, True),
        ('ETH/USD', 'Ethereum', 'Crypto', 'USD', 0.01, 100, 5, True),
        ('BNB/USD', 'Binance Coin', 'Crypto', 'USD', 0.1, 1000, 1, True),
        ('SOL/USD', 'Solana', 'Crypto', 'USD', 0.1, 1000, 0.5, True),
        ('ADA/USD', 'Cardano', 'Crypto', 'USD', 1, 10000, 0.001, True),
    ]
    
    cursor.executemany('INSERT OR REPLACE INTO markets VALUES (?,?,?,?,?,?,?,?)', markets)
    
    # Generate synthetic historical price data
    print("Generating historical price data...")
    
    symbols = [m[0] for m in markets]
    timeframes = ['1h', '4h', '1d']
    
    # Base volatility for different asset types
    volatility = {
        'Forex': 0.005,      # 0.5% daily volatility
        'Commodity': 0.015,   # 1.5% daily volatility
        'Crypto': 0.05        # 5% daily volatility
    }
    
    for symbol in symbols:
        # Determine asset type
        cursor.execute("SELECT type FROM markets WHERE symbol = ?", (symbol,))
        asset_type = cursor.fetchone()[0]
        base_vol = volatility.get(asset_type, 0.02)
        
        for timeframe in timeframes:
            # Number of candles based on timeframe
            if timeframe == '1h':
                n_candles = 1000  # ~41 days
                minutes = 60
            elif timeframe == '4h':
                n_candles = 500   # ~83 days
                minutes = 240
            else:  # 1d
                n_candles = 365   # 1 year
                minutes = 1440
            
            # Generate price data with trend and randomness
            current_price = 100.0 if asset_type != 'Crypto' else 50000.0
            if symbol == 'EUR/USD':
                current_price = 1.10
            elif symbol == 'GBP/USD':
                current_price = 1.30
            elif symbol == 'USD/JPY':
                current_price = 150.0
            elif symbol == 'XAU/USD':
                current_price = 2000.0
            elif symbol == 'BTC/USD':
                current_price = 50000.0
            
            prices = []
            current_time = datetime.now() - timedelta(days=n_candles)
            
            for i in range(n_candles):
                # Add trend and random walk
                trend = np.sin(i / 200) * 0.02  # Cyclical trend
                noise = np.random.normal(0, base_vol / np.sqrt(24*60/minutes))
                
                change = trend + noise
                current_price *= (1 + change)
                
                # Generate OHLC
                open_price = current_price
                high_price = open_price * (1 + abs(np.random.normal(0, base_vol/2)))
                low_price = open_price * (1 - abs(np.random.normal(0, base_vol/2)))
                close_price = open_price * (1 + np.random.normal(0, base_vol))
                volume = np.random.uniform(1000, 100000)
                
                prices.append((
                    symbol,
                    current_time,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume,
                    timeframe
                ))
                
                current_time += timedelta(minutes=minutes)
            
            # Insert price data
            cursor.executemany('''
                INSERT INTO price_data 
                (symbol, timestamp, open, high, low, close, volume, timeframe)
                VALUES (?,?,?,?,?,?,?,?)
            ''', prices)
    
    conn.commit()
    
    print(f"✅ Trading database created!")
    print(f"   - {len(markets)} markets")
    print(f"   - {len(symbols) * len(timeframes) * 1000} price candles")
    
    # Show sample data
    print("\n📊 Sample data:")
    cursor.execute("""
        SELECT symbol, timestamp, open, high, low, close 
        FROM price_data 
        WHERE symbol = 'BTC/USD' AND timeframe = '1d'
        ORDER BY timestamp DESC LIMIT 5
    """)
    
    for row in cursor.fetchall():
        print(f"   {row[0]} - {row[1]}: Open ${row[2]:.2f}, Close ${row[4]:.2f}")
    
    conn.close()
    return True

def calculate_technical_indicators():
    """Calculate technical indicators for all price data"""
    
    conn = sqlite3.connect('trading_data.db')
    
    # Get all price data
    df = pd.read_sql_query("""
        SELECT * FROM price_data 
        ORDER BY symbol, timeframe, timestamp
    """, conn)
    
    for symbol in df['symbol'].unique():
        for timeframe in df['timeframe'].unique():
            mask = (df['symbol'] == symbol) & (df['timeframe'] == timeframe)
            df_subset = df[mask].copy()
            
            if len(df_subset) < 50:
                continue
            
            # Calculate indicators
            df_subset['sma_20'] = df_subset['close'].rolling(20).mean()
            df_subset['sma_50'] = df_subset['close'].rolling(50).mean()
            df_subset['ema_12'] = df_subset['close'].ewm(span=12).mean()
            df_subset['ema_26'] = df_subset['close'].ewm(span=26).mean()
            
            # RSI
            delta = df_subset['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df_subset['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            df_subset['macd'] = df_subset['ema_12'] - df_subset['ema_26']
            df_subset['macd_signal'] = df_subset['macd'].ewm(span=9).mean()
            df_subset['macd_histogram'] = df_subset['macd'] - df_subset['macd_signal']
            
            # Bollinger Bands
            df_subset['bb_middle'] = df_subset['close'].rolling(20).mean()
            bb_std = df_subset['close'].rolling(20).std()
            df_subset['bollinger_upper'] = df_subset['bb_middle'] + (bb_std * 2)
            df_subset['bollinger_lower'] = df_subset['bb_middle'] - (bb_std * 2)
            
            # ATR
            high_low = df_subset['high'] - df_subset['low']
            high_close = abs(df_subset['high'] - df_subset['close'].shift())
            low_close = abs(df_subset['low'] - df_subset['close'].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df_subset['atr'] = tr.rolling(14).mean()
            
            # Volume SMA
            df_subset['volume_sma'] = df_subset['volume'].rolling(20).mean()
            
            # Insert indicators
            cursor = conn.cursor()
            for idx, row in df_subset.iterrows():
                if pd.notna(row['rsi']):
                    cursor.execute('''
                        INSERT OR REPLACE INTO indicators
                        (symbol, timestamp, rsi, macd, macd_signal, macd_histogram,
                         sma_20, sma_50, ema_12, ema_26, bollinger_upper, bollinger_lower,
                         volume_sma, atr)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ''', (
                        row['symbol'], row['timestamp'], row['rsi'], row['macd'],
                        row['macd_signal'], row['macd_histogram'], row['sma_20'],
                        row['sma_50'], row['ema_12'], row['ema_26'], row['bollinger_upper'],
                        row['bollinger_lower'], row['volume_sma'], row['atr']
                    ))
            
            conn.commit()
    
    conn.close()
    print("✅ Technical indicators calculated")

if __name__ == "__main__":
    create_trading_database()
    calculate_technical_indicators()