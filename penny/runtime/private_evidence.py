"""Read a bounded, operator-owned private evidence file without following links."""
import logging
import os
import stat

from penny.memory.evidence import MAX_EVIDENCE_BYTES

logger=logging.getLogger(__name__)


def read_private_file(path, limit):
    fd=None
    try:
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        info=os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid()
                or info.st_mode&0o077 or not 1<=info.st_size<=limit):
            raise PermissionError("unsafe evidence file")
        with os.fdopen(fd,"rb") as stream:
            fd=None
            data=stream.read(limit+1)
        if not 1<=len(data)<=limit:
            raise ValueError("invalid evidence size")
        return data
    except Exception as exc:
        logger.error("Private evidence read refused (%s)",type(exc).__name__)
        raise
    finally:
        if fd is not None:
            os.close(fd)


def read_evidence(path):
    return read_private_file(path, MAX_EVIDENCE_BYTES)
