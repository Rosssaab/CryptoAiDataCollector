import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import time
from PriceCollector import CryptoCollector
import logging

class CryptoCollectorService(win32serviceutil.ServiceFramework):
    _svc_name_ = "CryptoCollectorService"
    _svc_display_name_ = "Crypto Price Collector Service"
    _svc_description_ = "Collects cryptocurrency price data from various sources"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.collector = None
        self.logger = self._setup_logging()

    def _setup_logging(self):
        logger = logging.getLogger('CryptoCollectorService')
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler('crypto_service.log')
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        return logger

    def SvcStop(self):
        self.logger.info('Service stop requested')
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        self.logger.info('Service starting')
        try:
            self.collector = CryptoCollector()
            while True:
                # Check if service is being stopped
                if win32event.WaitForSingleObject(self.stop_event, 100) == win32event.WAIT_OBJECT_0:
                    break
                
                try:
                    # Run one collection cycle
                    self.collector.collect_data_once()
                    self.logger.info('Collection cycle completed')
                except Exception as e:
                    self.logger.error(f'Error in collection cycle: {str(e)}')
                
                # Wait for 5 minutes before next collection
                time.sleep(300)  # 5 minutes
                
        except Exception as e:
            self.logger.error(f'Service error: {str(e)}')
            servicemanager.LogErrorMsg(str(e))

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(CryptoCollectorService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(CryptoCollectorService)