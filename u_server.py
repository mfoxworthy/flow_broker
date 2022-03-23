import json
import select
import socket
import errno
import os


class U_Server:
    path = None
    s = None
    conn = None
    fh = None


    def server(self, path):
        self.path = path

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

        self.fh = self.conn.makefile()

        return self.fh

    def read(self):
        jd = None

        fd_read = [self.fh]
        fd_write = []

        rd, wr, ex = select.select(fd_read, fd_write, fd_read, 1.0)

        if not len(rd):
            return jd

        try:
            data = self.fh.readline()
        except:
            return None

        if not data:
            return None

        jd = json.loads(data)

        return jd
