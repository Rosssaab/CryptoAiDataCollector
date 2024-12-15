import sys
import datetime
import pyodbc
import logging
from textblob import TextBlob
from newsapi import NewsApiClient
import praw
from config import DB_CONNECTION_STRING, NEWS_API_KEY, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import webbrowser

def setup_logging():
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler('crypto_chat.log')
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger = logging.getLogger('ChatCollector')
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

class ChatCollector:
    def __init__(self):
        self.logger = setup_logging()
        self.init_database()
        self.init_apis()
        self.load_sources()

    def init_database(self):
        try:
            self.conn = pyodbc.connect(DB_CONNECTION_STRING)
            self.cursor = self.conn.cursor()
            self.logger.info("Database connected successfully")
        except Exception as e:
            self.logger.error(f"Database connection error: {str(e)}")
            sys.exit(1)

    def init_apis(self):
        try:
            # Initialize News API
            self.news_api = NewsApiClient(api_key=NEWS_API_KEY)
            self.logger.info("News API initialized successfully")

            # Initialize Reddit API
            self.reddit = praw.Reddit(
                client_id=REDDIT_CLIENT_ID,
                client_secret=REDDIT_CLIENT_SECRET,
                user_agent="CryptoSentimentBot/1.0"
            )
            self.logger.info("Reddit API initialized successfully")
            
        except Exception as e:
            self.logger.error(f"API initialization error: {str(e)}")
            sys.exit(1)

    def load_sources(self):
        try:
            self.cursor.execute("SELECT source_id, source_name FROM chat_source")
            self.sources = {row[1]: row[0] for row in self.cursor.fetchall()}
            self.logger.info(f"Loaded {len(self.sources)} chat sources")
        except Exception as e:
            self.logger.error(f"Error loading chat sources: {str(e)}")
            sys.exit(1)

    def analyze_sentiment(self, text):
        try:
            analysis = TextBlob(text)
            score = analysis.sentiment.polarity
            if score > 0:
                label = 'Positive'
            elif score < 0:
                label = 'Negative'
            else:
                label = 'Neutral'
            return score, label
        except Exception as e:
            self.logger.error(f"Sentiment analysis error: {str(e)}")
            return 0, 'Neutral'

    def collect_news_mentions(self, coin):
        mentions = []
        try:
            # Check if we should skip this coin based on API limits
            if hasattr(self, '_news_api_requests'):
                if self._news_api_requests >= 95:  # Leave some buffer
                    self.logger.warning("Approaching News API daily limit, skipping remaining coins")
                    return mentions
            else:
                self._news_api_requests = 0
                
            self.logger.info(f"Fetching news for {coin['symbol']} (Request #{self._news_api_requests + 1})")
            
            # Add delay between requests
            time.sleep(1)  # 1 second delay between requests
            
            articles = self.news_api.get_everything(
                q=f"{coin['symbol']} OR {coin['full_name']}",
                language='en',
                sort_by='publishedAt',
                from_param=(datetime.datetime.now() - datetime.timedelta(days=1)).date().isoformat()
            )
            
            if articles.get('status') != 'ok':
                self.logger.error(f"News API error: {articles.get('message', 'Unknown error')}")
                return mentions

            self._news_api_requests += 1
            
            for article in articles['articles']:
                if not article.get('url'):
                    self.logger.warning(f"Skipping article without URL for {coin['symbol']}")
                    continue
                    
                content = article.get('title', '') + " " + (article.get('description') or "")
                if not content.strip():
                    self.logger.warning(f"Skipping empty article for {coin['symbol']}")
                    continue

                mentions.append({
                    'source_id': self.sources['News'],
                    'content': content,
                    'url': article['url']
                })
                self.logger.info(f"Found article: {article.get('title', 'No title')}")
                
        except Exception as e:
            if 'rateLimited' in str(e):
                self.logger.warning("News API rate limit reached, switching to Reddit only")
                self._news_api_requests = 100  # Mark as limit reached
            else:
                self.logger.error(f"News API error for {coin['symbol']}: {str(e)}")
        
        return mentions

    def collect_reddit_mentions(self, coin):
        mentions = []
        # Only use main crypto subreddits for small coins to avoid 404s
        if len(coin['symbol']) <= 3:  # For short symbols like 'OM'
            subreddits = ['cryptocurrency', 'CryptoMarkets']
        else:
            subreddits = ['cryptocurrency', 'CryptoMarkets', coin['symbol'].lower()]
        
        for subreddit in subreddits:
            try:
                self.logger.info(f"Searching Reddit r/{subreddit} for {coin['symbol']}")
                
                try:
                    subreddit_obj = self.reddit.subreddit(subreddit)
                    # Test if subreddit exists and is accessible
                    subreddit_obj.id
                except Exception as e:
                    self.logger.warning(f"Skipping inaccessible subreddit r/{subreddit}: {str(e)}")
                    continue  # Skip to next subreddit without stopping

                # Add error handling for the search
                try:
                    search_results = subreddit_obj.search(
                        f"{coin['symbol']} OR {coin['full_name']}", 
                        time_filter='day',
                        limit=100
                    )
                    
                    for post in search_results:
                        if not post.selftext and not post.title:
                            continue
                            
                        content = f"Title: {post.title}\nContent: {post.selftext}"
                        if len(content.strip()) < 10:  # Skip very short posts
                            continue

                        mentions.append({
                            'source_id': self.sources['Reddit'],
                            'content': content,
                            'url': f"https://reddit.com{post.permalink}"
                        })
                        self.logger.info(f"Found Reddit post: {post.title}")

                except Exception as search_error:
                    self.logger.warning(f"Search failed for r/{subreddit}: {str(search_error)}")
                    continue  # Continue with next subreddit

            except Exception as e:
                self.logger.error(f"Reddit error for {subreddit}/{coin['symbol']}: {str(e)}")
                continue  # Continue with next subreddit
        
        return mentions

    def save_mentions(self, coin_id, mentions):
        current_time = datetime.datetime.now()
        saved_count = 0
        skipped_count = 0
        error_count = 0
        
        for mention in mentions:
            try:
                # Validate required fields
                if not all(key in mention for key in ['source_id', 'content', 'url']):
                    self.logger.error(f"Missing required fields in mention for coin_id {coin_id}")
                    error_count += 1
                    continue

                # Check for duplicates
                self.cursor.execute('''
                    SELECT chat_id FROM chat_data 
                    WHERE coin_id = ? AND url = ? 
                    AND DATEDIFF(hour, timestamp, ?) < 24
                ''', (coin_id, mention['url'], current_time))
                
                if self.cursor.fetchone():
                    self.logger.info(f"Skipping duplicate mention: {mention['url']}")
                    skipped_count += 1
                    continue
                
                # Validate content length
                if len(mention['content']) > 4000:  # SQL Server text limit
                    mention['content'] = mention['content'][:4000]
                    self.logger.warning(f"Truncated long content for {mention['url']}")

                score, label = self.analyze_sentiment(mention['content'])
                
                self.cursor.execute('''
                    INSERT INTO chat_data (
                        timestamp, coin_id, source_id, content,
                        sentiment_score, sentiment_label, url
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    current_time, coin_id, mention['source_id'],
                    mention['content'], score, label, mention['url']
                ))
                self.conn.commit()
                saved_count += 1
                
            except Exception as e:
                self.logger.error(f"Error saving mention: {str(e)}")
                error_count += 1

        self.logger.info(f"Coin {coin_id} summary: Saved {saved_count}, Skipped {skipped_count}, Errors {error_count}")
        return saved_count > 0

    def collect_chat_data(self):
        try:
            # Reset counters if it's a new day
            current_hour = datetime.datetime.now().hour
            if current_hour == 0 and hasattr(self, '_last_reset_hour'):
                if self._last_reset_hour != 0:
                    self.reset_api_counters()
            self._last_reset_hour = current_hour

            # Verify database connection
            try:
                self.cursor.execute("SELECT 1")
            except Exception as e:
                self.logger.error("Database connection lost, attempting to reconnect")
                self.init_database()

            # Changed query to not use market_cap
            self.cursor.execute("""
                SELECT coin_id, symbol, full_name 
                FROM Coins 
                ORDER BY coin_id
            """)
            
            coins = [{'id': row[0], 'symbol': row[1], 'full_name': row[2]} 
                    for row in self.cursor.fetchall()]
            
            if not coins:
                self.logger.error("No coins found in database")
                return False

            total_mentions = 0
            for coin in coins:
                self.logger.info(f"Collecting mentions for {coin['symbol']}")
                
                mentions = []
                
                # Only collect news if we haven't hit the limit
                if not hasattr(self, '_news_api_requests') or self._news_api_requests < 95:
                    news_mentions = self.collect_news_mentions(coin)
                    self.logger.info(f"Found {len(news_mentions)} news mentions for {coin['symbol']}")
                    mentions.extend(news_mentions)
                
                reddit_mentions = self.collect_reddit_mentions(coin)
                self.logger.info(f"Found {len(reddit_mentions)} Reddit mentions for {coin['symbol']}")
                mentions.extend(reddit_mentions)
                
                if mentions:
                    self.save_mentions(coin['id'], mentions)
                    total_mentions += len(mentions)
                
            self.logger.info(f"Collection completed. Total mentions: {total_mentions}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in chat collection: {str(e)}")
            return False

class ChatCollectorGUI(ChatCollector):
    def __init__(self):
        super().__init__()
        self.root = tk.Tk()
        self.root.title("Crypto Chat Collector")
        self.is_collecting = False
        self.create_gui()
        self.setup_tree_bindings()

    def setup_tree_bindings(self):
        self.tree.bind('<Double-1>', self.on_tree_double_click)
        self.tree.bind('<Return>', self.on_tree_double_click)

    def on_tree_double_click(self, event):
        # Get selected item
        selected_item = self.tree.selection()
        if not selected_item:
            return
            
        # Get the URL from the selected row (URL is the last column)
        item_values = self.tree.item(selected_item[0])['values']
        if item_values and len(item_values) >= 5:  # Make sure we have all columns
            url = item_values[4]  # URL is the 5th column
            try:
                webbrowser.open(url)  # This opens the system's default browser
            except Exception as e:
                self.logger.error(f"Error opening URL: {str(e)}")
                messagebox.showerror("Error", f"Could not open URL: {str(e)}")

    def create_gui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Control frame for buttons and filters
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        # Left side: Buttons and status
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        # Collection button
        self.collect_button = ttk.Button(
            button_frame, 
            text="Start Collection",
            width=15,
            command=self.toggle_collection
        )
        self.collect_button.pack(side=tk.LEFT, padx=5)
        
        # Load History button - make sure it's visible
        self.load_button = ttk.Button(
            button_frame, 
            text="Load History",
            width=15,
            command=self.load_history
        )
        self.load_button.pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = ttk.Label(button_frame, text="Ready", width=30)
        self.status_label.pack(side=tk.LEFT, padx=10)

        # Right side: Filters
        filter_frame = ttk.Frame(control_frame)
        filter_frame.pack(side=tk.RIGHT)

        # Source filter
        ttk.Label(filter_frame, text="Source:").pack(side=tk.LEFT, padx=(0, 5))
        self.source_var = tk.StringVar(value="All")
        self.source_filter = ttk.Combobox(
            filter_frame, 
            textvariable=self.source_var,
            values=["All", "News", "Reddit"],
            width=10,
            state="readonly"
        )
        self.source_filter.pack(side=tk.LEFT, padx=(0, 20))
        self.source_filter.bind('<<ComboboxSelected>>', self.apply_filters)

        # Coin filter
        ttk.Label(filter_frame, text="Coin:").pack(side=tk.LEFT, padx=(0, 5))
        self.coin_var = tk.StringVar(value="All")
        self.coin_filter = ttk.Combobox(
            filter_frame, 
            textvariable=self.coin_var,
            width=10,
            state="readonly"
        )
        self.coin_filter.pack(side=tk.LEFT)
        self.coin_filter.bind('<<ComboboxSelected>>', self.apply_filters)
        
        # Update coin filter with available coins
        self.update_coin_filter()

        # Results treeview
        self.tree = ttk.Treeview(main_frame, columns=(
            "timestamp", "coin", "source", "sentiment", "url"
        ), show="headings")

        # Configure columns
        self.tree.heading("timestamp", text="Time")
        self.tree.heading("coin", text="Coin")
        self.tree.heading("source", text="Source")
        self.tree.heading("sentiment", text="Sentiment")
        self.tree.heading("url", text="URL")

        self.tree.column("timestamp", width=150)
        self.tree.column("coin", width=100)
        self.tree.column("source", width=100)
        self.tree.column("sentiment", width=100)
        self.tree.column("url", width=300)

        self.tree.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=1, column=2, sticky=(tk.N, tk.S))
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Stats frame
        stats_frame = ttk.LabelFrame(main_frame, text="Collection Statistics", padding="5")
        stats_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        # Stats labels
        self.stats_labels = {
            'total': ttk.Label(stats_frame, text="Total Mentions: 0"),
            'news': ttk.Label(stats_frame, text="News Articles: 0"),
            'reddit': ttk.Label(stats_frame, text="Reddit Posts: 0"),
            'sentiment': ttk.Label(stats_frame, text="Avg Sentiment: 0.00")
        }

        for i, label in enumerate(self.stats_labels.values()):
            label.grid(row=0, column=i, padx=10)

        # Help label
        help_label = ttk.Label(
            main_frame, 
            text="Double-click or press Enter on a row to open the article",
            font=('Helvetica', 9, 'italic')
        )
        help_label.grid(row=3, column=0, columnspan=3, pady=(5,0))

    def update_coin_filter(self):
        try:
            self.cursor.execute("SELECT DISTINCT symbol FROM Coins ORDER BY symbol")
            coins = ["All"] + [row[0] for row in self.cursor.fetchall()]
            self.coin_filter['values'] = coins
        except Exception as e:
            self.logger.error(f"Error updating coin filter: {str(e)}")
            self.coin_filter['values'] = ["All"]

    def apply_filters(self, event=None):
        try:
            self.status_label.config(text="Applying filters...")
            self.tree.delete(*self.tree.get_children())  # Clear current items
            
            # Build query based on filters
            query = """
                SELECT TOP 100
                    cd.timestamp,
                    c.symbol,
                    cs.source_name,
                    cd.sentiment_score,
                    cd.sentiment_label,
                    cd.url
                FROM chat_data cd
                JOIN Coins c ON cd.coin_id = c.coin_id
                JOIN chat_source cs ON cd.source_id = cs.source_id
                WHERE 1=1
            """
            params = []
            
            # Apply source filter
            if self.source_var.get() != "All":
                query += " AND cs.source_name = ?"
                params.append(self.source_var.get())
                
            # Apply coin filter
            if self.coin_var.get() != "All":
                query += " AND c.symbol = ?"
                params.append(self.coin_var.get())
                
            query += " ORDER BY cd.timestamp DESC"
            
            # Execute query with filters
            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()
            
            # Populate tree with filtered results
            for row in rows:
                self.tree.insert("", "end", values=(
                    row[0].strftime('%Y-%m-%d %H:%M:%S'),
                    row[1],  # symbol
                    row[2],  # source_name
                    f"{row[4]} ({row[3]:.2f})",  # sentiment_label (sentiment_score)
                    row[5]   # url
                ))
                
            # Update statistics for filtered results
            news_count = sum(1 for item in self.tree.get_children() 
                            if self.tree.item(item)['values'][2] == 'News')
            reddit_count = sum(1 for item in self.tree.get_children() 
                              if self.tree.item(item)['values'][2] == 'Reddit')
            
            if rows:
                total_sentiment = sum(float(self.tree.item(item)['values'][3].split('(')[1].strip(')'))
                                     for item in self.tree.get_children())
                avg_sentiment = total_sentiment / len(rows)
            else:
                avg_sentiment = 0
            
            self.update_stats(news_count, reddit_count, avg_sentiment)
            
            self.status_label.config(text=f"Showing {len(rows)} records")
            
        except Exception as e:
            self.logger.error(f"Error applying filters: {str(e)}")
            messagebox.showerror("Error", f"Failed to apply filters: {str(e)}")
            self.status_label.config(text="Error applying filters")

    def add_mention(self, coin_symbol, source, sentiment_score, sentiment_label, url):
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        item = self.tree.insert("", "end", values=(
            timestamp,
            coin_symbol,
            source,
            f"{sentiment_label} ({sentiment_score:.2f})",
            url
        ))
        
        # Apply current filters to new item
        self.apply_filters()
        
        # Keep only last 100 items
        items = self.tree.get_children()
        if len(items) > 100:
            self.tree.delete(items[0])

    def update_stats(self, news_count, reddit_count, sentiment_avg):
        total = news_count + reddit_count
        self.stats_labels['total'].config(text=f"Total Mentions: {total}")
        self.stats_labels['news'].config(text=f"News Articles: {news_count}")
        self.stats_labels['reddit'].config(text=f"Reddit Posts: {reddit_count}")
        self.stats_labels['sentiment'].config(text=f"Avg Sentiment: {sentiment_avg:.2f}")

    def toggle_collection(self):
        if not self.is_collecting:
            self.is_collecting = True
            self.collect_button.config(text="Stop Collection")
            self.collection_thread = threading.Thread(target=self.collect_with_gui_updates)
            self.collection_thread.daemon = True
            self.collection_thread.start()
        else:
            self.is_collecting = False
            self.collect_button.config(text="Start Collection")

    def collect_with_gui_updates(self):
        while self.is_collecting:
            try:
                self.status_label.config(text="Starting collection...")
                self.tree.delete(*self.tree.get_children())  # Clear previous items
                news_count = 0
                reddit_count = 0
                total_sentiment = 0
                mention_count = 0

                self.cursor.execute("""
                    SELECT coin_id, symbol, full_name 
                    FROM Coins 
                    ORDER BY coin_id
                """)
                
                coins = [{'id': row[0], 'symbol': row[1], 'full_name': row[2]} 
                        for row in self.cursor.fetchall()]

                for coin in coins:
                    if not self.is_collecting:  # Check if stopped
                        break
                    
                    self.status_label.config(text=f"Collecting {coin['symbol']}...")
                    
                    if not hasattr(self, '_news_api_requests') or self._news_api_requests < 95:
                        news_mentions = self.collect_news_mentions(coin)
                        for mention in news_mentions:
                            score, label = self.analyze_sentiment(mention['content'])
                            self.add_mention(coin['symbol'], 'News', score, label, mention['url'])
                            total_sentiment += score
                            news_count += 1
                            mention_count += 1

                    reddit_mentions = self.collect_reddit_mentions(coin)
                    for mention in reddit_mentions:
                        score, label = self.analyze_sentiment(mention['content'])
                        self.add_mention(coin['symbol'], 'Reddit', score, label, mention['url'])
                        total_sentiment += score
                        reddit_count += 1
                        mention_count += 1

                # Update final stats
                avg_sentiment = total_sentiment / mention_count if mention_count > 0 else 0
                self.update_stats(news_count, reddit_count, avg_sentiment)
                
                collection_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if self.is_collecting:  # Only show "waiting" if not manually stopped
                    self.status_label.config(text=f"Last collection: {collection_time}. Waiting for next run...")
                else:
                    self.status_label.config(text=f"Collection stopped at {collection_time}")
                
                # Wait for an hour if still collecting
                for _ in range(3600):
                    if not self.is_collecting:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"GUI collection error: {str(e)}")
                messagebox.showerror("Error", f"Collection failed: {str(e)}")
                self.is_collecting = False
                self.collect_button.config(text="Start Collection")
                self.status_label.config(text="Collection failed!")
                break
            
        # Make sure button text is reset when collection stops
        self.collect_button.config(text="Start Collection")
        if self.status_label.cget("text") != "Collection failed!":
            self.status_label.config(text="Collection stopped")

    def load_history(self):
        try:
            self.status_label.config(text="Loading history...")
            self.tree.delete(*self.tree.get_children())  # Clear current items
            
            # Build query based on filters - using TOP instead of LIMIT for SQL Server
            query = """
                SELECT TOP 100
                    cd.timestamp,
                    c.symbol,
                    cs.source_name,
                    cd.sentiment_score,
                    cd.sentiment_label,
                    cd.url
                FROM chat_data cd
                JOIN Coins c ON cd.coin_id = c.coin_id
                JOIN chat_source cs ON cd.source_id = cs.source_id
                WHERE 1=1
            """
            params = []
            
            if self.coin_var.get() != "All":
                query += " AND c.symbol = ?"
                params.append(self.coin_var.get())
                
            if self.source_var.get() != "All":
                query += " AND cs.source_name = ?"
                params.append(self.source_var.get())
                
            query += " ORDER BY cd.timestamp DESC"  # Removed LIMIT, using TOP instead
            
            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()
            
            for row in rows:
                self.tree.insert("", "end", values=(
                    row[0].strftime('%Y-%m-%d %H:%M:%S'),
                    row[1],  # symbol
                    row[2],  # source_name
                    f"{row[4]} ({row[3]:.2f})",  # sentiment_label (sentiment_score)
                    row[5]   # url
                ))
                
            self.status_label.config(text=f"Loaded {len(rows)} records")
            
            # Update statistics
            news_count = sum(1 for item in self.tree.get_children() 
                            if self.tree.item(item)['values'][2] == 'News')
            reddit_count = sum(1 for item in self.tree.get_children() 
                              if self.tree.item(item)['values'][2] == 'Reddit')
            
            total_sentiment = sum(float(self.tree.item(item)['values'][3].split('(')[1].strip(')'))
                                 for item in self.tree.get_children())
            avg_sentiment = total_sentiment / len(rows) if rows else 0
            
            self.update_stats(news_count, reddit_count, avg_sentiment)
            
        except Exception as e:
            self.logger.error(f"Error loading history: {str(e)}")
            messagebox.showerror("Error", f"Failed to load history: {str(e)}")
            self.status_label.config(text="Error loading history")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--service':
        # Run in service mode
        collector = ChatCollector()
        while True:
            collector.collect_chat_data()
            time.sleep(3600)  # Wait for 1 hour
    else:
        # Run in GUI mode
        app = ChatCollectorGUI()
        app.root.mainloop()

if __name__ == "__main__":
    main()