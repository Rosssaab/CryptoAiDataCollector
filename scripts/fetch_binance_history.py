from binance.client import Client
from datetime import datetime, timedelta
import sqlalchemy as sa
from sqlalchemy import text
import pandas as pd
import logging
import sys
import os
import time
import pyodbc
import urllib.parse

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONNECTION_STRING

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BinanceHistoryFetcher:
    def __init__(self):
        # Initialize Binance client (no API keys needed for public data)
        self.client = Client()
        
        # Convert ODBC connection string to SQLAlchemy format
        params = urllib.parse.quote_plus(DB_CONNECTION_STRING)
        engine_string = f"mssql+pyodbc:///?odbc_connect={params}"
        
        # Create database engine
        self.db_connection = sa.create_engine(
            engine_string,
            fast_executemany=True
        )
        
        # Parameters
        self.START_DATE = '2023-01-01'  # Fetch data from this date
        self.INTERVAL = Client.KLINE_INTERVAL_1DAY
        
    def get_coin_list(self):
        """Get list of coins from database"""
        try:
            query = "SELECT coin_id, symbol FROM Coins"  # Changed to match your table name
            with self.db_connection.connect() as conn:
                result = conn.execute(text(query))
                return [(row[0], row[1]) for row in result]
        except Exception as e:
            logger.error(f"Error fetching coin list: {str(e)}")
            return []

    def fetch_historical_data(self, symbol):
        """Fetch historical data from Binance"""
        try:
            # Add USDT suffix for Binance pair
            symbol_pair = f"{symbol}USDT"
            
            # Get klines (candlestick data)
            klines = self.client.get_historical_klines(
                symbol_pair,
                self.INTERVAL,
                self.START_DATE
            )
            
            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignored'
            ])
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Keep only needed columns and calculate additional metrics
            df = df[['timestamp', 'close', 'volume', 'quote_volume']]
            df.columns = ['timestamp', 'price_usd', 'volume_24h', 'quote_volume']
            
            # Convert to proper types
            df['price_usd'] = df['price_usd'].astype(float)
            df['volume_24h'] = df['volume_24h'].astype(float)
            
            # Calculate price change
            df['price_change_24h'] = df['price_usd'].pct_change() * 100
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return None

    def save_to_database(self, coin_id, symbol, data):
        """Save historical data to database"""
        try:
            # Prepare data for insertion
            records = []
            for _, row in data.iterrows():
                records.append({
                    'coin_id': coin_id,
                    'timestamp': row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    'price_usd': float(row['price_usd']),
                    'volume_24h': float(row['volume_24h']),
                    'price_change_24h': float(row['price_change_24h']) if pd.notnull(row['price_change_24h']) else 0,
                    'data_source': 'binance'
                })
            
            # Insert query for SQL Server
            query = """
            INSERT INTO Price_Data 
            (coin_id, timestamp, price_usd, volume_24h, price_change_24h, data_source)
            VALUES 
            (:coin_id, :timestamp, :price_usd, :volume_24h, :price_change_24h, :data_source)
            """
            
            # Execute in batches
            with self.db_connection.begin() as conn:
                for record in records:
                    conn.execute(text(query), record)
            
            logger.info(f"Saved {len(records)} records for {symbol}")
            
        except Exception as e:
            logger.error(f"Error saving data for {symbol}: {str(e)}")

    def run(self):
        """Main execution method"""
        logger.info("Starting historical data fetch from Binance")
        
        # Get list of coins
        coins = self.get_coin_list()
        logger.info(f"Found {len(coins)} coins to process")
        
        # Process each coin
        for coin_id, symbol in coins:
            logger.info(f"Processing {symbol}...")
            
            # Fetch data
            data = self.fetch_historical_data(symbol)
            if data is not None and not data.empty:
                # Save to database
                self.save_to_database(coin_id, symbol, data)
            
            # Small delay to avoid rate limits
            time.sleep(1)
        
        logger.info("Completed historical data fetch")

if __name__ == "__main__":
    fetcher = BinanceHistoryFetcher()
    fetcher.run() 