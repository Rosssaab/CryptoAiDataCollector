import sys
import datetime
import pyodbc
import logging
from textblob import TextBlob
from newsapi import NewsApiClient
from config import DB_CONNECTION_STRING, NEWS_API_KEY

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
        self.init_news_api()
        self.load_sources()

    def init_database(self):
        try:
            self.conn = pyodbc.connect(DB_CONNECTION_STRING)
            self.cursor = self.conn.cursor()
            self.logger.info("Database connected successfully")
        except Exception as e:
            self.logger.error(f"Database connection error: {str(e)}")
            sys.exit(1)

    def init_news_api(self):
        try:
            # Initialize only News API
            self.news_api = NewsApiClient(api_key=NEWS_API_KEY)
            self.logger.info("News API initialized successfully")
        except Exception as e:
            self.logger.error(f"News API initialization error: {str(e)}")
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
            self.logger.info(f"Fetching news for {coin['symbol']}")
            articles = self.news_api.get_everything(
                q=f"{coin['symbol']} OR {coin['full_name']}",
                language='en',
                sort_by='publishedAt',
                from_param=(datetime.datetime.now() - datetime.timedelta(days=1)).date().isoformat()
            )
            
            for article in articles['articles']:
                mentions.append({
                    'source_id': self.sources['News'],
                    'content': article['title'] + " " + (article['description'] or ""),
                    'url': article['url']
                })
                self.logger.info(f"Found article: {article['title']}")
        except Exception as e:
            self.logger.error(f"News API error for {coin['symbol']}: {str(e)}")
        
        return mentions

    def save_mentions(self, coin_id, mentions):
        current_time = datetime.datetime.now()
        
        for mention in mentions:
            try:
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
                
            except Exception as e:
                self.logger.error(f"Error saving mention: {str(e)}")

    def collect_chat_data(self):
        try:
            self.cursor.execute("SELECT coin_id, symbol, full_name FROM Coins")
            coins = [{'id': row[0], 'symbol': row[1], 'full_name': row[2]} 
                    for row in self.cursor.fetchall()]
            
            for coin in coins:
                self.logger.info(f"Collecting news mentions for {coin['symbol']}")
                mentions = self.collect_news_mentions(coin)
                self.logger.info(f"Found {len(mentions)} news mentions for {coin['symbol']}")
                self.save_mentions(coin['id'], mentions)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error in chat collection: {str(e)}")
            return False

def main():
    collector = ChatCollector()
    success = collector.collect_chat_data()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()