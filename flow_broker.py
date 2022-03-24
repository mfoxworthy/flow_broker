import json
import socket
import errno
import os
import threading

from multiprocessing import Process, Pipe, RLock
lock = RLock()

sc_address = '/var/run/l7stats.sock'
try:
    os.unlink(sc_address)
except OSError:
    if os.path.exists(sc_address):
        raise
    sc = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    print("Starting up on {}".format(sc_address))
    sc.bind(sc_address)

    sc.listen(5)

    # Wait for a connection from l7stats
    print("Waiting for a connection on stats")
    stats_conn, stats_addr = sc.accept()
    stats_conn.setblocking(0)
    print("Accepted connection from: l7stats")


# TODO create logger functions

def stats_thread(msg):
    stats_conn.sendall(msg)


def p_thread():
    p = socket.socket()

    print("Starting up on {}".format(p))
    p.bind(('127.0.0.1', 6001))

    p.listen()

    # Wait for a connection from ulogd
    print("Waiting for a connection on ulogd_p")
    p_conn, ulog_addr = p.accept()
    print("Accepted connection from: ulogd_p")

    '''
    p_stats = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    stats_address = "/var/run/l7stats.sock"
    p_stats.connect(stats_address)
    '''

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
                stats_thread((str(p_data).encode("utf-8")))
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

    '''
    f_stats = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    stats_address = "/var/run/l7stats.sock"
    f_stats.connect(stats_address)
    '''

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
                    stats_thread((str(f_data).encode("utf-8")))
            except IOError as e:
                if e.errno == errno.EPIPE:
                    break
    # f_stats.close()


if __name__ == "__main__":

    p_proc = Process(target=p_thread)
    f_proc = Process(target=f_thread)

    p_proc.start()
    f_proc.start()

