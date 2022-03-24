import json
import socket
import errno
import os
from u_server import U_Server


# TODO create logger functions

def broker_service():
    s_address = '/var/run/ulogd_pkt.sock'
    sc_address = '/var/run/l7stats.sock'

    # Make sure the socket does not alredy exist
    try:
        os.unlink(s_address)
        os.unlink(sc_address)
    except OSError:
        if os.path.exists(s_address):
            raise
        if os.path.exists(sc_address):
            raise

    # create a UDS socket
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sc = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    # Bind the socket to the port

    print("Starting up on {}".format(s_address))
    s.bind(s_address)
    print("Starting up on {}".format(sc_address))
    sc.bind(sc_address)

    s.listen()
    sc.listen()

    # Wait for a connection drom ulogd
    print("Waiting for a connection on ulogd")
    u_conn, ulog_addr = s.accept()
    print("Accepted connection from: ulogd")

    # Wait for a connection from l7stats
    print("Waiting for a connection on stats")
    stats_conn, stats_addr = sc.accept()
    print("Accepted connection from: l7stats")
    tmp = dict()
    # Create file handler for ulogd json strings
    fh = u_conn.makefile()

    while True:
        with open("/tmp/ulogd_flows.log") as f:
            try:
                print("Step 1")
                uf_jd = f.readlines()
                if len(uf_jd):
                    uf_jd = uf_jd[-1]
                uf_jd = json.loads(str(uf_jd))
                if uf_jd == tmp:
                    continue
                else:
                    tmp = uf_jd
            except Exception as e:
                print(e)
                break
            if uf_jd is None:
                print("We have no data")
                continue
            if "orig.ip.protocol" not in uf_jd.keys():
                print("Still no data")
                continue
            if uf_jd["orig.ip.protocol"] == 1:
                continue
            else:
                uf_dict = {"l_ip": uf_jd["reply.ip.daddr.str"], "l_port": uf_jd["reply.l4.dport"],
                           "r_ip": uf_jd["reply.ip.saddr.str"],
                           "r_port": uf_jd["reply.l4.sport"], "purge": 1}
                uf_data = json.dumps(uf_dict)
                uf_data = uf_data + "\n"
            try:
                stats_conn.sendall(str(uf_data).encode("utf-8"))
                print("Step 3.2")
            except IOError as e:
                if e.errno == errno.EPIPE:
                    break
            try:
                data = fh.readline()
            except:
                break

            if not data:
                break

            jd = json.loads(data)
            print(jd)
            if jd["ip.protocol"] == 1:
                continue
            elif "src_port" not in jd:
                continue
            s_data = {"src_ip": jd["src_ip"], "src_port": jd["src_port"], "dest_ip": jd["dest_ip"],
                      "dest_port": jd["dest_port"],
                      "oob.in": jd["oob.in"], "oob.out": jd["oob.out"], "bytes": jd["ip.totlen"]}
            s_data = json.dumps(s_data)
            s_data = s_data + "\n"
            # print(s_data)
            try:
                stats_conn.sendall(str(s_data).encode("utf-8"))
            except IOError as e:
                if e.errno == errno.EPIPE:
                    stats_conn.close()
                    u_conn.close()
                    break

    stats_conn.close()


if __name__ == "__main__":
    while True:
        try:
            broker_service()
        except KeyboardInterrupt:
            break
        else:
            continue
