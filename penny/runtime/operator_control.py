"""Trusted SSH operator controls; never route these to a public API or model."""
from contextlib import contextmanager
import logging
import os
from uuid import UUID,uuid4

import psycopg

from penny.guardian.policy import identity_matches
from penny.scheduler.storage_db import locked
from penny.scheduler.outcomes import _finalize
from penny.runtime.inference import LOCK_ID as INFERENCE_LOCK
from penny.bridge.worker_store import LOCK_ID as BRIDGE_LOCK

logger=logging.getLogger(__name__)


@contextmanager
def _exclusive(dsn,key):
    # The session lock cannot attest that a separate Ollama process stopped.
    with psycopg.connect(dsn,autocommit=True,connect_timeout=5) as guard:
        guard.execute("SET statement_timeout='5s'")
        acquired=guard.execute("SELECT pg_try_advisory_lock(%s)",(key,)).fetchone()[0]
        yield acquired


def _event(conn,now,action,task_id=None):
    conn.execute("INSERT INTO runtime_operator_event VALUES (%s,%s,%s,%s,%s)",
                 (uuid4(),action,now,os.getuid(),task_id))


def stop(dsn):
    # Emergency admission stop remains available even on identity failure.
    with locked(dsn) as (conn,_,now):
        conn.execute("UPDATE scheduler_control SET paused=true WHERE singleton")
        conn.execute("UPDATE inference_runtime SET enabled=false WHERE singleton")
        conn.execute("UPDATE bridge_control SET enabled=false WHERE singleton")
        _event(conn,now,"stop")
    return True


def start(dsn,kind,*,confirmed=False):
    if kind not in ("inference","bridge") or confirmed is not True:
        return False
    key=INFERENCE_LOCK if kind=="inference" else BRIDGE_LOCK
    with _exclusive(dsn,key) as acquired:
        if not acquired:
            return False
        with locked(dsn) as (conn,control,now):
            if not identity_matches():
                return False
            inf=conn.execute("SELECT * FROM inference_runtime WHERE singleton FOR UPDATE").fetchone()
            bridge=conn.execute("SELECT * FROM bridge_control WHERE singleton FOR UPDATE").fetchone()
            if not inf or not bridge or inf["uncertain"]:
                return False
            if kind=="inference":
                if conn.execute("SELECT 1 FROM work_task WHERE state='running'").fetchone():
                    return False
                conn.execute("UPDATE inference_runtime SET enabled=true WHERE singleton")
                conn.execute("UPDATE scheduler_control SET paused=false WHERE singleton")
            else:
                if control["paused"] or not inf["enabled"] or bridge["blocked_reason"]:
                    return False
                conn.execute("UPDATE bridge_control SET enabled=true WHERE singleton")
            _event(conn,now,"start_"+kind)
            return True


def recover_inference(dsn,*,isolated=False,task_id=None,fence=None):
    # Operator attestation, not a process kill or proof of GPU idleness.
    if isolated is not True or ((task_id is None)!=(fence is None)):
        return False
    if task_id is not None and (type(task_id) is not UUID or type(fence) is not UUID):
        return False
    with _exclusive(dsn,INFERENCE_LOCK) as acquired:
        if not acquired:
            return False
        with locked(dsn) as (conn,control,now):
            inf=conn.execute("SELECT * FROM inference_runtime WHERE singleton FOR UPDATE").fetchone()
            bridge=conn.execute("SELECT enabled FROM bridge_control WHERE singleton").fetchone()
            if (not control["paused"] or not inf or not bridge or inf["enabled"]
                    or bridge["enabled"] or not inf["uncertain"]):
                return False
            row=conn.execute("SELECT * FROM work_task WHERE state='running'").fetchone()
            if row is not None:
                if (row["id"],row["fence"])!=(task_id,fence) or row["lease_until"]>now:
                    return False
                _finalize(conn,row,"failed","operator confirmed isolated recovery",now)
            elif task_id is not None:
                return False
            conn.execute("""UPDATE inference_runtime SET uncertain=false,
                         last_finished=%s,last_result='interrupted' WHERE singleton""",(now,))
            _event(conn,now,"recover_inference",task_id)
            return True


def clear_bridge_block(dsn,*,reviewed=False):
    if reviewed is not True:
        return False
    with _exclusive(dsn,BRIDGE_LOCK) as acquired:
        if not acquired:
            return False
        with locked(dsn) as (conn,control,now):
            gate=conn.execute("SELECT * FROM bridge_control WHERE singleton FOR UPDATE").fetchone()
            if (not gate or gate["enabled"] or not control["paused"]
                    or gate["blocked_reason"] is None):
                return False
            # Preserve existing cooldown; clearing a block never enables network.
            conn.execute("UPDATE bridge_control SET blocked_reason=NULL WHERE singleton")
            _event(conn,now,"clear_bridge_block")
            return True
