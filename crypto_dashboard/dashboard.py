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
        
        # Initialize managers
        self.db_manager = DatabaseManager()
        self.chart_manager = ChartManager()
        
        # Apply a modern theme
        self.setup_styles()
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Initialize tabs
        self.mentions_tab = MentionsTab(self.notebook, self.db_manager, self.chart_manager)
        self.price_tab = PriceTab(self.notebook, self.db_manager, self.chart_manager)
        self.sentiment_tab = SentimentTab(self.notebook, self.db_manager, self.chart_manager)
        
        # Add tabs to notebook
        self.notebook.add(self.mentions_tab.get_frame(), text='Mentions Overview')
        self.notebook.add(self.price_tab.get_frame(), text='Price Analysis')
        self.notebook.add(self.sentiment_tab.get_frame(), text='Sentiment Analysis')
        
        # Create loading indicator
        self.setup_loading_indicator()
        
        # Add window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_styles(self):
        """Configure the application's visual styles"""
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
        style.configure("Mentions.TFrame", background="#FFFACD")
        
        # Configure the root window color
        self.root.configure(bg="#2B2B2B")

    def setup_loading_indicator(self):
        """Setup the loading indicator"""
        style = ttk.Style()
        style.configure('Loading.TLabel', 
                       font=('Helvetica', 14, 'bold'),
                       background='#2B2B2B',
                       foreground='white')
        
        self.loading_label = ttk.Label(self.root, text="Loading...", style='Loading.TLabel')
        self.loading_label.place(relx=0.5, rely=0.5, anchor='center')
        self.loading_label.place_forget()

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

    def on_closing(self):
        """Handle cleanup when window is closed"""
        try:
            # Close all matplotlib figures
            import matplotlib.pyplot as plt
            plt.close('all')
            
            # Destroy the root window
            self.root.destroy()
            
            # Quit the application
            self.root.quit()
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

    def run(self):
        """Start the application"""
        self.root.mainloop()
