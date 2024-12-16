import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class ChartManager:
    @staticmethod
    def create_price_charts(df, coin, frame):
        """Create price and volume charts"""
        plt.close('all')
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
        canvas = FigureCanvasTkAgg(fig, frame)
        canvas.draw()
        return canvas

    @staticmethod
    def create_sentiment_charts(df, coin, frame):
        """Create sentiment distribution charts"""
        plt.close('all')
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
        canvas = FigureCanvasTkAgg(fig, frame)
        canvas.draw()
        return canvas

    @staticmethod
    def create_mentions_pie_charts(df, sorted_coins, n_rows, n_cols, current_width, current_height, scrollable_frame):
        """Create pie charts for mentions view"""
        plt.close('all')
        
        # Create figure with fixed size per chart
        fig = plt.figure(figsize=(15, n_rows * 5))  # Fixed width, height scales with rows
        plt.subplots_adjust(hspace=0.5, wspace=0.3)
        
        colors = {
            'Positive': '#00ff00',     # Bright green
            'Very Positive': '#008000', # Dark green
            'Neutral': '#808080',      # Grey
            'Negative': '#ff0000',     # Bright red
            'Very Negative': '#800000'  # Dark red
        }
        
        # Create a pie chart for each coin
        for idx, coin in enumerate(sorted_coins):
            ax = fig.add_subplot(n_rows, n_cols, idx + 1)
            
            # Get data for this coin
            coin_data = df[df['symbol'] == coin].groupby('sentiment_label')['mention_count'].sum()
            
            if not coin_data.empty:
                # Create color list for this pie
                chart_colors = [colors.get(label, '#CCCCCC') for label in coin_data.index]
                
                # Create pie chart without labels, only percentages
                wedges, _, autotexts = ax.pie(coin_data.values, 
                                           labels=None,  # Remove labels
                                           colors=chart_colors,
                                           autopct='%1.1f%%',
                                           pctdistance=0.85)
                
                # Set title
                ax.set_title(f"{coin}\nTotal: {coin_data.sum()}", fontsize=12, pad=10)
                
                # Make the percentage labels larger
                plt.setp(autotexts, size=10, weight="bold")
        
        plt.tight_layout()
        return fig, colors
