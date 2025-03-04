import servicemanager
import win32service
import win32event
import win32serviceutil
import socket
from phantom_agent import RMMAgent  # Your main agent class

class RMMAgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = "RMMAgent"
    _svc_display_name_ = "RMM Client Agent"
    _svc_description_ = "Remote Monitoring and Management Client Service"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.agent = RMMAgent()

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.agent.running = False

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()

    def main(self):
        self.agent.check_in()