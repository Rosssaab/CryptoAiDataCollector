@echo off
echo Starting Crypto Chat Collection: %date% %time%
python C:\PythonApps\CryptoAiAnalyzer\CollectChat.py --service
if errorlevel 1 (
    echo Collection failed with error code %errorlevel%
) else (
    echo Collection completed successfully
)
echo Collection finished: %date% %time%