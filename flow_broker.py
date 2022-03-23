import json
import socket
import errno
import os

# TODO create logger functions

def broker_service():
    s_address = '/var/run/ulogd.sock'
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

    # Create file handler for ulogd json strings
    fh = u_conn.makefile()

    while True:

        try:
            data = fh.readline()
        except:
            break

        if not data:
            break

        jd = json.loads(data)
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
    broker_service()


if __name__ == "__main__":
    broker_service()
