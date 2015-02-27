# pid.py - module to help manage PID files
import errno
import fcntl
import logging
import os


def is_process_alive(pid):
    """Sends null signal to a process to check if it's alive"""
    try:
        # Sending the null signal (sig. 0) to the process will check
        # pid's validity.
        os.kill(pid, 0)
    except OSError, e:
        # Access denied, but process is alive
        return e.errno == errno.EPERM
    except:
        return False
    else:
        return True


def kill_processes(pids):
    while pids:
        pid = pids.pop()
        if is_process_alive(pid):
            try:
                logging.info("Sending SIGKILL to PID: %d" % pid)
                os.kill(pid, 9)
            except OSError, e:
                if e.errno == errno.ESRCH:
                    # process is dead already, no need to do anything
                    pass
                else:
                    raise
            else:
                # We'll check if the process is dead in a later iteration
                pids.insert(0, pid)


def check(path):
    try:
        logging.info("Checking pidfile '%s'", path)
        pids = [int(pid) for pid in open(path).read().strip().split(' ')]
        kill_processes(pids)
    except IOError, (code, text):
        if code == errno.ENOENT:
            logging.warning("pidfile '%s' not found" % path)
        else:
            raise


def write(path, append=False, pid=None):
    try:
        if pid is None:
            pid = os.getpid()
        if append:
            pidfile = open(path, 'a+b')
        else:
            pidfile = open(path, 'wb')
        # get a blocking exclusive lock, we may have multiple
        # processes updating this pid file.
        fcntl.flock(pidfile.fileno(), fcntl.LOCK_EX)
        if append:
            pidfile.write(" %d" % pid)
        else:
            # clear out the file
            pidfile.seek(0)
            pidfile.truncate(0)
            # write the pid
            pidfile.write(str(pid))
        logging.info("Writing PID %s to '%s'", pid, path)
    except:
        raise
    finally:
        try:
            pidfile.close()
        except:
            pass


def remove(path):
    try:
        # make sure we delete our pidfile
        logging.info("Removing pidfile '%s'", path)
        os.unlink(path)
    except:
        pass
