import json
import socket
import errno
import os
from multiprocessing import Process, RLock
from u_server import uServer

lock = RLock()
s_server = uServer()

# TODO create logger functions


def p_thread():
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
                s_server.send((str(p_data).encode("utf-8")))
        except IOError as e:
            if e.errno == errno.EPIPE:
                break

    # p_stats.close()


def f_thread():
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
                    s_server.send((str(f_data).encode("utf-8")))
            except IOError as e:
                if e.errno == errno.EPIPE:
                    break
    # f_stats.close()


if __name__ == "__main__":
    s_server.server("/var/run/l7stats.sock")
    p_proc = Process(target=p_thread)
    f_proc = Process(target=f_thread)

    p_proc.start()
    f_proc.start()