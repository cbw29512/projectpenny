"""Fixed release manifest; no auto-discovery or executable external migration."""
import hashlib
import logging
from pathlib import Path

logger=logging.getLogger(__name__)
NAMES=(
    "001_schema.sql","002_admission.sql","003_delivery.sql","004_security.sql",
    "005_throttle.sql","006_admin.sql","007_admin_throttle.sql",
    "008_activity_observation.sql","009_retire_cloud_admin.sql",
    "010_workshop_observation.sql","011_workshop_budget.sql",
)
ROOT=Path(__file__).resolve().parents[1]/"mailbox"


def release_plan():
    """Return digest and exact immutable migration inputs from trusted checkout."""
    try:
        if tuple(sorted(p.name for p in ROOT.glob("*.sql")))!=NAMES:
            raise ValueError("unexpected mailbox migration set")
        entries=[]
        for name in NAMES:
            path=ROOT/name
            if path.is_symlink() or not path.is_file():
                raise ValueError("unsafe migration file")
            raw=path.read_bytes()
            if not 1<=len(raw)<=131072:
                raise ValueError("invalid migration size")
            # Only remove the known outer wrappers; installer owns transaction.
            lines=raw.decode("utf-8").strip().splitlines()
            if (lines[0]!="BEGIN;" or lines[-1]!="COMMIT;"
                    or any(line.strip().upper() in ("BEGIN;","COMMIT;","ROLLBACK;")
                           for line in lines[1:-1])):
                raise ValueError("unexpected migration transaction wrapper")
            entries.append((name,hashlib.sha256(raw).hexdigest(),"\n".join(lines[1:-1])))
        digest=hashlib.sha256("".join(name+":"+sha+"\n" for name,sha,_ in entries).encode("ascii")).hexdigest()
        return digest,tuple(entries)
    except Exception as exc:
        logger.error("Mailbox release plan refused (%s)",type(exc).__name__)
        raise
