from __future__ import with_statement
import os
import signal
import atexit
import random


def check_pid(pidfile):
    if pidfile and os.path.exists(pidfile):
        try:
            pid = int(open(pidfile).read().strip())
            os.kill(pid, 0)
            return pid
        except:
            return 0
    return 0


def write_pid(pidfile):
    print "Writing pid file"
    with open(pidfile, 'w') as fobj:
        fobj.write(str(os.getpid()))


def run(cmd, pidfile=None):
    import daemon
    existing_pid = check_pid(pidfile)
    if pidfile and existing_pid:
        print "Server already running (pid=%s)" % (existing_pid,)
        return
    log = open('/var/log/luigi/luigi-server.log', 'a+')  # TODO: better log location...
    ctx = daemon.DaemonContext(stdout=log, stderr=log, working_directory='.')
    with ctx:
        if pidfile:
            print "Checking pid file"
            existing_pid = check_pid(pidfile)
            if not existing_pid:
                write_pid(pidfile)
                cmd()
            else:
                print "Server already running (pid=%s)" % (existing_pid,)
                return
        else:
            cmd()


def fork_linked_workers(num_processes):
    """ Forks num_processes child processes.

    Returns an id between 0 and num_processes - 1 for each child process.
    Will consume the parent process and kill it 

    The child processes will be killed when the parent dies
    If a child dies, the parent shuts down and kills all other children
    TODO: If the parent is force-terminated (kill -9) the child processes will terminate after a while when they notice it.
    """
    children = {}  # keep child indices

    for i in xrange(num_processes):
        child_id = len(children)
        child_pid = os.fork()

        if not child_pid:
            break

        children[child_pid] = child_id

    if len(children) == num_processes:
        # kill all children if parent process exits any other way than all child processes finishing
        def shutdown_handler(signum=None, frame=None):
            print "Shutting down parent. Killing ALL THE children"
            if not signum:
                signum = signal.SIGTERM
            for c in children:
                print "Killing child %d" % c
                try:
                    os.kill(c, signum)
                    os.waitpid(c, 0)
                except OSError:
                    print "Child %d is already dead" % c
                    pass
            os._exit(0)  # exit without calling exit handler

        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)
        signal.signal(signal.SIGQUIT, shutdown_handler)
        atexit.register(shutdown_handler)

        # while children:
        #     pid, status = os.wait()
        #     del children[pid]
        os.wait()
        os.exit(1)  # exit parent without running shutdown_handler
    else:
        # in child process
        # TODO: add periodic check to see if parent is alive and die if parent is dead
        return child_id
