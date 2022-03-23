import json
import socket
import errno
import os
from u_server import U_Server

# TODO create logger functions

def broker_service():
    sc_address = '/var/run/l7stats.sock'

    # Make sure the socket does not alredy exist
    try:
        os.unlink(sc_address)
    except OSError:
        if os.path.exists(sc_address):
            raise

    # create a UDS socket
    sc = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    # Bind the socket to the port

    print("Starting up on {}".format(sc_address))
    sc.bind(sc_address)

    sc.listen()

    # Wait for a connection from l7stats
    print("Waiting for a connection on stats")
    stats_conn, stats_addr = sc.accept()
    print("Accepted connection from: l7stats")

    # Create file handler for ulogd json strings
    uf_fh = uf_conn.makefile()
    up_fh = up_conn.makefile()

    while True:
        print("Step 0")

        try:

            if uf_fh.readline():
                continue
            else:
                print("Step 1")
                uf_data = uf_fh.readline()
            print("uf data done")
        except:
            break

        uf_jd = json.loads(uf_data)
        print("Step 2")
        # Handle flow destroy event
        print("Step 3")
        if uf_jd["orig.ip.protocol"] == 1:
            continue
        else:
            uf_dict = {"l_ip": uf_jd["reply.ip.daddr.str"], "l_port": uf_jd["reply.l4.dport"],
                       "r_ip": uf_jd["reply.ip.saddr.str"],
                       "r_port": uf_jd["reply.l4.sport"], "purge": 1}
            uf_data = json.dumps(uf_dict)
            uf_data = uf_data + "\n"
            print("Step 3.1")
            try:
                stats_conn.sendall(str(uf_data).encode("utf-8"))
                print("Step 3.2")
            except IOError as e:
                if e.errno == errno.EPIPE:
                    pass

        try:
            up_data = up_fh.readline()
        except:
            break

        if not up_data:
            break
        print("Step 2")

        up_jd = json.loads(up_data)

        print("Step 4")
        # Handle ICMP
        if "src_port" not in up_jd:
            continue

        # Handle packet event
        else:
            print(up_jd)
            up_dict = {"src_ip": up_jd["src_ip"], "src_port": up_jd["src_port"], "dest_ip": up_jd["dest_ip"],
                       "dest_port": up_jd["dest_port"],
                       "oob.in": up_jd["oob.in"], "oob.out": up_jd["oob.out"], "bytes": up_jd["ip.totlen"]}

        up_data = json.dumps(up_dict)
        up_data = up_data + "\n"
        print("Step 5")
        try:
            stats_conn.sendall(str(up_data).encode("utf-8"))
        except IOError as e:
            if e.errno == errno.EPIPE:
                break
        print("Step 6")
    stats_conn.close()
    uf_conn.close()
    up_conn.close()


if __name__ == "__main__":
    while True:
        try:
            broker_service()
        except KeyboardInterrupt:
            break
        else:
            continue
