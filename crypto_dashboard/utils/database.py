import pyodbc
from sqlalchemy import create_engine
import pandas as pd
from config import DB_CONNECTION_STRING

class DatabaseManager:
    def __init__(self):
        self.conn_str = DB_CONNECTION_STRING

    def get_connection(self):
        """Get a raw PYODBC connection"""
        return pyodbc.connect(self.conn_str)

    def get_engine(self):
        """Get a SQLAlchemy engine"""
        return create_engine(f"mssql+pyodbc:///?odbc_connect={self.conn_str}")

    def get_available_coins(self):
        """Get list of available coins from database"""
        try:
            engine = self.get_engine()
            query = "SELECT symbol FROM Coins ORDER BY symbol"
            df = pd.read_sql_query(query, engine)
            return df['symbol'].tolist()
        except Exception as e:
            print(f"Error getting coins: {str(e)}")
            return []

    def get_price_data(self, coin, start_time):
        """Get price data for a specific coin and time range"""
        query = """
        SELECT pd.timestamp, pd.price_usd as price, pd.volume_24h as volume
        FROM Price_Data pd
        JOIN Coins c ON pd.coin_id = c.coin_id
        WHERE c.symbol = ? AND pd.timestamp >= ?
        ORDER BY pd.timestamp
        """
        try:
            engine = self.get_engine()
            return pd.read_sql_query(query, engine, params=(coin, start_time))
        except Exception as e:
            print(f"Error getting price data: {str(e)}")
            return pd.DataFrame()

    def get_sentiment_data(self, coin):
        """Get sentiment data for a specific coin (last 7 days)"""
        query = """
        SELECT 
            CAST(cd.timestamp AS DATE) as date,
            cd.sentiment_label,
            COUNT(*) as count
        FROM chat_data cd
        JOIN Coins c ON cd.coin_id = c.coin_id
        WHERE c.symbol = ? 
        AND cd.timestamp >= DATEADD(day, -7, GETDATE())
        GROUP BY CAST(cd.timestamp AS DATE), cd.sentiment_label
        ORDER BY date
        """
        try:
            engine = self.get_engine()
            return pd.read_sql_query(query, engine, params=(coin,))
        except Exception as e:
            print(f"Error getting sentiment data: {str(e)}")
            return pd.DataFrame()

    def get_mentions_data(self, timerange):
        """Get mentions data for the specified time range"""
        try:
            # Convert timerange to datetime
            if timerange == '24h':
                start_time = "DATEADD(day, -1, GETDATE())"
            elif timerange == '7d':
                start_time = "DATEADD(day, -7, GETDATE())"
            elif timerange == '30d':
                start_time = "DATEADD(day, -30, GETDATE())"
            else:  # 90d
                start_time = "DATEADD(day, -90, GETDATE())"
            
            query = f"""
            SELECT 
                c.symbol,
                cd.sentiment_label,
                COUNT(*) as mention_count
            FROM chat_data cd
            JOIN Coins c ON cd.coin_id = c.coin_id
            WHERE cd.timestamp >= {start_time}
            GROUP BY c.symbol, cd.sentiment_label
            """
            
            engine = self.get_engine()
            return pd.read_sql_query(query, engine)
            
        except Exception as e:
            print(f"Error getting mentions data: {str(e)}")
            return pd.DataFrame()

    def get_coin_details(self, coin):
        """Get detailed information for a specific coin"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get price data
            price_query = """
            SELECT TOP 1 
                pd.price_usd,
                pd.volume_24h,
                pd.price_change_24h
            FROM Price_Data pd
            JOIN Coins c ON pd.coin_id = c.coin_id
            WHERE c.symbol = ?
            ORDER BY pd.timestamp DESC
            """
            cursor.execute(price_query, coin)
            price_data = cursor.fetchone()
            
            # Get sentiment data
            sentiment_query = """
            SELECT 
                sentiment_label,
                COUNT(*) as count,
                AVG(CAST(sentiment_score as float)) as avg_score
            FROM chat_data cd
            JOIN Coins c ON cd.coin_id = c.coin_id
            WHERE c.symbol = ?
            AND cd.timestamp >= DATEADD(day, -1, GETDATE())
            GROUP BY sentiment_label
            """
            cursor.execute(sentiment_query, coin)
            sentiment_data = cursor.fetchall()
            
            conn.close()
            return price_data, sentiment_data
            
        except Exception as e:
            print(f"Error getting coin details: {str(e)}")
            return None, None