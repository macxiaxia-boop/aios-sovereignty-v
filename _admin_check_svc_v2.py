import ctypes, ctypes.wintypes as w, sys, os
advapi32 = ctypes.windll.advapi32
kernel32 = ctypes.windll.kernel32

SC_MANAGER_ALL_ACCESS = 0xF003F
SERVICE_QUERY_CONFIG = 0x0001

OpenSCManager = advapi32.OpenSCManagerW
OpenSCManager.restype = w.LPCVOID
OpenSCManager.argtypes = [w.LPCWSTR, w.LPCWSTR, w.DWORD]

OpenService = advapi32.OpenServiceW
OpenService.restype = w.LPCVOID
OpenService.argtypes = [w.LPCVOID, w.LPCWSTR, w.DWORD]

QueryServiceStatus = advapi32.QueryServiceStatus
QueryServiceStatus.restype = w.BOOL
QueryServiceStatus.argtypes = [w.LPCVOID, ctypes.c_void_p]

CloseServiceHandle = advapi32.CloseServiceHandle

class SERVICE_STATUS(ctypes.Structure):
    _fields_ = [
        ('dwServiceType', w.DWORD), ('dwCurrentState', w.DWORD),
        ('dwControlsAccepted', w.DWORD), ('dwWin32ExitCode', w.DWORD),
        ('dwServiceSpecificExitCode', w.DWORD), ('dwCheckPoint', w.DWORD),
        ('dwWaitHint', w.DWORD),
    ]

SERVICE_NAME = 'CodexSandboxService.OpenAI.Codex'
RESULT_FILE = r'D:\\AIOS\\_admin_check_svc_v2_result.txt'

with open(RESULT_FILE, 'w', encoding='utf-8') as f:
    f.write('')

is_admin = ctypes.windll.shell32.IsUserAnAdmin()
with open(RESULT_FILE, 'a', encoding='utf-8') as f:
    f.write(f'is_admin={is_admin}\\n')

if not is_admin:
    print('not admin')
    sys.exit(2)

scm = OpenSCManager(None, None, SC_MANAGER_ALL_ACCESS)
if not scm:
    print(f'OpenSCManager failed: {kernel32.GetLastError()}')
    sys.exit(3)
with open(RESULT_FILE, 'a', encoding='utf-8') as f:
    f.write('OpenSCManager ok\\n')

svc = OpenService(scm, SERVICE_NAME, SERVICE_QUERY_CONFIG)
if not svc:
    err = kernel32.GetLastError()
    with open(RESULT_FILE, 'a', encoding='utf-8') as f:
        f.write(f'OpenService failed: {err}, service not registered\\n')
    print(f'OpenService failed: {err}')
    CloseServiceHandle(scm)
    sys.exit(4)
with open(RESULT_FILE, 'a', encoding='utf-8') as f:
    f.write('OpenService ok\\n')

status = SERVICE_STATUS()
if QueryServiceStatus(svc, ctypes.byref(status)):
    states = {1:'STOPPED',2:'START_PENDING',3:'STOP_PENDING',4:'RUNNING',5:'CONTINUE_PENDING',6:'PAUSE_PENDING',7:'PAUSED'}
    state_name = states.get(status.dwCurrentState, str(status.dwCurrentState))
    msg = f'state={state_name}, exit_code={status.dwWin32ExitCode}, checkpoint={status.dwCheckPoint}, wait_hint={status.dwWaitHint}\\n'
    with open(RESULT_FILE, 'a', encoding='utf-8') as f:
        f.write(msg)
    print(msg.strip())

CloseServiceHandle(svc)
CloseServiceHandle(scm)
print('done')
