import tkinter as tk
from tkinter import ttk
from utils.database import DatabaseManager
from utils.chart_utils import ChartManager
from tab_managers.mentions_tab import MentionsTab
from tab_managers.price_tab import PriceTab
from tab_managers.sentiment_tab import SentimentTab

class Dashboard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Crypto Analytics Dashboard")
        
        # Set initial window size to 1024px wide
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
        
        # Initialize managers
        self.db_manager = DatabaseManager()
        self.chart_manager = ChartManager()
        
        # Apply a modern theme
        self.setup_styles()
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create tabs
        self.mentions_tab = MentionsTab(self.notebook, self.db_manager, self.chart_manager, self.notebook)
        self.price_tab = PriceTab(self.notebook, self.db_manager, self.chart_manager)
        self.sentiment_tab = SentimentTab(self.notebook, self.db_manager, self.chart_manager)
        
        # Add tabs to notebook
        self.notebook.add(self.mentions_tab.get_frame(), text='Mentions')
        self.notebook.add(self.price_tab.get_frame(), text='Price')
        self.notebook.add(self.sentiment_tab.get_frame(), text='Sentiment')
        
        # Connect tabs
        self.mentions_tab.set_tab_references(self.price_tab, self.sentiment_tab)
        
        # Set up closing handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Create loading indicator
        self.setup_loading_indicator()

    def setup_styles(self):
        """Set up custom styles for the application"""
        style = ttk.Style()
        style.configure('Mentions.TFrame', background='#FFFACD')
        style.configure('Price.TFrame', background='#E6E6FA')
        style.configure('Sentiment.TFrame', background='#98FB98')
        
        style.configure('Loading.TLabel', 
                       font=('Helvetica', 14, 'bold'),
                       background='#2B2B2B',
                       foreground='white')

    def setup_loading_indicator(self):
        """Set up the loading indicator"""
        self.loading_label = ttk.Label(self.root, text="Loading...", style='Loading.TLabel')
        self.loading_label.place(relx=0.5, rely=0.5, anchor='center')
        self.loading_label.place_forget()

    def show_loading(self):
        """Show the loading indicator safely"""
        if self.root.winfo_exists():
            self.loading_label.place(relx=0.5, rely=0.5, anchor='center')
            self.root.update_idletasks()

    def hide_loading(self):
        """Hide the loading indicator safely"""
        if self.root.winfo_exists():
            self.loading_label.place_forget()
            self.root.update_idletasks()

    def on_closing(self):
        """Handle cleanup when window is closed"""
        try:
            import matplotlib.pyplot as plt
            plt.close('all')
            self.root.destroy()
            self.root.quit()
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

    def run(self):
        """Start the application"""
        self.root.mainloop()
