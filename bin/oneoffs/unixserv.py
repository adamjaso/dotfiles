import socket, sys, os

if len(sys.argv) < 2:
    print("usage: unixserv.py SOCKFILE")
    sys.exit(1)
if os.exists(sys.argv[1]):
    os.unlink(sysargv[1])
print("unixserv.py: starting...", file=sys.stderr)
server = socket.socket(socket.AF_UNIX)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(sys.argv[1])
server.listen(8)
lines = [line for line in sys.stdin]
pid = os.fork()
if pid != 0:
    print("unixserv.py: pid=" + str(pid), file=sys.stderr)
    sys.exit(0)
print("unixserv.py: started.", file=sys.stderr)
for line in lines:
    conn, _ = server.accept()
    conn.send(line.encode("utf-8"))
    print(line, end="")
    conn.close()
server.shutdown(socket.SHUT_RD)
server.close()
print("unixserv.py: exited.", file=sys.stderr)
