import json
import socket
import sys
import os


def Main():
    fl_table = {}
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

    """listen waits for the client to approach
       the server to make a connection"""
    s.listen(1)
    sc.listen(1)

    while True:
        # Waits for a connection
        print("Waiting for a connection on ulogd")
        u_conn, ulog_addr = s.accept()
        fh = u_conn.makefile()

        try:
            print('connection from', ulog_addr)
            data = fh.readline()
            jd = json.loads(data)
            if jd["ip.protocol"] == 1:
                continue
            elif "src_port" not in jd:
                continue
            s_data = {"src_ip": jd["src_ip"], "src_port": jd["src_port"], "dest_ip": jd["dest_ip"], "dest_port": jd["dest_port"],
                      "oob.in": jd["oob.in"], "oob.out": jd["oob.out"], "bytes": jd["ip.totlen"] }
            s_data = json.dumps(s_data, indent=4)
            print(s_data)
            # Receive the data in small chunks and retransmit it
            while True:
                print("Waiting for a connection on stats")
                stats_conn, stats_addr = sc.accept()

                try:
                    print('connection from', stats_addr)
                    while True:
                        stats_conn.sendall(str(s_data).encode("utf-8"))
                finally:
                    stats_conn.close()
                """
                if jd["oob.in"] != None:
                    r_ip = jd["src_ip"]
                    r_port = jd["src_port"]
                    l_ip = jd["dest_ip"]
                    l_port = jd["dest_port"]
                    rx = jd["ip.totlen"]
                    fl_hash = (r_ip, r_port, l_ip, l_port)
                    fl_hash = str(hash(fl_hash))
                    if fl_hash in fl_table and "rx" in fl_table[fl_hash].keys():
                        fl_table[fl_hash]["rx"] += rx
                    elif fl_hash not in fl_table:
                        fl_table.update({fl_hash: {"rx": 0}})
                    else:
                        fl_table[fl_hash]["rx"] = rx
                if jd["oob.out"] != None:
                    r_ip = jd["dest_ip"]
                    r_port = jd["dest_port"]
                    l_ip = jd["src_ip"]
                    l_port = jd["src_port"]
                    tx = jd["ip.totlen"]
                    fl_hash = (l_ip, l_port, r_ip, r_port)
                    fl_hash = str(hash(fl_hash))
                    if fl_hash in fl_table and "tx" in fl_table[fl_hash].keys():
                        fl_table[fl_hash]["tx"] += tx
                    elif fl_hash not in fl_table:
                        fl_table.update({fl_hash: {"tx": 0}})
                    else:
                        fl_table[fl_hash]["tx"] = tx
                print(fl_table)
                """
        finally:
                # Free the connection
            u_conn.close()



if __name__ == "__main__":
    Main()