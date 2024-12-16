import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class MentionsTab:
    def __init__(self, parent, db_manager, chart_manager):
        self.parent = parent
        self.db_manager = db_manager
        self.chart_manager = chart_manager
        
        # Create the tab
        self.frame = ttk.Frame(parent, style="Mentions.TFrame")
        self.setup_tab()
        
        # Store references for resize handling
        self.last_width = None
        self.last_height = None
        self.resize_timer = None

    def setup_tab(self):
        # Controls frame
        self.controls_frame = ttk.Frame(self.frame)
        self.controls_frame.pack(fill='x', padx=5, pady=5)
        
        # Time range selection
        ttk.Label(self.controls_frame, text="Time Range:").pack(side='left', padx=5)
        self.timerange_var = tk.StringVar()
        ranges = ['24h', '7d', '30d', '90d']
        self.range_dropdown = ttk.Combobox(self.controls_frame, textvariable=self.timerange_var, values=ranges)
        self.range_dropdown.pack(side='left', padx=5)
        self.range_dropdown.set('7d')
        
        # Update button
        update_btn = ttk.Button(self.controls_frame, text="Update", command=self.update_view)
        update_btn.pack(side='left', padx=5)
        
        # Create main content frame
        content_frame = ttk.Frame(self.frame)
        content_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Charts frame on the left
        self.charts_frame = ttk.Frame(content_frame)
        self.charts_frame.pack(side='left', fill='both', expand=True)
        
        # Details frame on the right
        self.details_frame = ttk.LabelFrame(content_frame, text="Coin Details")
        self.details_frame.pack(side='right', fill='y')

    def update_view(self):
        try:
            print("Starting update_view...")
            
            # Clear existing charts
            for widget in self.charts_frame.winfo_children():
                widget.destroy()
            
            # Create main scrollable canvas
            main_canvas = tk.Canvas(self.charts_frame, bg='#FFFACD')
            scrollbar = ttk.Scrollbar(self.charts_frame, orient="vertical", command=main_canvas.yview)
            
            # Configure the canvas scrolling
            main_canvas.configure(yscrollcommand=scrollbar.set)
            
            # Pack scrollbar and canvas
            scrollbar.pack(side="right", fill="y")
            main_canvas.pack(side="left", fill="both", expand=True)
            
            # Create a frame inside the canvas for the charts
            chart_frame = ttk.Frame(main_canvas)
            
            # Get data and create charts
            df = self.db_manager.get_mentions_data(self.timerange_var.get())
            if df.empty:
                print("No data returned from database")
                return
            
            # Sort coins by total mentions
            sorted_coins = df.groupby('symbol')['mention_count'].sum().sort_values(ascending=False).index
            
            # Calculate grid layout
            n_coins = len(sorted_coins)
            n_cols = 3
            n_rows = (n_coins + n_cols - 1) // n_cols
            
            # Create the figure with proper size
            fig_width = self.frame.winfo_width() * 0.9  # 90% of frame width
            fig_height = 300 * n_rows  # Fixed height per row
            
            fig, colors = self.chart_manager.create_mentions_pie_charts(
                df, sorted_coins, n_rows, n_cols, fig_width, fig_height, chart_frame
            )
            
            # Create and pack the chart
            chart_canvas = FigureCanvasTkAgg(fig, chart_frame)
            chart_widget = chart_canvas.get_tk_widget()
            chart_widget.pack(fill='both', expand=True)
            
            # Create window in canvas that contains the frame
            main_canvas.create_window((0, 0), window=chart_frame, anchor='nw')
            
            # Update scroll region
            chart_frame.bind('<Configure>', lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")))
            
            # Configure mouse wheel scrolling
            def _on_mousewheel(event):
                main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
            main_canvas.bind_all("<MouseWheel>", _on_mousewheel)
            
            # Draw the canvas
            chart_canvas.draw()
            print("Finished update_view successfully")
            
        except Exception as e:
            print(f"Error updating mentions view: {str(e)}")
            import traceback
            traceback.print_exc()

    def show_coin_detail(self, coin):
        """Show detailed information for a selected coin"""
        # Clear previous details
        for widget in self.details_frame.winfo_children():
            widget.destroy()
            
        try:
            price_data, sentiment_data = self.db_manager.get_coin_details(coin)
            
            # Add title
            title = ttk.Label(self.details_frame, text=f"{coin} Details", font=('Helvetica', 12, 'bold'))
            title.pack(pady=10)
            
            if price_data:
                price, volume, change = price_data
                
                # Price info frame
                price_frame = ttk.Frame(self.details_frame)
                price_frame.pack(fill='x', padx=5, pady=5)
                
                ttk.Label(price_frame, text=f"Current Price: ${price:,.2f}").pack()
                
                change_color = 'green' if change > 0 else 'red' if change < 0 else 'black'
                ttk.Label(price_frame, text=f"24h Change: {change:+.2f}%", foreground=change_color).pack()
                
                ttk.Label(price_frame, text=f"24h Volume: ${volume:,.0f}").pack()
            
            if sentiment_data:
                # Sentiment info
                sentiment_frame = ttk.LabelFrame(self.details_frame, text="24h Sentiment")
                sentiment_frame.pack(fill='x', padx=5, pady=5)
                
                total_mentions = sum(row[1] for row in sentiment_data)
                
                for label, count, avg_score in sentiment_data:
                    percentage = (count / total_mentions) * 100
                    ttk.Label(sentiment_frame, 
                             text=f"{label}: {count} ({percentage:.1f}%)").pack()
                             
        except Exception as e:
            print(f"Error showing coin detail: {str(e)}")
            ttk.Label(self.details_frame, text="Error loading details").pack()

    def get_frame(self):
        return self.frame

    def handle_resize(self, event=None):
        """Handle window resize events"""
        if event and event.widget == self.parent:
            if (self.last_width is None or 
                abs(event.width - self.last_width) > 50 or 
                abs(event.height - self.last_height) > 50):
                
                if self.resize_timer:
                    self.parent.after_cancel(self.resize_timer)
                
                self.resize_timer = self.parent.after(500, self.update_view)
                self.last_width = event.width
                self.last_height = event.height
