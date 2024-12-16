import tkinter as tk
from tkinter import ttk
import pyodbc
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
from config import DB_CONNECTION_STRING
from sqlalchemy import create_engine

class Dashboard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Crypto Analytics Dashboard")
        self.root.state('zoomed')  # Start maximized
        
        # Apply a modern theme
        style = ttk.Style()
        style.theme_use('clam')  # Using clam theme as base
        
        # Configure custom colors
        style.configure("TFrame", background="#2B2B2B")
        style.configure("TLabel", background="#2B2B2B", foreground="white")
        style.configure("TButton", background="#404040", foreground="white")
        style.configure("TNotebook", background="#2B2B2B", foreground="white")
        style.configure("TNotebook.Tab", background="#404040", foreground="white", padding=[10, 2])
        style.map('TNotebook.Tab', background=[('selected', '#505050')])
        
        # Configure custom style for mentions tab
        style.configure("Mentions.TFrame", background="#FFFACD")  # Lemon chiffon color
        
        # Configure the root window color
        self.root.configure(bg="#2B2B2B")
        
        # Add protocol handler for window close button
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Use connection string from config
        self.conn_str = DB_CONNECTION_STRING
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create tabs
        self.mentions_tab = ttk.Frame(self.notebook, style="Mentions.TFrame")  # Apply lemon style
        self.price_tab = ttk.Frame(self.notebook)
        self.sentiment_tab = ttk.Frame(self.notebook)
        
        # Add tabs in new order
        self.notebook.add(self.mentions_tab, text='Mentions Overview')
        self.notebook.add(self.price_tab, text='Price Analysis')
        self.notebook.add(self.sentiment_tab, text='Sentiment Analysis')
        
        # Setup each tab
        self.setup_mentions_tab()
        self.setup_price_tab()
        self.setup_sentiment_tab()
        
        # Add resize timer variable
        self.resize_timer = None

    def get_db_connection(self):
        return pyodbc.connect(self.conn_str)

    def setup_price_tab(self):
        # Controls frame
        controls_frame = ttk.Frame(self.price_tab)
        controls_frame.pack(fill='x', padx=5, pady=5)
        
        # Dropdown for coin selection
        ttk.Label(controls_frame, text="Select Coin:").pack(side='left', padx=5)
        self.coin_var = tk.StringVar()
        coins = self.get_available_coins()
        coin_dropdown = ttk.Combobox(controls_frame, textvariable=self.coin_var, values=coins)
        coin_dropdown.pack(side='left', padx=5)
        coin_dropdown.set(coins[0] if coins else '')
        
        # Time range selection
        ttk.Label(controls_frame, text="Time Range:").pack(side='left', padx=5)
        self.timerange_var = tk.StringVar()
        ranges = ['24h', '7d', '30d', '90d']
        range_dropdown = ttk.Combobox(controls_frame, textvariable=self.timerange_var, values=ranges)
        range_dropdown.pack(side='left', padx=5)
        range_dropdown.set('24h')
        
        # Update button
        update_btn = ttk.Button(controls_frame, text="Update", command=self.update_price_charts)
        update_btn.pack(side='left', padx=5)
        
        # Charts frame
        self.price_charts_frame = ttk.Frame(self.price_tab)
        self.price_charts_frame.pack(fill='both', expand=True, padx=5, pady=5)

    def setup_sentiment_tab(self):
        # Controls frame
        controls_frame = ttk.Frame(self.sentiment_tab)
        controls_frame.pack(fill='x', padx=5, pady=5)
        
        # Dropdown for coin selection
        ttk.Label(controls_frame, text="Select Coin:").pack(side='left', padx=5)
        self.sentiment_coin_var = tk.StringVar()
        coins = self.get_available_coins()
        coin_dropdown = ttk.Combobox(controls_frame, textvariable=self.sentiment_coin_var, values=coins)
        coin_dropdown.pack(side='left', padx=5)
        coin_dropdown.set(coins[0] if coins else '')
        
        # Update button
        update_btn = ttk.Button(controls_frame, text="Update", command=self.update_sentiment_charts)
        update_btn.pack(side='left', padx=5)
        
        # Charts frame
        self.sentiment_charts_frame = ttk.Frame(self.sentiment_tab)
        self.sentiment_charts_frame.pack(fill='both', expand=True, padx=5, pady=5)

    def setup_mentions_tab(self):
        # Controls frame
        self.mentions_controls_frame = ttk.Frame(self.mentions_tab)
        self.mentions_controls_frame.pack(fill='x', padx=5, pady=5)
        
        # Time range selection
        ttk.Label(self.mentions_controls_frame, text="Time Range:").pack(side='left', padx=5)
        self.mentions_timerange_var = tk.StringVar()
        ranges = ['24h', '7d', '30d', '90d']
        self.range_dropdown = ttk.Combobox(self.mentions_controls_frame, textvariable=self.mentions_timerange_var, values=ranges)
        self.range_dropdown.pack(side='left', padx=5)
        self.range_dropdown.set('7d')
        
        # Update button
        update_btn = ttk.Button(self.mentions_controls_frame, text="Update", command=self.update_mentions_view)
        update_btn.pack(side='left', padx=5)
        
        # Create a frame for the main content with charts and details
        self.mentions_content_frame = ttk.Frame(self.mentions_tab)
        self.mentions_content_frame.pack(fill='both', expand=True)
        
        # Charts frame on the left
        self.mentions_charts_frame = ttk.Frame(self.mentions_content_frame)
        self.mentions_charts_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        # Details frame on the right
        self.mentions_details_frame = ttk.LabelFrame(self.mentions_content_frame, text="Coin Details")
        self.mentions_details_frame.pack(side='right', fill='y', padx=5, pady=5)

    def get_available_coins(self):
        try:
            engine = create_engine(f"mssql+pyodbc:///?odbc_connect={self.conn_str}")
            query = "SELECT symbol FROM Coins ORDER BY symbol"
            df = pd.read_sql_query(query, engine)
            return df['symbol'].tolist()
        except Exception as e:
            print(f"Error getting coins: {str(e)}")
            return []

    def update_price_charts(self):
        coin = self.coin_var.get()
        timerange = self.timerange_var.get()
        
        # Clear existing charts
        for widget in self.price_charts_frame.winfo_children():
            widget.destroy()
        
        try:
            # Calculate time range
            now = datetime.now()
            if timerange == '24h':
                start_time = now - timedelta(days=1)
            elif timerange == '7d':
                start_time = now - timedelta(days=7)
            elif timerange == '30d':
                start_time = now - timedelta(days=30)
            else:  # 90d
                start_time = now - timedelta(days=90)
            
            query = """
            SELECT pd.timestamp, pd.price_usd as price, pd.volume_24h as volume
            FROM Price_Data pd
            JOIN Coins c ON pd.coin_id = c.coin_id
            WHERE c.symbol = ? AND pd.timestamp >= ?
            ORDER BY pd.timestamp
            """
            
            # Create SQLAlchemy engine
            engine = create_engine(f"mssql+pyodbc:///?odbc_connect={self.conn_str}")
            df = pd.read_sql_query(query, engine, params=(coin, start_time))
            
            if len(df) == 0:
                return
            
            # Create price chart
            fig = plt.figure(figsize=(12, 8))
            
            # Price subplot
            ax1 = fig.add_subplot(211)
            ax1.plot(df['timestamp'], df['price'])
            ax1.set_title(f'{coin} Price')
            ax1.set_xlabel('Time')
            ax1.set_ylabel('Price (USD)')
            
            # Volume subplot
            ax2 = fig.add_subplot(212)
            ax2.bar(df['timestamp'], df['volume'])
            ax2.set_title(f'{coin} Volume')
            ax2.set_xlabel('Time')
            ax2.set_ylabel('Volume (USD)')
            
            plt.tight_layout()
            
            # Embed chart in tkinter
            canvas = FigureCanvasTkAgg(fig, self.price_charts_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
            
        except Exception as e:
            print(f"Error updating price charts: {str(e)}")

    def update_sentiment_charts(self):
        coin = self.sentiment_coin_var.get()
        
        # Clear existing charts
        for widget in self.sentiment_charts_frame.winfo_children():
            widget.destroy()
        
        try:
            # Get sentiment data for last 7 days
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
            
            engine = create_engine(f"mssql+pyodbc:///?odbc_connect={self.conn_str}")
            df = pd.read_sql_query(query, engine, params=(coin,))
            
            if len(df) == 0:
                return
                
            # Create sentiment distribution chart
            fig = plt.figure(figsize=(12, 8))
            
            # Sentiment over time
            ax1 = fig.add_subplot(211)
            pivot_df = df.pivot(index='date', columns='sentiment_label', values='count').fillna(0)
            pivot_df.plot(kind='bar', stacked=True, ax=ax1)
            ax1.set_title(f'{coin} Sentiment Distribution Over Time')
            ax1.set_xlabel('Date')
            ax1.set_ylabel('Number of Mentions')
            plt.xticks(rotation=45)
            
            # Pie chart of total sentiment distribution
            ax2 = fig.add_subplot(212)
            sentiment_totals = df.groupby('sentiment_label')['count'].sum()
            ax2.pie(sentiment_totals, labels=sentiment_totals.index, autopct='%1.1f%%')
            ax2.set_title('Overall Sentiment Distribution')
            
            plt.tight_layout()
            
            # Embed chart in tkinter
            canvas = FigureCanvasTkAgg(fig, self.sentiment_charts_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
            
        except Exception as e:
            print(f"Error updating sentiment charts: {str(e)}")

    def update_mentions_view(self):
        # Clear existing charts
        for widget in self.mentions_charts_frame.winfo_children():
            widget.destroy()
            
        try:
            # Get the time range
            timerange = self.mentions_timerange_var.get()
            
            # Calculate time range
            now = datetime.now()
            if timerange == '24h':
                start_time = now - timedelta(days=1)
            elif timerange == '7d':
                start_time = now - timedelta(days=7)
            elif timerange == '30d':
                start_time = now - timedelta(days=30)
            else:  # 90d
                start_time = now - timedelta(days=90)
            
            # Query to get mentions data
            query = """
            SELECT 
                c.symbol,
                cd.sentiment_label,
                COUNT(*) as mention_count
            FROM chat_data cd
            JOIN Coins c ON cd.coin_id = c.coin_id
            WHERE cd.timestamp >= ?
            GROUP BY c.symbol, cd.sentiment_label
            """
            
            # Create SQLAlchemy engine and connect
            engine = create_engine(f"mssql+pyodbc:///?odbc_connect={self.conn_str}")
            with engine.connect() as connection:
                df = pd.read_sql_query(query, connection, params=(start_time,))
            
            # Calculate positive sentiment percentage for each coin
            coin_sentiments = []
            for coin in df['symbol'].unique():
                coin_data = df[df['symbol'] == coin]
                total_mentions = coin_data['mention_count'].sum()
                positive_mentions = coin_data[coin_data['sentiment_label'].isin(['positive', 'very positive'])]['mention_count'].sum()
                positive_percentage = (positive_mentions / total_mentions * 100) if total_mentions > 0 else 0
                coin_sentiments.append((coin, positive_percentage))
            
            # Sort coins by positive sentiment percentage (descending)
            sorted_coins = [coin for coin, _ in sorted(coin_sentiments, key=lambda x: x[1], reverse=True)]
            n_coins = len(sorted_coins)
            n_cols = 3  # Changed to 3 columns
            n_rows = (n_coins + n_cols - 1) // n_cols
            
            # Get window dimensions once
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
            
            # Create a canvas with scrollbar first
            canvas = tk.Canvas(self.mentions_charts_frame, width=window_width-50)
            scrollbar = ttk.Scrollbar(self.mentions_charts_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            # Configure the canvas
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # Pack scrollbar and canvas
            scrollbar.pack(side="right", fill="y")
            canvas.pack(side="left", fill="both", expand=True)
            
            # Create a window in the canvas for the scrollable frame
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            
            # Calculate figure size
            fig_width = window_width / 100  # Convert to inches
            single_pie_height = window_height / 100 * 0.8
            fig_height = single_pie_height * n_rows
            
            # Create figure with lemon background
            fig = plt.figure(figsize=(fig_width, fig_height), dpi=100, facecolor='#FFFACD')
            
            # Set up the plots
            plt.subplots_adjust(hspace=1.2, wspace=0.3)
            
            colors = {
                'positive': '#00ff00',    # Bright green
                'very positive': '#008000', # Dark green
                'neutral': '#808080',     # Grey
                'negative': '#ff0000',    # Bright red
                'very negative': '#800000'  # Dark red
            }
            
            for idx, coin in enumerate(sorted_coins):
                coin_data = df[df['symbol'] == coin]
                ax = fig.add_subplot(n_rows, n_cols, idx + 1)
                sentiment_counts = coin_data.groupby('sentiment_label')['mention_count'].sum()
                
                pie_colors = [colors.get(label.lower(), '#808080') for label in sentiment_counts.index]
                wedges, texts, autotexts = ax.pie(sentiment_counts, 
                                                labels=[''] * len(sentiment_counts),
                                                autopct='%1.1f%%',
                                                colors=pie_colors,
                                                radius=1.0,
                                                startangle=90,
                                                labeldistance=1.1,
                                                explode=[0.05] * len(sentiment_counts),
                                                shadow=True)
                
                plt.setp(autotexts, size=16, weight="bold", color='black')
                
                positive_pct = next(pct for coin_, pct in coin_sentiments if coin_ == coin)
                ax.set_title(f'{coin} ({positive_pct:.1f}% Positive)', 
                            pad=20, 
                            y=1.1, 
                            fontsize=18, 
                            weight='bold',
                            color='black')
                
                ax.set_facecolor('#FFFACD')
            
            plt.tight_layout(h_pad=4.0, w_pad=2.0)
            
            # Create the matplotlib canvas
            chart_canvas = FigureCanvasTkAgg(fig, scrollable_frame)
            chart_widget = chart_canvas.get_tk_widget()
            chart_widget.pack(fill='both', expand=True)
            
            # Configure scrolling
            def on_mousewheel(event):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
            canvas.bind_all("<MouseWheel>", on_mousewheel)
            
            # Update the scroll region after the window is updated
            def configure_scroll_region(event):
                canvas.configure(scrollregion=canvas.bbox("all"))
            
            scrollable_frame.bind('<Configure>', configure_scroll_region)
            
            # Draw once
            chart_canvas.draw()
            
        except Exception as e:
            print(f"Error updating mentions view: {str(e)}")
            import traceback
            traceback.print_exc()

    def show_coin_detail(self, coin):
        # Clear previous details
        for widget in self.mentions_details_frame.winfo_children():
            widget.destroy()
        
        try:
            # Get current price and sentiment data
            query = """
            SELECT TOP 1 
                pd.price_usd,
                pd.volume_24h,
                pd.price_change_24h
            FROM Price_Data pd
            JOIN Coins c ON pd.coin_id = c.coin_id
            WHERE c.symbol = ?
            ORDER BY pd.timestamp DESC
            """
            
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute(query, coin)
            price_row = cursor.fetchone()
            
            # Add title
            title = ttk.Label(self.mentions_details_frame, text=f"{coin} Details", font=('Helvetica', 12, 'bold'))
            title.pack(pady=10)
            
            if price_row:
                price, volume, change = price_row
                
                # Price info
                price_frame = ttk.Frame(self.mentions_details_frame)
                price_frame.pack(fill='x', padx=5, pady=5)
                
                ttk.Label(price_frame, text=f"Current Price: ${price:,.2f}").pack()
                
                change_color = 'green' if change > 0 else 'red' if change < 0 else 'black'
                ttk.Label(price_frame, text=f"24h Change: {change:+.2f}%", foreground=change_color).pack()
                
                ttk.Label(price_frame, text=f"24h Volume: ${volume:,.0f}").pack()
            
            # Get sentiment distribution
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
            sentiment_rows = cursor.fetchall()
            
            if sentiment_rows:
                # Sentiment info
                sentiment_frame = ttk.LabelFrame(self.mentions_details_frame, text="24h Sentiment")
                sentiment_frame.pack(fill='x', padx=5, pady=5)
                
                total_mentions = sum(row[1] for row in sentiment_rows)
                
                for label, count, avg_score in sentiment_rows:
                    percentage = (count / total_mentions) * 100
                    ttk.Label(sentiment_frame, 
                             text=f"{label}: {count} ({percentage:.1f}%)").pack()
            
            conn.close()
            
        except Exception as e:
            print(f"Error showing coin detail: {str(e)}")
            ttk.Label(self.mentions_details_frame, text="Error loading details").pack()

    def on_closing(self):
        """Handle cleanup when window is closed"""
        try:
            # Cancel any pending resize timer
            if hasattr(self, 'resize_timer') and self.resize_timer:
                self.root.after_cancel(self.resize_timer)
            
            # Close all matplotlib figures
            plt.close('all')
            
            # Destroy the root window
            self.root.destroy()
            
            # Quit the application
            self.root.quit()
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = Dashboard()
    app.run()