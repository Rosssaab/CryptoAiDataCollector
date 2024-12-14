-- Create Coins table
CREATE TABLE Coins (
    coin_id INT IDENTITY(1,1) PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    full_name VARCHAR(100),
    created_at DATETIME DEFAULT GETDATE()
);

-- Create price_data table
CREATE TABLE price_data (
    price_id INT IDENTITY(1,1) PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    coin_id INT NOT NULL,
    price_usd DECIMAL(18,8) NOT NULL,
    volume_24h DECIMAL(24,8),
    price_change_24h DECIMAL(10,2),
    data_source VARCHAR(20),
    FOREIGN KEY (coin_id) REFERENCES Coins(coin_id)
);

-- Create indexes for better performance
CREATE INDEX idx_price_data_timestamp ON price_data(timestamp);
CREATE INDEX idx_price_data_coin_id ON price_data(coin_id);
CREATE INDEX idx_coins_symbol ON Coins(symbol); 