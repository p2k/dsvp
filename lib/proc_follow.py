#
#  proc_follow.py
#  dSVP
#
#  Created by p2k on 24.03.18.
#  Copyright (c) 2018 Patrick "p2k" Schneider
#
#  Licensed under the EUPL
#

import sys, os

__all__ = ['ProcessFollower']

def find_line(buf):
    r = buf.find(b'\r')
    n = buf.find(b'\n')
    if r == -1 and n == -1:
        return

    if r == -1 or (n != -1 and r > n):
        line = bytes(buf[:n])
        buf[:] = buf[(n+1):]
    elif n == -1 or (r != -1 and n > r):
        line = bytes(buf[:r])
        if n == r+1:
            buf[:] = buf[(r+2):]
        else:
            buf[:] = buf[(r+1):]

    return line

if sys.platform == 'darwin' or sys.platform.startswith('freebsd'):
    import select, fcntl

    class ProcessFollower(object):
        """
        Utility class for following a process' stdout and stderr pipes at the
        same time (kqueue edition). Object of this class are to be iterated
        over and will yield a tuple of a boolean which is true for stderr (and
        false for stdout) and a byte sequence with the line data.
        """
        def __init__(self, proc):
            self.__proc = proc
            self.__kq = select.kqueue()
            self.__stdout_fd = proc.stdout.fileno()
            self.__stderr_fd = proc.stderr.fileno()
            fcntl.fcntl(self.__stdout_fd, fcntl.F_SETFL, fcntl.fcntl(self.__stdout_fd, fcntl.F_GETFL) | os.O_NONBLOCK)
            fcntl.fcntl(self.__stderr_fd, fcntl.F_SETFL, fcntl.fcntl(self.__stderr_fd, fcntl.F_GETFL) | os.O_NONBLOCK)
            self.__kq.control([
                select.kevent(self.__stdout_fd, select.KQ_FILTER_READ, select.KQ_EV_ADD),
                select.kevent(self.__stderr_fd, select.KQ_FILTER_READ, select.KQ_EV_ADD),
                select.kevent(proc.pid, select.KQ_FILTER_PROC, select.KQ_EV_ADD, select.KQ_NOTE_EXIT)
            ], 0, 0)

        def __iter__(self):
            stdout_buf = bytearray()
            stderr_buf = bytearray()
            while True:
                kevs = self.__kq.control(None, 3, None)
                for kev in kevs:
                    if kev.filter == select.KQ_FILTER_PROC:
                        self.__kq.close()
                        self.__proc.stdout.close()
                        self.__proc.stderr.close()
                        return
                for kev in kevs:
                    if kev.filter != select.KQ_FILTER_READ:
                        continue

                    if kev.ident == self.__stdout_fd:
                        stderr = False
                        buf = stdout_buf
                    else:
                        stderr = True
                        buf = stderr_buf

                    try:
                        while True:
                            buf.extend(os.read(kev.ident, 8192))
                            if self.__proc.poll() is not None:
                                break
                    except BlockingIOError:
                        pass

                    while True:
                        line = find_line(buf)
                        if line is None:
                            break
                        else:
                            yield stderr, line
elif sys.platform.startswith('linux'):
    import select, fcntl

    class ProcessFollower(object):
        """
        Utility class for following a process' stdout and stderr pipes at the
        same time (epoll edition). Object of this class are to be iterated
        over and will yield a tuple of a boolean which is true for stderr (and
        false for stdout) and a byte sequence with the line data.
        """
        def __init__(self, proc):
            self.__proc = proc
            self.__ep = select.epoll()
            self.__stdout_fd = proc.stdout.fileno()
            self.__stderr_fd = proc.stderr.fileno()
            fcntl.fcntl(self.__stdout_fd, fcntl.F_SETFL, fcntl.fcntl(self.__stdout_fd, fcntl.F_GETFL) | os.O_NONBLOCK)
            fcntl.fcntl(self.__stderr_fd, fcntl.F_SETFL, fcntl.fcntl(self.__stderr_fd, fcntl.F_GETFL) | os.O_NONBLOCK)
            self.__ep.register(self.__stdout_fd, select.EPOLLIN | select.EPOLLERR | select.EPOLLHUP)
            self.__ep.register(self.__stderr_fd, select.EPOLLIN | select.EPOLLERR | select.EPOLLHUP)

        def __iter__(self):
            stdout_buf = bytearray()
            stderr_buf = bytearray()
            while True:
                for fd, event in self.__ep.poll():
                    if event == select.EPOLLERR or event == select.EPOLLHUP:
                        self.__ep.close()
                        self.__proc.stdout.close()
                        self.__proc.stderr.close()
                        return

                    if fd == self.__stdout_fd:
                        stderr = False
                        buf = stdout_buf
                    else:
                        stderr = True
                        buf = stderr_buf

                    try:
                        while True:
                            buf.extend(os.read(fd, 8192))
                    except BlockingIOError:
                        pass

                    while True:
                        line = find_line(buf)
                        if line is None:
                            break
                        else:
                            yield stderr, line
else:
    import threading
    from queue import Queue

    class ThreadedLineReader(threading.Thread):
        def __init__(self, f, q, stderr):
            threading.Thread.__init__(self)
            self.__f = f
            self.__q = q
            self.__stderr = stderr

        def run(self):
            buf = bytearray()
            cr = False
            while True:
                b = self.__f.read(1)
                if len(b) == 0:
                    self.__q.put( (self.__stderr, None) )
                    break
                if b == b'\n':
                    if cr:
                        cr = False
                    else:
                        self.__q.put( (self.__stderr, bytes(buf)) )
                        buf.clear()
                elif b == b'\r':
                    cr = True
                    self.__q.put( (self.__stderr, bytes(buf)) )
                    buf.clear()
                else:
                    cr = False
                    buf.extend(b)

    class ProcessFollower(object):
        """
        Utility class for following a process' stdout and stderr pipes at the
        same time (threaded edition). Object of this class are to be iterated
        over and will yield a tuple of a boolean which is true for stderr (and
        false for stdout) and a byte sequence with the line data.
        """
        def __init__(self, proc):
            self.__proc = proc
            self.__q = Queue()
            self.__stdout_lr = ThreadedLineReader(proc.stdout, self.__q, False)
            self.__stdout_lr.start()
            self.__stderr_lr = ThreadedLineReader(proc.stderr, self.__q, True)
            self.__stderr_lr.start()

        def __iter__(self):
            while True:
                stderr, line = self.__q.get()
                if line is None:
                    self.__proc.stdout.close()
                    self.__proc.stderr.close()
                    return
                else:
                    yield stderr, line
