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
        
        # Set initial window size to 1024px wide
        # Calculate height based on 16:9 aspect ratio
        width = 1024
        height = int(width * 9/16)  # This will be 576px
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate center position
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        # Set window size and position
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Apply a modern theme
        style = ttk.Style()
        style.theme_use('clam')
        
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
        
        # Add initial window size
        self.last_width = None
        self.last_height = None
        
        # Create a loading label (hidden initially)
        self.loading_label = ttk.Label(self.root, text="Loading...", style='Loading.TLabel')
        self.loading_label.place(relx=0.5, rely=0.5, anchor='center')
        self.loading_label.place_forget()  # Hide initially
        
        # Configure loading label style
        style = ttk.Style()
        style.configure('Loading.TLabel', 
                       font=('Helvetica', 14, 'bold'),
                       background='#2B2B2B',
                       foreground='white')

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
        self.root.config(cursor="wait")  # Set busy cursor
        plt.close('all')
        try:
            coin = self.coin_var.get()
            timerange = self.timerange_var.get()
            
            # Show loading indicator
            self.show_loading()
            
            # Clear existing charts
            for widget in self.price_charts_frame.winfo_children():
                widget.destroy()
            
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
        finally:
            # Hide loading indicator
            self.hide_loading()
            self.root.config(cursor="")  # Reset cursor

    def update_sentiment_charts(self):
        self.root.config(cursor="wait")  # Set busy cursor
        plt.close('all')
        try:
            coin = self.sentiment_coin_var.get()
            
            # Show loading indicator
            self.show_loading()
            
            # Clear existing charts
            for widget in self.sentiment_charts_frame.winfo_children():
                widget.destroy()
            
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
        finally:
            # Hide loading indicator
            self.hide_loading()
            self.root.config(cursor="")  # Reset cursor

    def update_mentions_view(self):
        # Clear existing charts and close all figures
        plt.close('all')
        for widget in self.mentions_charts_frame.winfo_children():
            widget.destroy()
            
        try:
            # Get current window size
            current_width = self.root.winfo_width()
            current_height = self.root.winfo_height()
            
            # Update last known size
            self.last_width = current_width
            self.last_height = current_height
            
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
                negative_mentions = coin_data[coin_data['sentiment_label'].isin(['negative', 'very negative'])]['mention_count'].sum()
                neutral_mentions = coin_data[coin_data['sentiment_label'] == 'neutral']['mention_count'].sum()
                
                # Calculate positive percentage
                positive_percentage = (positive_mentions / total_mentions * 100) if total_mentions > 0 else 0
                coin_sentiments.append((coin, positive_percentage))
            
            # Sort coins by positive sentiment percentage (descending)
            sorted_coins = [coin for coin, _ in sorted(coin_sentiments, key=lambda x: x[1], reverse=True)]
            n_coins = len(sorted_coins)
            n_cols = 3  # Changed to 3 columns
            n_rows = (n_coins + n_cols - 1) // n_cols
            
            # Create a canvas with scrollbar first
            canvas = tk.Canvas(self.mentions_charts_frame, width=current_width-50)
            scrollbar = ttk.Scrollbar(self.mentions_charts_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            # Configure the canvas
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # Pack scrollbar and canvas
            scrollbar.pack(side="right", fill="y")
            canvas.pack(side="left", fill="both", expand=True)
            
            # Create a window in the canvas for the scrollable frame
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            
            # Calculate figure size based on current window size
            fig_width = current_width / 100  # Convert to inches
            single_pie_height = current_height / 100 * 0.8
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
                
                ax.set_title(coin, 
                            pad=20, 
                            y=1.1, 
                            fontsize=18, 
                            weight='bold',
                            color='black')
                
                def on_pick(event, coin_symbol=coin):
                    # Ignore if not left click
                    if not hasattr(event, 'mouseevent') or event.mouseevent.button != 1:
                        return
                    
                    # Prevent multiple triggers
                    if hasattr(self, '_processing'):
                        return
                    self._processing = True
                    
                    def do_updates():
                        try:
                            # Set coin in price analysis tab
                            self.coin_var.set(coin_symbol)
                            
                            # Set coin in sentiment tab
                            self.sentiment_coin_var.set(coin_symbol)
                            
                            # Switch to sentiment tab first
                            self.notebook.select(2)
                            
                            # Then update the charts
                            self.update_sentiment_charts()
                            
                        except Exception as e:
                            print(f"Error in pie chart update: {str(e)}")
                        finally:
                            if hasattr(self, '_processing'):
                                delattr(self, '_processing')
                    
                    # Schedule the updates
                    self.root.after(100, do_updates)
                
                # Make pie wedges pickable
                for wedge in wedges:
                    wedge.set_picker(True)
                    wedge.figure.canvas.mpl_connect('pick_event', 
                        lambda event, coin_symbol=coin: on_pick(event, coin_symbol))
            
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
            
            # Add resize handler
            def on_window_resize(event=None):
                if event.widget == self.root:  # Only handle root window resizes
                    # Check if size changed significantly (more than 50 pixels)
                    if (abs(event.width - self.last_width) > 50 or 
                        abs(event.height - self.last_height) > 50):
                        
                        # Cancel previous timer if it exists
                        if self.resize_timer:
                            self.root.after_cancel(self.resize_timer)
                        
                        # Schedule new update
                        self.resize_timer = self.root.after(500, self.update_mentions_view)
            
            # Bind resize event
            self.root.bind('<Configure>', on_window_resize)
            
            # Draw the canvas
            chart_canvas.draw()
            
        except Exception as e:
            print(f"Error updating mentions view: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # Hide loading indicator
            self.hide_loading()

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

    def show_loading(self):
        """Show the loading indicator safely"""
        if self.root.winfo_exists() and hasattr(self, 'loading_label'):
            self.loading_label.lift()
            self.loading_label.place(relx=0.5, rely=0.5, anchor='center')
            self.root.update_idletasks()

    def hide_loading(self):
        """Hide the loading indicator safely"""
        if self.root.winfo_exists() and hasattr(self, 'loading_label'):
            self.loading_label.place_forget()
            self.root.update_idletasks()

if __name__ == "__main__":
    app = Dashboard()
    app.run()