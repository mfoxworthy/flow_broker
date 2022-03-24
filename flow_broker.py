import json
import socket
import errno
import os
from queue import Queue
from threading import Thread, RLock

lock = RLock()


# TODO create logger functions
def server(sq):
    path = "/var/run/l7stats.sock"
    try:
        os.unlink(path)
    except OSError:
        if os.path.exists(path):
            raise
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    print("Starting up on {}".format(path))
    s.bind(path)
    s.listen()

    conn, addr = s.accept()
    while True:
        msg = sq.get()
        conn.sendall(msg)


def p_thread(sq):
    p = socket.socket()

    print("Starting up on {}".format(p))
    p.bind(('127.0.0.1', 6001))

    p.listen()

    # Wait for a connection from ulogd
    print("Waiting for a connection on ulogd_p")
    p_conn, ulog_addr = p.accept()
    print("Accepted connection from: ulogd_p")

    p_fh = p_conn.makefile()

    while True:
        try:
            data = p_fh.readline()
        except:
            break

        if not data:
            break

        p_jd = json.loads(data)
        if p_jd["ip.protocol"] == 1:
            continue
        elif "src_port" not in p_jd:
            continue
        p_data = {"src_ip": p_jd["src_ip"], "src_port": p_jd["src_port"], "dest_ip": p_jd["dest_ip"],
                  "dest_port": p_jd["dest_port"],
                  "oob.in": p_jd["oob.in"], "oob.out": p_jd["oob.out"], "bytes": p_jd["ip.totlen"]}
        p_data = json.dumps(p_data)
        p_data = p_data + "\n"
        # print(s_data)
        try:
            with lock:
                sq.put((str(p_data).encode("utf-8")))
        except IOError as e:
            if e.errno == errno.EPIPE:
                break

    # p_stats.close()


def f_thread(sq):
    f = socket.socket()

    print("Starting up on {}".format(f))
    f.bind(('127.0.0.1', 6000))

    f.listen()

    print("Waiting for a connection on ulogd_f")
    f_conn, ulogp_addr = f.accept()
    print("Accepted connection from: ulogd_f")

    f_fh = f_conn.makefile()

    while True:

        try:
            f_data = f_fh.readline()
        except:
            break
        if not f_data:
            continue

        f_jd = json.loads(f_data)
        if f_jd is None:
            print("We have no data")
            continue
        if "orig.ip.protocol" not in f_jd.keys():
            print("Still no data")
            continue
        if f_jd["orig.ip.protocol"] == 1:
            continue
        else:
            f_data = {"l_ip": f_jd["reply.ip.daddr.str"], "l_port": f_jd["reply.l4.dport"],
                      "r_ip": f_jd["reply.ip.saddr.str"],
                      "r_port": f_jd["reply.l4.sport"], "purge": 1}
            f_data = json.dumps(f_data)
            f_data = f_data + "\n"
            try:
                with lock:
                    sq.put((str(f_data).encode("utf-8")))
            except IOError as e:
                if e.errno == errno.EPIPE:
                    break
    # f_stats.close()


if __name__ == "__main__":

    q = Queue(maxsize=0)

    s_proc = Thread(target=server, args=(q, ), daemon=True)
    p_proc = Thread(target=p_thread, args=(q, ))
    f_proc = Thread(target=f_thread, args=(q, ))

    s_proc.start()
    p_proc.start()
    f_proc.start()




