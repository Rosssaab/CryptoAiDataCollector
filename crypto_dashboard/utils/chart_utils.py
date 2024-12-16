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
        
        # Define consistent colors for sentiment
        colors = {
            'Positive': '#00ff00',      # Green
            'Very Positive': '#008000',  # Dark Green
            'Neutral': '#808080',       # Gray
            'Negative': '#ff0000',      # Red
            'Very Negative': '#800000'   # Dark Red
        }
        
        # Sentiment over time
        ax1 = fig.add_subplot(211)
        pivot_df = df.pivot(index='date', columns='sentiment_label', values='count').fillna(0)
        pivot_df.plot(kind='bar', stacked=True, ax=ax1, 
                     color=[colors.get(x, '#CCCCCC') for x in pivot_df.columns])
        ax1.set_title(f'{coin} Sentiment Distribution Over Time')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Number of Mentions')
        plt.xticks(rotation=45)
        
        # Pie chart of total sentiment distribution
        ax2 = fig.add_subplot(212)
        sentiment_totals = df.groupby('sentiment_label')['count'].sum()
        pie_colors = [colors.get(label, '#CCCCCC') for label in sentiment_totals.index]
        ax2.pie(sentiment_totals, labels=sentiment_totals.index, autopct='%1.1f%%', colors=pie_colors)
        ax2.set_title('Overall Sentiment Distribution')
        
        plt.tight_layout()
        
        # Embed chart in tkinter
        canvas = FigureCanvasTkAgg(fig, frame)
        canvas.draw()
        return canvas

    @staticmethod
    def create_mentions_pie_charts(df, sorted_coins, n_rows, n_cols, current_width, current_height, scrollable_frame, click_handler=None):
        """Create pie charts for mentions view"""
        plt.close('all')
        
        # Create figure with fixed size per chart
        fig = plt.figure(figsize=(15, n_rows * 5))
        plt.subplots_adjust(hspace=0.5, wspace=0.3)
        
        colors = {
            'Positive': '#00ff00',
            'Very Positive': '#008000',
            'Neutral': '#808080',
            'Negative': '#ff0000',
            'Very Negative': '#800000'
        }
        
        # Calculate total positive sentiment percentage for each coin
        coin_sentiments = {}
        for coin in sorted_coins:
            coin_data = df[df['symbol'] == coin].groupby('sentiment_label')['mention_count'].sum()
            total_mentions = coin_data.sum()
            positive_mentions = coin_data.get('Positive', 0) + coin_data.get('Very Positive', 0)
            positive_percentage = (positive_mentions / total_mentions * 100) if total_mentions > 0 else 0
            coin_sentiments[coin] = positive_percentage
        
        # Sort coins by positive sentiment percentage
        sorted_coins_by_sentiment = sorted(coin_sentiments.items(), key=lambda x: x[1], reverse=True)
        
        # Store axes and their associated coins
        axes_coins = {}
        
        # Create a pie chart for each coin
        for idx, (coin, sentiment_pct) in enumerate(sorted_coins_by_sentiment):
            ax = fig.add_subplot(n_rows, n_cols, idx + 1)
            axes_coins[ax] = coin  # Store the coin for this axis
            
            # Get data for this coin
            coin_data = df[df['symbol'] == coin].groupby('sentiment_label')['mention_count'].sum()
            
            if not coin_data.empty:
                chart_colors = [colors.get(label, '#CCCCCC') for label in coin_data.index]
                
                wedges, _, autotexts = ax.pie(coin_data.values, 
                                           labels=None,
                                           colors=chart_colors,
                                           autopct='%1.1f%%',
                                           pctdistance=0.85)
                
                ax.set_title(f"{coin}\nTotal: {coin_data.sum()}", 
                            fontsize=12, pad=10)
                
                plt.setp(autotexts, size=10, weight="bold")
                
                # Add click event handler for mouse clicks only
                if click_handler:
                    # Create closure to store last click time
                    last_click_time = [0]  # Use list to store mutable value
                    
                    def handle_pick(event):
                        if event.mouseevent.button == 1:  # Left click only
                            # Get current time
                            current_time = event.mouseevent.guiEvent.time
                            
                            # If less than 1000ms since last click, ignore
                            if current_time - last_click_time[0] < 1000:
                                return
                                
                            # Update last click time
                            last_click_time[0] = current_time
                            
                            # Get the axis that was clicked
                            ax = event.artist.axes
                            # Get the coin associated with this axis
                            clicked_coin = axes_coins.get(ax)
                            if clicked_coin:
                                click_handler(clicked_coin)
                    
                    for wedge in wedges:
                        wedge.set_picker(5)  # 5 points tolerance
                    fig.canvas.mpl_connect('pick_event', handle_pick)
        
        plt.tight_layout()
        return fig, colors
