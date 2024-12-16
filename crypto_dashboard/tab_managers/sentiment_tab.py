import tkinter as tk
from tkinter import ttk

class SentimentTab:
    def __init__(self, parent, db_manager, chart_manager):
        self.parent = parent
        self.db_manager = db_manager
        self.chart_manager = chart_manager
        
        # Create the tab
        self.frame = ttk.Frame(parent)
        self.setup_tab()

    def setup_tab(self):
        # Controls frame
        self.controls_frame = ttk.Frame(self.frame)
        self.controls_frame.pack(fill='x', padx=5, pady=5)
        
        # Coin selection
        ttk.Label(self.controls_frame, text="Coin:").pack(side='left', padx=5)
        self.coin_var = tk.StringVar()
        coins = ['BTC', 'ETH', 'SOL', 'XRP', 'DOGE']
        self.coin_dropdown = ttk.Combobox(self.controls_frame, textvariable=self.coin_var, values=coins)
        self.coin_dropdown.pack(side='left', padx=5)
        self.coin_dropdown.set(coins[0])
        
        # Update button
        update_btn = ttk.Button(self.controls_frame, text="Update", command=self.update_charts)
        update_btn.pack(side='left', padx=5)
        
        # Charts frame
        self.charts_frame = ttk.Frame(self.frame)
        self.charts_frame.pack(fill='both', expand=True, padx=5, pady=5)

    def update_charts(self):
        try:
            coin = self.coin_var.get()
            
            # Clear existing charts
            for widget in self.charts_frame.winfo_children():
                widget.destroy()
            
            # Get data and create charts
            df = self.db_manager.get_sentiment_data(coin)
            if not df.empty:
                canvas = self.chart_manager.create_sentiment_charts(df, coin, self.charts_frame)
                canvas.get_tk_widget().pack(fill='both', expand=True)
            
        except Exception as e:
            print(f"Error updating sentiment charts: {str(e)}")

    def get_frame(self):
        return self.frame

    def get_current_coin(self):
        return self.coin_var.get()

    def set_coin(self, coin):
        """Set the selected coin in the dropdown and update charts"""
        if hasattr(self, 'coin_var'):
            self.coin_var.set(coin)
            self.coin_dropdown.set(coin)  # Explicitly set the dropdown
            self.frame.update_idletasks()  # Force GUI update
            self.update_charts()  # Immediately update the charts
