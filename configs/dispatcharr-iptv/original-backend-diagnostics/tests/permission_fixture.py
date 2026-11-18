"""Only synthetic filesystem state inside a disposable user/network namespace/chroot."""
import importlib.util,json,os,stat,tempfile,sys
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fixture_lifecycle',HERE/'candidate/lifecycle.py');L=importlib.util.module_from_spec(spec);spec.loader.exec_module(L)

def main():
    assert os.geteuid()==0 and os.environ.get('BACKEND_DIAGNOSTIC_PERMISSION_FIXTURE')=='1'
    count=0
    with tempfile.TemporaryDirectory(prefix='backend-diagnostics-permissions-') as root:
        pid=os.fork()
        if pid==0:
            try:
                os.chroot(root);os.chdir('/');os.chmod('/',0o755)
                def fresh(number):
                    path=Path('/case'+str(number));path.mkdir(mode=0o755);(path/'app').mkdir(mode=0o755);(path/'app/private').mkdir(mode=0o700);L.ROOT=path/'app';return L.ROOT
                fresh(0);target,fd=L._private_dir();name='a'*32+'.intent.json'
                L._receipt(target,fd,name,{'schema':1,'state':'intent'})
                s=(target/name).lstat();assert (s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode),s.st_nlink)==(0,0,0o600,1);assert stat.S_IMODE(target.stat().st_mode)==0o700
                assert os.get_inheritable(fd) is False
                public=L.ROOT/'public-marker';public.write_text('synthetic-public');public.chmod(0o644)
                original=(target/name).read_bytes()
                try:L._receipt(target,fd,name,{'different':True});raise AssertionError('collision accepted')
                except FileExistsError:pass
                assert (target/name).read_bytes()==original
                secret=Path('/fixture-secret');secret.write_text('synthetic-private-data');secret.chmod(0o600)
                link='b'*32+'.intent.json';(target/link).symlink_to(secret)
                try:L._receipt(target,fd,link,{});raise AssertionError('symlink accepted')
                except FileExistsError:pass
                link='c'*32+'.intent.json';os.link(secret,target/link)
                try:L._receipt(target,fd,link,{});raise AssertionError('hardlink accepted')
                except FileExistsError:pass
                assert secret.read_text()=='synthetic-private-data'
                child=os.fork()
                if child==0:
                    try:
                        os.close(fd);os.setgroups([]);os.setgid(1000);os.setuid(1000)
                        assert public.read_text()=='synthetic-public'
                        try:(target/name).read_bytes();os._exit(1)
                        except PermissionError:os._exit(0)
                    except BaseException:os._exit(2)
                _,status=os.waitpid(child,0);assert os.waitstatus_to_exitcode(status)==0
                old=target.with_name('old-diagnostics');os.rename(target,old);target.mkdir(mode=0o700)
                try:L._receipt(target,fd,'d'*32+'.result.json',{});raise AssertionError('replacement accepted')
                except ValueError:pass
                os.close(fd)
                for number,kind in [(1,'public_private'),(2,'public_receipts'),(3,'wrong_owner'),(4,'symlink')]:
                    root=fresh(number)
                    if kind=='public_private':(root/'private').chmod(0o755)
                    elif kind=='public_receipts':(root/'private/backend-diagnostics').mkdir(mode=0o755)
                    elif kind=='wrong_owner':(root/'private/backend-diagnostics').mkdir(mode=0o700);os.chown(root/'private/backend-diagnostics',1000,1000)
                    else:(root/'private/backend-diagnostics').symlink_to('/case0/app/private/backend-diagnostics')
                    try:
                        _,opened=L._private_dir();os.close(opened);raise AssertionError(kind+' accepted')
                    except (ValueError,OSError):pass
                root=fresh(5);target,fd=L._private_dir()
                try:L._receipt(target,fd,'../bad',{});raise AssertionError('traversal accepted')
                except ValueError:pass
                os.close(fd)
                print(json.dumps({'fixture':'disposable UID0/UID1000 chroot','checks':13,'success':True,'Docker_operations':0,'external_requests':0}),flush=True);os._exit(0)
            except BaseException as error:
                print(json.dumps({'fixture':'FAIL','type':type(error).__name__}),flush=True);os._exit(1)
        _,status=os.waitpid(pid,0);assert os.waitstatus_to_exitcode(status)==0

if __name__=='__main__':main()
