"""Private subprocess: fixed getaddrinfo only, no HTTP, no inherited app credentials."""
import json,socket,sys,os,ctypes,signal
parent=os.getppid()
if sys.platform=="linux":
 if ctypes.CDLL(None,use_errno=True).prctl(1,signal.SIGKILL,0,0,0)!=0: raise SystemExit(1)
 if os.getppid()!=parent: raise SystemExit(1)
try:
 host=sys.argv[1];port=int(sys.argv[2]);answers=socket.getaddrinfo(host,port,socket.AF_UNSPEC,socket.SOCK_STREAM)
 if len(answers)>64:raise ValueError()
 print(json.dumps({'ok':True,'answers':answers},separators=(',',':')))
except Exception:
 print('{"ok":false}')
 raise SystemExit(1)
