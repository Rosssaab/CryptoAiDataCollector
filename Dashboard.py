import tkinter as tk
from tkinter import ttk, messagebox
import pyodbc
from config import DB_CONNECTION_STRING
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
import logging
from datetime import datetime, timedelta

def setup_logging():
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler('crypto_analysis.log')
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger = logging.getLogger('CryptoAnalysis')
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

class CryptoAnalysisDashboard:
    def __init__(self):
        self.logger = setup_logging()
        self.init_database()
        self.root = tk.Tk()
        self.root.title("Crypto Trend Analysis Dashboard")
        self.models = {}  # Store trained models for each coin
        self.create_gui()

    def init_database(self):
        try:
            self.conn = pyodbc.connect(DB_CONNECTION_STRING)
            self.cursor = self.conn.cursor()
            self.logger.info("Database connected successfully")
        except Exception as e:
            self.logger.error(f"Database connection error: {str(e)}")
            raise

    def create_gui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Control Panel
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Coin Selection
        ttk.Label(control_frame, text="Select Coin:").pack(side=tk.LEFT, padx=(0, 5))
        self.coin_var = tk.StringVar()
        self.coin_combo = ttk.Combobox(
            control_frame,
            textvariable=self.coin_var,
            width=15,
            state="readonly"
        )
        self.coin_combo.pack(side=tk.LEFT, padx=(0, 20))

        # Analysis Actions
        ttk.Button(
            control_frame,
            text="Analyze Trends",
            command=self.analyze_trends
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            control_frame,
            text="Train Model",
            command=self.train_model
        ).pack(side=tk.LEFT, padx=5)

        # Results Area
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Trend Analysis Tab
        trend_frame = ttk.Frame(self.notebook)
        self.notebook.add(trend_frame, text="Trend Analysis")
        
        # Create Treeview for trend analysis
        self.trend_tree = ttk.Treeview(
            trend_frame,
            columns=("metric", "value", "trend"),
            show="headings"
        )
        self.trend_tree.heading("metric", text="Metric")
        self.trend_tree.heading("value", text="Current Value")
        self.trend_tree.heading("trend", text="Trend")
        self.trend_tree.pack(fill=tk.BOTH, expand=True)

        # Prediction Tab
        pred_frame = ttk.Frame(self.notebook)
        self.notebook.add(pred_frame, text="Price Predictions")
        
        # Create Treeview for predictions
        self.pred_tree = ttk.Treeview(
            pred_frame,
            columns=("timeframe", "prediction", "confidence"),
            show="headings"
        )
        self.pred_tree.heading("timeframe", text="Timeframe")
        self.pred_tree.heading("prediction", text="Predicted Change")
        self.pred_tree.heading("confidence", text="Confidence")
        self.pred_tree.pack(fill=tk.BOTH, expand=True)

        # Load coins
        self.load_coins()
        
        # Set minimum window size
        self.root.minsize(800, 600)

    def load_coins(self):
        try:
            self.cursor.execute("""
                SELECT DISTINCT c.symbol 
                FROM Coins c
                JOIN price_data p ON c.coin_id = p.coin_id
                JOIN chat_data cd ON c.coin_id = cd.coin_id
                ORDER BY c.symbol
            """)
            coins = [row[0] for row in self.cursor.fetchall()]
            self.coin_combo['values'] = coins
            if coins:
                self.coin_var.set(coins[0])
        except Exception as e:
            self.logger.error(f"Error loading coins: {str(e)}")
            messagebox.showerror("Error", "Failed to load coins")

    def analyze_trends(self):
        coin = self.coin_var.get()
        if not coin:
            messagebox.showwarning("Warning", "Please select a coin")
            return

        try:
            # Clear existing items
            for item in self.trend_tree.get_children():
                self.trend_tree.delete(item)

            # Get recent price data
            query = """
                SELECT TOP 168 -- Last 7 days
                    p.price_usd,
                    p.volume_24h,
                    p.price_change_24h,
                    cd.sentiment_score
                FROM price_data p
                JOIN Coins c ON p.coin_id = c.coin_id
                LEFT JOIN chat_data cd ON c.coin_id = cd.coin_id 
                    AND cd.timestamp >= DATEADD(hour, -24, p.timestamp)
                WHERE c.symbol = ?
                ORDER BY p.timestamp DESC
            """
            
            df = pd.read_sql(query, self.conn, params=[coin])
            
            if df.empty:
                messagebox.showinfo("Info", "No data available for analysis")
                return

            # Calculate trends
            price_trend = self.calculate_trend(df['price_usd'])
            volume_trend = self.calculate_trend(df['volume_24h'])
            sentiment_trend = self.calculate_trend(df['sentiment_score'])

            # Add results to treeview
            self.trend_tree.insert("", "end", values=(
                "Price", f"${df['price_usd'].iloc[0]:.2f}", 
                self.format_trend(price_trend)
            ))
            self.trend_tree.insert("", "end", values=(
                "Volume", f"${df['volume_24h'].iloc[0]:,.0f}", 
                self.format_trend(volume_trend)
            ))
            self.trend_tree.insert("", "end", values=(
                "Sentiment", f"{df['sentiment_score'].mean():.2f}", 
                self.format_trend(sentiment_trend)
            ))

            # Make prediction if model exists
            if coin in self.models:
                self.predict_prices(coin, df)

        except Exception as e:
            self.logger.error(f"Error analyzing trends: {str(e)}")
            messagebox.showerror("Error", "Failed to analyze trends")

    def train_model(self):
        coin = self.coin_var.get()
        if not coin:
            messagebox.showwarning("Warning", "Please select a coin")
            return

        try:
            # Check data availability first
            check_query = """
                SELECT 
                    COUNT(DISTINCT p.timestamp) as price_points,
                    COUNT(DISTINCT cd.chat_data_id) as sentiment_points,
                    DATEDIFF(hour, MIN(p.timestamp), MAX(p.timestamp)) as hours_span
                FROM Coins c
                LEFT JOIN price_data p ON c.coin_id = p.coin_id
                LEFT JOIN chat_data cd ON c.coin_id = cd.coin_id
                WHERE c.symbol = ?
                GROUP BY c.coin_id
            """
            
            self.cursor.execute(check_query, [coin])
            result = self.cursor.fetchone()
            
            if not result:
                messagebox.showwarning("Warning", "No data available for this coin")
                return
            
            price_points, sentiment_points, hours_span = result
            
            # Data requirements check
            if price_points < 720:  # 30 days of hourly data
                messagebox.showwarning(
                    "Insufficient Data", 
                    f"Need at least 720 price records, but only have {price_points}.\n"
                    f"Continue collecting price data for {coin}."
                )
                return
            
            if sentiment_points < 100:
                messagebox.showwarning(
                    "Insufficient Data", 
                    f"Need at least 100 sentiment records, but only have {sentiment_points}.\n"
                    f"Continue collecting sentiment data for {coin}."
                )
                return
            
            if hours_span < 720:  # 30 days
                messagebox.showwarning(
                    "Insufficient History", 
                    f"Need at least 30 days of history, but only have {hours_span/24:.1f} days.\n"
                    f"Continue collecting data for {coin}."
                )
                return

            # If we get here, proceed with model training
            # Get historical data for training
            query = """
                SELECT 
                    p.price_usd,
                    p.volume_24h,
                    p.price_change_24h,
                    COALESCE(AVG(cd.sentiment_score), 0) as avg_sentiment,
                    LEAD(p.price_usd, 24) OVER (ORDER BY p.timestamp) as future_price
                FROM price_data p
                JOIN Coins c ON p.coin_id = c.coin_id
                LEFT JOIN chat_data cd ON c.coin_id = cd.coin_id 
                    AND cd.timestamp >= DATEADD(hour, -24, p.timestamp)
                WHERE c.symbol = ?
                GROUP BY p.timestamp, p.price_usd, p.volume_24h, p.price_change_24h
                ORDER BY p.timestamp DESC
            """
            
            df = pd.read_sql(query, self.conn, params=[coin])
            df = df.dropna()  # Remove rows with missing future prices

            if df.empty:
                messagebox.showinfo("Info", "Insufficient data for training")
                return

            # Prepare features and target
            X = df[['price_usd', 'volume_24h', 'price_change_24h', 'avg_sentiment']]
            y = (df['future_price'] - df['price_usd']) / df['price_usd']  # Predict % change

            # Split and scale data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Train model
            model = RandomForestRegressor(n_estimators=100)
            model.fit(X_train_scaled, y_train)

            # Save model and scaler
            self.models[coin] = {
                'model': model,
                'scaler': scaler,
                'accuracy': model.score(X_test_scaled, y_test)
            }

            messagebox.showinfo("Success", 
                f"Model trained successfully\nAccuracy Score: {self.models[coin]['accuracy']:.2%}")

        except Exception as e:
            self.logger.error(f"Error training model: {str(e)}")
            messagebox.showerror("Error", "Failed to train model")

    def predict_prices(self, coin, current_data):
        try:
            # Clear existing predictions
            for item in self.pred_tree.get_children():
                self.pred_tree.delete(item)

            if coin not in self.models:
                return

            # Prepare current data for prediction
            X = current_data[['price_usd', 'volume_24h', 'price_change_24h', 'sentiment_score']].iloc[0]
            X = X.values.reshape(1, -1)
            X_scaled = self.models[coin]['scaler'].transform(X)

            # Make prediction
            pred_change = self.models[coin]['model'].predict(X_scaled)[0]
            confidence = self.models[coin]['accuracy']

            # Add prediction to tree
            self.pred_tree.insert("", "end", values=(
                "24 Hours",
                f"{pred_change:+.2%}",
                f"{confidence:.2%}"
            ))

        except Exception as e:
            self.logger.error(f"Error making prediction: {str(e)}")

    @staticmethod
    def calculate_trend(series):
        if series.empty:
            return 0
        # Calculate percentage change over the series
        return (series.iloc[0] - series.iloc[-1]) / series.iloc[-1] if series.iloc[-1] != 0 else 0

    @staticmethod
    def format_trend(trend):
        if trend > 0.05:
            return "Strong Upward ↑↑"
        elif trend > 0:
            return "Slight Upward ↑"
        elif trend < -0.05:
            return "Strong Downward ↓↓"
        elif trend < 0:
            return "Slight Downward ↓"
        else:
            return "Neutral →"

def main():
    app = CryptoAnalysisDashboard()
    app.root.mainloop()

if __name__ == "__main__":
    main() 