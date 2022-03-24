import json
import select
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
    disconn = True
    while True:
        if disconn:
            conn, addr = s.accept()
            disconn = False
        while True:
            msg = sq.get()
            if not len(msg):
                continue
            try:
                conn.sendall(msg)
            except Exception as e:
                print("Could not send data")
                disconn = True
                break
        conn.close()



def pkt_thread(sq):
    disconn = True
    p = socket.socket()

    print("Starting up on {}".format(p))
    p.bind(('127.0.0.1', 6001))

    p.listen()

    while True:
        if disconn:
            print("Waiting for a connection on ulogd_p")
            p_conn, ulog_addr = p.accept()
            print("Accepted connection from: ulogd_p")
            try:
                p_fh = p_conn.makefile()
            except Exception as e:
                print("Cannot read socket: Restarting")
            disconn = True
        while True:
            try:
                p_data = p_fh.readline()
            except:
                p_conn.close()
                disconn = True

            if not p_data:
                break

            p_jd = json.loads(p_data)
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
                sq.put((str(p_data).encode("utf-8")))
            except IOError as e:
                if e.errno == errno.EPIPE:
                    break


def flow_thread(sq):
    disconn = True
    f = socket.socket()

    print("Starting up on {}".format(f))
    f.bind(('127.0.0.1', 6000))

    f.listen()

    while True:
        if disconn:
            print("Waiting for a connection on ulogd_f")
            f_conn, ulog_addr = f.accept()
            print("Accepted connection from: ulogd_f")
            try:
                f_fh = f_conn.makefile()
            except Exception as e:
                print("Cannot read socket: Restarting")
            disconn = True
        while True:
            try:
                f_data = f_fh.readline()
            except:
                f_conn.close()
                disconn = True

            if not f_data:
                break

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
                    sq.put((str(f_data).encode("utf-8")))
                except IOError as e:
                    if e.errno == errno.EPIPE:
                        break


if __name__ == "__main__":

    q = Queue(maxsize=0)

    s_proc = Thread(target=server, args=(q, ), daemon=True)
    p_proc = Thread(target=pkt_thread, args=(q, ))
    f_proc = Thread(target=flow_thread, args=(q, ))

    s_proc.start()
    p_proc.start()
    f_proc.start()




