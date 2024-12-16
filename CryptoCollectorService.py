import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import time
import subprocess
import os
import sys
from datetime import datetime, timedelta
import logging

class CryptoCollectorService(win32serviceutil.ServiceFramework):
    _svc_name_ = "CryptoCollectorService"
    _svc_display_name_ = "Crypto Data Collector Service"
    _svc_description_ = "Runs PriceCollector.py every 2 hours and CollectChat.py every 4 hours"
    _exe_name_ = r"C:\Python312\python.exe"
    _exe_args_ = ""

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.running = True

        # Setup logging
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'crypto_service.log')
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        logging.info("Service initialized")

    def SvcStop(self):
        logging.info("Service stop requested")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.running = False

    def SvcDoRun(self):
        try:
            logging.info("Service starting main loop")
            self.main()
        except Exception as e:
            logging.error(f"Service error in SvcDoRun: {str(e)}")
            self.SvcStop()

    def run_script(self, script_name):
        try:
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name)
            logging.info(f"Running {script_name} from {script_path}")
            
            # Use the full Python path
            process = subprocess.Popen(
                [self._exe_name_, script_path, '--service'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.path.dirname(os.path.abspath(__file__))  # Set working directory
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                logging.info(f"{script_name} completed successfully")
            else:
                logging.error(f"{script_name} failed with error: {stderr.decode()}")
                
        except Exception as e:
            logging.error(f"Error running {script_name}: {str(e)}")

    def main(self):
        logging.info("Service started")
        
        last_price_run = None
        last_chat_run = None
        
        while self.running:
            try:
                current_time = datetime.now()
                
                # Check if it's time to run PriceCollector (every 2 hours)
                if (last_price_run is None or 
                    (current_time - last_price_run).total_seconds() >= 7200):  # 2 hours = 7200 seconds
                    self.run_script('PriceCollector.py')
                    last_price_run = current_time
                
                # Check if it's time to run CollectChat (every 4 hours)
                if (last_chat_run is None or 
                    (current_time - last_chat_run).total_seconds() >= 14400):  # 4 hours = 14400 seconds
                    self.run_script('CollectChat.py')
                    last_chat_run = current_time
                
                # Sleep for 5 minutes before next check
                time.sleep(300)  # 5 minutes = 300 seconds
            except Exception as e:
                logging.error(f"Error in main loop: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(CryptoCollectorService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(CryptoCollectorService) 