import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta

class PriceTab:
    def __init__(self, parent, db_manager, chart_manager):
        self.parent = parent
        self.db_manager = db_manager
        self.chart_manager = chart_manager
        
        # Create the tab
        self.frame = ttk.Frame(parent)
        self.setup_tab()

    def setup_tab(self):
        # Controls frame
        controls_frame = ttk.Frame(self.frame)
        controls_frame.pack(fill='x', padx=5, pady=5)
        
        # Dropdown for coin selection
        ttk.Label(controls_frame, text="Select Coin:").pack(side='left', padx=5)
        self.coin_var = tk.StringVar()
        coins = self.db_manager.get_available_coins()
        self.coin_dropdown = ttk.Combobox(controls_frame, textvariable=self.coin_var, values=coins)
        self.coin_dropdown.pack(side='left', padx=5)
        self.coin_dropdown.set(coins[0] if coins else '')
        
        # Time range selection
        ttk.Label(controls_frame, text="Time Range:").pack(side='left', padx=5)
        self.timerange_var = tk.StringVar()
        ranges = ['24h', '7d', '30d', '90d']
        self.range_dropdown = ttk.Combobox(controls_frame, textvariable=self.timerange_var, values=ranges)
        self.range_dropdown.pack(side='left', padx=5)
        self.range_dropdown.set('24h')
        
        # Update button
        update_btn = ttk.Button(controls_frame, text="Update", command=self.update_charts)
        update_btn.pack(side='left', padx=5)
        
        # Charts frame
        self.charts_frame = ttk.Frame(self.frame)
        self.charts_frame.pack(fill='both', expand=True, padx=5, pady=5)

    def update_charts(self):
        try:
            coin = self.coin_var.get()
            timerange = self.timerange_var.get()
            
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
            
            # Clear existing charts
            for widget in self.charts_frame.winfo_children():
                widget.destroy()
            
            # Get data and create charts
            df = self.db_manager.get_price_data(coin, start_time)
            if not df.empty:
                canvas = self.chart_manager.create_price_charts(df, coin, self.charts_frame)
                canvas.get_tk_widget().pack(fill='both', expand=True)
            
        except Exception as e:
            print(f"Error updating price charts: {str(e)}")

    def get_frame(self):
        return self.frame

    def get_current_coin(self):
        return self.coin_var.get()

    def set_coin(self, coin):
        self.coin_var.set(coin)
