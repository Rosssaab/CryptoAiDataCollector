import argparse
import sys
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sklearn.ensemble import RandomForestRegressor
from config import DB_SERVER, DB_NAME, DB_USER, DB_PASSWORD
from tqdm import tqdm
import json
from sklearn.linear_model import LinearRegression

class PricePredictor:
    MODEL_VERSION = "1.0.0"
    TRAINING_WINDOW_DAYS = 90

    def __init__(self):
        self.logger = self.setup_logger()
        self.db_connection = self.connect_to_db()

    def setup_logger(self):
        logger = logging.getLogger('PricePredictor')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        return logger

    def connect_to_db(self):
        try:
            self.logger.info("Connecting to database...")
            connection_string = f'mssql+pyodbc://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}/{DB_NAME}?driver=ODBC+Driver+17+for+SQL+Server'
            engine = create_engine(connection_string)
            self.logger.info("Database connection successful")
            return engine
        except Exception as e:
            self.logger.error(f"Database connection error: {str(e)}")
            sys.exit(1)

    def get_historical_data(self, coin_id, coin_symbol, days=90):
        self.logger.info(f"Fetching historical data for {coin_symbol} (past {days} days)...")
        query = f"""
        SELECT 
            p.[timestamp] as price_date,
            p.price_usd as price,
            AVG(c.sentiment_score) as avg_sentiment,
            COUNT(c.chat_id) as mention_count
        FROM Price_Data p
        LEFT JOIN chat_data c ON p.coin_id = c.coin_id 
            AND c.[timestamp] BETWEEN DATEADD(hour, -24, p.[timestamp]) AND p.[timestamp]
        WHERE p.coin_id = {coin_id}
        AND p.[timestamp] >= DATEADD(day, -{days}, GETDATE())
        GROUP BY p.[timestamp], p.price_usd
        ORDER BY p.[timestamp]
        """
        df = pd.read_sql(query, self.db_connection)
        self.logger.info(f"Found {len(df)} historical price points for {coin_symbol}")
        return df

    def calculate_sentiment_score(self, coin_id, coin_symbol):
        self.logger.info(f"Calculating current sentiment for {coin_symbol}...")
        query = f"""
        SELECT AVG(sentiment_score) as avg_sentiment,
               COUNT(*) as mention_count
        FROM chat_data
        WHERE coin_id = {coin_id}
        AND [timestamp] >= DATEADD(hour, -24, GETDATE())
        """
        result = pd.read_sql(query, self.db_connection)
        sentiment = float(result['avg_sentiment'].iloc[0] or 0)
        mentions = int(result['mention_count'].iloc[0])
        self.logger.info(f"Current sentiment for {coin_symbol}: {sentiment:.2f} (based on {mentions} mentions)")
        return sentiment

    def prepare_features(self, historical_data, coin_symbol):
        """Prepare features for the prediction model"""
        self.logger.info(f"Preparing features for {coin_symbol}...")
        
        # Create features DataFrame
        df = historical_data.copy()
        
        # Add technical indicators
        df['price_change'] = df['price'].pct_change()
        df['price_change_3d'] = df['price'].pct_change(periods=3)
        df['price_change_7d'] = df['price'].pct_change(periods=7)
        df['rolling_mean_3d'] = df['price'].rolling(window=3).mean()
        df['rolling_std_3d'] = df['price'].rolling(window=3).std()
        
        # Add sentiment features
        df['sentiment_score'] = df['avg_sentiment'].fillna(0)
        df['mention_count_normalized'] = df['mention_count'].fillna(0) / df['mention_count'].fillna(0).max()
        
        # Create target variable (next day's price change)
        df['target'] = df['price'].shift(-1) / df['price'] - 1
        
        # Drop rows with NaN values
        df = df.dropna()
        
        # Select features for model
        features = df[[
            'price_change', 'price_change_3d', 'price_change_7d',
            'rolling_mean_3d', 'rolling_std_3d',
            'sentiment_score', 'mention_count_normalized',
            'target'
        ]]
        
        self.logger.info(f"Prepared {len(features)} data points with features")
        return features

    def make_prediction(self, coin_id, coin_symbol):
        try:
            # Get historical data
            historical_data = self.get_historical_data(coin_id, coin_symbol)
            if len(historical_data) < 5:
                self.logger.warning(f"Insufficient historical data for {coin_symbol}")
                return

            # Prepare features
            features = self.prepare_features(historical_data, coin_symbol)
            if len(features) < 5:
                self.logger.warning(f"Insufficient feature data for {coin_symbol}")
                return

            # Calculate current sentiment
            current_sentiment = self.calculate_sentiment_score(coin_id, coin_symbol)
            
            # Get current price
            current_price = historical_data['price'].iloc[-1]
            self.logger.info(f"Current price for {coin_symbol}: ${current_price:,.2f}")

            # Prepare model
            self.logger.info(f"Training prediction model for {coin_symbol}...")
            X = features.drop('target', axis=1)
            y = features['target']
            
            self.model = LinearRegression()
            self.model.fit(X, y)
            
            # Make predictions
            last_features = X.iloc[-1:].copy()
            base_prediction = current_price * (1 + self.model.predict(last_features)[0])
            
            # Calculate predictions with sentiment adjustment
            pred_24h = base_prediction * (1 + current_sentiment * 0.1)
            pred_7d = base_prediction * (1 + current_sentiment * 0.2)
            pred_30d = base_prediction * (1 + current_sentiment * 0.3)
            pred_90d = base_prediction * (1 + current_sentiment * 0.4)
            
            # Ensure predictions are not negative
            pred_24h = max(pred_24h, current_price * 0.8)  # Limit downside to 20%
            pred_7d = max(pred_7d, pred_24h)
            pred_30d = max(pred_30d, pred_7d)
            pred_90d = max(pred_90d, pred_30d)
            
            # Calculate confidence score
            confidence_score = min(abs(self.model.score(X, y) * 100), 95.0)  # Cap at 95%

            # Create prediction data dictionary
            prediction_data = {
                'coin_id': coin_id,
                'current_price': current_price,
                'prediction_24h': pred_24h,
                'prediction_7d': pred_7d,
                'prediction_30d': pred_30d,
                'prediction_90d': pred_90d,
                'sentiment_score': current_sentiment,
                'confidence_score': confidence_score,
                'historical_prices': historical_data['price'].tolist(),
                'features_used': list(X.columns),
                'training_data': features.to_dict(),
                'feature_importance': dict(zip(X.columns, abs(self.model.coef_)))
            }

            # Print prediction summary
            self.print_prediction_summary(coin_symbol, prediction_data)
            
            # Save prediction
            self.save_prediction(prediction_data)

        except Exception as e:
            self.logger.error(f"Prediction error for {coin_symbol}: {str(e)}")

    def save_prediction(self, prediction_data):
        """Save prediction data to database"""
        try:
            # Convert datetime to string for SQL
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Create the query using direct parameter binding
            query = """
            INSERT INTO predictions (
                coin_id, prediction_date, current_price, 
                prediction_24h, prediction_7d, prediction_30d, prediction_90d,
                sentiment_score, confidence_score, features_used,
                model_version, training_window_days, data_points_count
            ) VALUES (
                :coin_id, :pred_date, :curr_price,
                :pred_24h, :pred_7d, :pred_30d, :pred_90d,
                :sentiment, :confidence, :features,
                :model_ver, :train_days, :data_points
            )
            """
            
            # Create parameters dictionary
            params = {
                'coin_id': prediction_data['coin_id'],
                'pred_date': current_time,
                'curr_price': float(prediction_data['current_price']),
                'pred_24h': float(prediction_data['prediction_24h']),
                'pred_7d': float(prediction_data['prediction_7d']),
                'pred_30d': float(prediction_data['prediction_30d']),
                'pred_90d': float(prediction_data['prediction_90d']),
                'sentiment': float(prediction_data['sentiment_score']),
                'confidence': float(prediction_data['confidence_score']),
                'features': json.dumps(prediction_data['features_used']),
                'model_ver': self.MODEL_VERSION,
                'train_days': self.TRAINING_WINDOW_DAYS,
                'data_points': len(prediction_data['historical_prices'])
            }
            
            # Execute query with parameters dictionary
            with self.db_connection.connect() as conn:
                conn.execute(text(query), params)
                conn.commit()
            
            self.logger.info("Prediction saved to database")
            
        except Exception as e:
            self.logger.error(f"Error saving prediction: {str(e)}")

    def run_predictions(self):
        self.logger.info("Starting prediction process...")
        
        # Get all coins (removed is_active filter)
        query = "SELECT coin_id, symbol FROM coins"
        coins = pd.read_sql(query, self.db_connection)
        
        self.logger.info(f"Found {len(coins)} coins")
        
        for _, coin in tqdm(coins.iterrows(), total=len(coins), desc="Processing coins"):
            self.make_prediction(coin['coin_id'], coin['symbol'])

        self.logger.info("\nPrediction process completed!")

    def determine_market_condition(self, historical_prices):
        """Determine if market is bullish, bearish, or sideways"""
        # Implementation logic here
        pass

    def calculate_volatility(self, historical_prices):
        """Calculate price volatility index"""
        # Implementation logic here
        pass

    def save_feature_importance(self, prediction_id, feature_importance):
        """Save feature importance scores to database"""
        query = """
        INSERT INTO prediction_feature_importance 
        (prediction_id, feature_name, importance_score)
        VALUES (?, ?, ?)
        """
        with self.db_connection.connect() as conn:
            for feature, importance in feature_importance.items():
                conn.execute(text(query), (prediction_id, feature, importance))

    def print_prediction_summary(self, coin_symbol, prediction_data):
        """Print a summary of the predictions"""
        self.logger.info("\nPrediction Summary for {}:".format(coin_symbol))
        self.logger.info("==============================")
        self.logger.info("Current Price: ${:,.2f}".format(prediction_data['current_price']))
        
        # Calculate and print price changes
        self.logger.info("24h Prediction: ${:,.2f} ({:+.2f}%)".format(
            prediction_data['prediction_24h'],
            ((prediction_data['prediction_24h'] / prediction_data['current_price']) - 1) * 100
        ))
        
        self.logger.info("7d Prediction:  ${:,.2f} ({:+.2f}%)".format(
            prediction_data['prediction_7d'],
            ((prediction_data['prediction_7d'] / prediction_data['current_price']) - 1) * 100
        ))
        
        self.logger.info("30d Prediction: ${:,.2f} ({:+.2f}%)".format(
            prediction_data['prediction_30d'],
            ((prediction_data['prediction_30d'] / prediction_data['current_price']) - 1) * 100
        ))
        
        self.logger.info("90d Prediction: ${:,.2f} ({:+.2f}%)".format(
            prediction_data['prediction_90d'],
            ((prediction_data['prediction_90d'] / prediction_data['current_price']) - 1) * 100
        ))
        
        self.logger.info("Confidence Score: {:.2f}%".format(prediction_data['confidence_score']))
        self.logger.info("==============================\n")

def main():
    print("\n" + "="*50)
    print("Crypto Price Predictor v1.0")
    print("="*50 + "\n")

    parser = argparse.ArgumentParser(description='Crypto Price Predictor')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    predictor = PricePredictor()
    if args.debug:
        predictor.logger.setLevel(logging.DEBUG)
    
    predictor.run_predictions()

if __name__ == "__main__":
    main()