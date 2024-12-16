echo Starting Crypto Data Collection: %date% %time%
python C:\PythonApps\CryptoAiAnalyzer\PriceCollector.py --service
if errorlevel 1 (
    echo Collection failed with error code %errorlevel%
) else (
    echo Collection completed successfully
)
echo Collection finished: %date% %time%
