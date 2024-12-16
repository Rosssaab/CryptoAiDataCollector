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
        controls_frame = ttk.Frame(self.frame)
        controls_frame.pack(fill='x', padx=5, pady=5)
        
        # Dropdown for coin selection
        ttk.Label(controls_frame, text="Select Coin:").pack(side='left', padx=5)
        self.coin_var = tk.StringVar()
        coins = self.db_manager.get_available_coins()
        self.coin_dropdown = ttk.Combobox(controls_frame, textvariable=self.coin_var, values=coins)
        self.coin_dropdown.pack(side='left', padx=5)
        self.coin_dropdown.set(coins[0] if coins else '')
        
        # Update button
        update_btn = ttk.Button(controls_frame, text="Update", command=self.update_charts)
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
        self.coin_var.set(coin)
        self.update_charts()
