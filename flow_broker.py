import json
import socket
import errno
import os
from queue import Queue
from threading import Thread
import hashlib
from syslog import \
    openlog, syslog, LOG_PID, LOG_PERROR, LOG_DAEMON, \
    LOG_DEBUG, LOG_ERR, LOG_WARNING, LOG_INFO

debug = 0


def print_pkt(pkt):
    print_pkt_data = (str(pkt["src_ip"]) + " " + str(pkt["src_port"]) + " " +
                      str(pkt["dest_ip"]) + " " + str(pkt["dest_port"]) + " " + str(pkt["ip.totlen"]))
    print(print_pkt_data)


def server(sq):
    path = "/var/run/l7stats.sock"
    try:
        os.unlink(path)
    except OSError as e:
        syslog(LOG_ERR, f"Cannot unlink file: {path}")
        if os.path.exists(path):
            raise
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    syslog(LOG_INFO, "Starting up stats socket")
    s.bind(path)
    s.listen()
    disconn = True
    while True:
        if disconn:
            syslog(LOG_INFO, f"Waiting for a connection on {s}")
            conn, addr = s.accept()
            syslog(LOG_INFO, f"Accepted connection on {s}")
            disconn = False
        while True:
            msg = sq.get()
            if not len(msg):
                continue
            try:
                conn.sendall(msg)
            except Exception as e:
                syslog(LOG_ERR, f"Could not send data on {conn}")
                disconn = True
                break
        conn.close()


def pkt_thread(sq):
    disconn = True
    p = socket.socket()

    syslog(LOG_INFO, "Starting up on pkt socket")
    p.bind(('127.0.0.1', 6001))
    rbytes = 0
    tbytes = 0
    rh_data = ""
    th_data = ""
    rret = 0
    tret = 0
    p.listen()
    while True:
        if disconn:
            syslog(LOG_INFO, f"Waiting for a connection on {p}")
            p_conn, ulog_addr = p.accept()
            syslog(LOG_INFO, f"Accepted connection from: {p}")
            try:
                p_fh = p_conn.makefile()
            except Exception as e:
                syslog(LOG_ERR, f"Cannot read socket: Restarting {p_conn}")
            disconn = True
        while True:
            try:
                p_data = p_fh.readline()
            except Exception as e:
                syslog(LOG_ERR, f"Lost connection to packet socket: {e}")
                p_conn.close()
                disconn = True

            if not p_data:
                break

            p_jd = json.loads(p_data)
            if p_jd["ip.protocol"] == 1:
                continue
            elif "src_port" not in p_jd:
                continue
            try:
                if p_jd["oob.out"] != "":
                    if debug == 1:
                        print_pkt(p_jd)
                    h_data = (str(p_jd["src_ip"]) + str(p_jd["src_port"]) +
                              str(p_jd["dest_ip"]) + str(p_jd["dest_port"])).replace(".", "")
                    if th_data == h_data:
                        tbytes += p_jd["ip.totlen"]
                        tret = 1
                        continue
                    elif th_data != h_data and tret == 1:
                        th_data = hashlib.sha1(th_data.encode())
                        th_data = str(th_data.hexdigest())
                        q_data = {th_data: {"event": "pkt", "iface": p_jd["oob.out"], "t_bytes": tbytes}}
                        tbytes = p_jd["ip.totlen"]
                        th_data = h_data
                        tret = 1
                    else:
                        tbytes = p_jd["ip.totlen"]
                        th_data = h_data
                        tret = 1
                        continue

                else:
                    if debug == 1:
                        print_pkt(p_jd)
                    h_data = (str(p_jd["dest_ip"]) + str(p_jd["dest_port"]) +
                              str(p_jd["src_ip"]) + str(p_jd["src_port"])).replace(".", "")
                    if rh_data == h_data:
                        rbytes += p_jd["ip.totlen"]
                        rret = 1
                        continue
                    elif rh_data != h_data and rret == 1:
                        rh_data = hashlib.sha1(rh_data.encode())
                        rh_data = str(rh_data.hexdigest())
                        q_data = {rh_data: {"event": "pkt", "iface": p_jd["oob.in"], "r_bytes": rbytes}}
                        rbytes = p_jd["ip.totlen"]
                        rh_data = h_data
                        rret = 1
                    else:
                        rbytes = p_jd["ip.totlen"]
                        rh_data = h_data
                        rret = 1
                        continue
            except Exception as e:
                p_data = {"KeyError": e}
                syslog(LOG_ERR, f"Must have a KeyError with: {e}")
                continue
            q_data = json.dumps(q_data)
            q_data = q_data + "\n"
            try:
                sq.put((str(q_data).encode("utf-8")))
            except IOError as e:
                if e.errno == errno.EPIPE:
                    break


def flow_thread(sq):
    disconn = True
    f = socket.socket()

    syslog(LOG_INFO, "Starting up flow socket")
    f.bind(('127.0.0.1', 6000))

    f.listen()

    while True:
        if disconn:
            syslog(LOG_INFO, f"Waiting for a connection on {f}")
            f_conn, ulog_addr = f.accept()
            syslog(LOG_INFO, f"Accepted connection from: {f}")
            try:
                f_fh = f_conn.makefile()
            except Exception as e:
                syslog(LOG_ERR, f"Cannot read socket: Restarting {f_conn}")
            disconn = True
        while True:
            try:
                f_data = f_fh.readline()
            except Exception as e:
                syslog(LOG_ERR, f"Lost connection to flow socket: {e}")
                f_conn.close()
                disconn = True

            if not f_data:
                break

            f_jd = json.loads(f_data)
            if f_jd is None:
                syslog(LOG_DEBUG, "We have no data on f_jd")
                continue
            if "orig.ip.protocol" not in f_jd.keys():
                syslog(LOG_DEBUG, "Still no data in f_jd")
                continue
            if f_jd["orig.ip.protocol"] == 1:
                continue
            else:
                try:
                    h_data = (str(f_jd["reply.ip.daddr.str"]) + str(f_jd["reply.l4.dport"])
                              + str(f_jd["reply.ip.saddr.str"]) + str(f_jd["reply.l4.sport"])).replace(".", "")
                    h_data = hashlib.sha1(h_data.encode())
                    h_data = h_data.hexdigest()
                    f_data = {str(h_data): {"event:": "purge"}}
                except Exception as e:
                    f_data = {"KeyError": e}
                    syslog(LOG_ERR, f"Must have a KeyError with: {e}")
                    continue
                f_data = json.dumps(f_data)
                f_data = f_data + "\n"
                try:
                    sq.put((str(f_data).encode("utf-8")))
                except IOError as e:
                    if e.errno == errno.EPIPE:
                        break


if __name__ == "__main__":
    q = Queue(maxsize=0)

    s_proc = Thread(target=server, args=(q,), daemon=True)
    p_proc = Thread(target=pkt_thread, args=(q,))
    f_proc = Thread(target=flow_thread, args=(q,))
    syslog(LOG_INFO, "Flow Broker Starting")
    s_proc.start()
    p_proc.start()
    f_proc.start()
