import socket
import os


class uServer:
    path = None
    s = None
    conn = None

    def server(self, path, sq):
        self.path = path
        self.sq = sq

        try:
            os.unlink(path)
        except OSError:
            if os.path.exists(path):
                raise
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        print("Starting up on {}".format(path))
        self.s.bind(path)
        self.s.listen()

        self.conn, addr = self.s.accept()
        while True:
            msg = sq.get()
            self.conn.sendall(msg)


    def send(self, msg):
        self.conn.sendall(msg)

    def close(self):
        if self.conn is not None:
            self.conn.close()
