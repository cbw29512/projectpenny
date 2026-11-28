"""Read-only, bounded NucBox preflight; no inference or service mutations."""
import http.client
import json
import logging
import re
import subprocess
from pathlib import Path

import psycopg

from penny.brain.transport import MODEL
from penny.guardian.policy import identity_matches
from .config import load_config

logger = logging.getLogger(__name__)
UNITS = ("penny-inference.service", "penny-inference.timer",
         "penny-bridge.service", "penny-bridge.timer")
MAX_BYTES = 262144


def model_probe():
    """Read the local Ollama inventory, never load or download a model."""
    connection = None
    try:
        connection = http.client.HTTPConnection("127.0.0.1", 11434, timeout=5)
        connection.request("GET", "/api/tags")
        response = connection.getresponse()
        if response.status != 200:
            return "unavailable"
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            return "invalid"
        models = json.loads(raw)["models"]
        if type(models) is not list:
            return "invalid"
        matches = [m for m in models if type(m) is dict and m.get("name") == MODEL]
        if not matches:
            return "missing"
        if len(matches) != 1:
            return "invalid"
        digest = matches[0].get("digest")
        if type(digest) is not str or not re.fullmatch("[0-9a-f]{64}", digest):
            return "invalid"
        return "present_unbenchmarked"
    except Exception as exc:
        logger.warning("Model inventory probe unavailable (%s)", type(exc).__name__)
        return "unavailable"
    finally:
        if connection is not None:
            connection.close()


def unit_probe(unit):
    """Inspect fixed Penny unit names only; do not start or reload anything."""
    try:
        if unit not in UNITS:
            return "invalid"
        result = subprocess.run(
            ["systemctl", "--user", "show", "--no-pager",
             "--property=LoadState", "--property=ActiveState", unit],
            capture_output=True, text=True, timeout=5, check=False,
        )
        fields = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        if fields.get("LoadState") == "not-found":
            return "missing"
        if result.returncode != 0 or fields.get("LoadState") != "loaded":
            return "unavailable"
        state = fields.get("ActiveState")
        return state if state in ("active", "inactive", "failed", "activating", "deactivating") else "unknown"
    except Exception as exc:
        logger.warning("Unit probe unavailable (%s)", type(exc).__name__)
        return "unavailable"


def database_probe(dsn):
    """Check runtime schema sentinels, not full migration or privilege certification."""
    try:
        with psycopg.connect(dsn, connect_timeout=5) as conn:
            conn.execute("SET TRANSACTION READ ONLY")
            conn.execute("SET LOCAL statement_timeout='5s'")
            row = conn.execute("""SELECT s.paused,s.rest_enabled,i.enabled,i.uncertain,
                                  b.enabled,b.blocked_reason IS NOT NULL
                                  FROM scheduler_control s CROSS JOIN inference_runtime i
                                  CROSS JOIN bridge_control b
                                  WHERE s.singleton AND i.singleton AND b.singleton""").fetchone()
            if row is None:
                return {"status": "missing_control"}
            return {"status": "runtime_schema_present", "paused": row[0],
                    "rest_enabled": row[1], "inference_enabled": row[2],
                    "inference_uncertain": row[3], "bridge_enabled": row[4],
                    "bridge_blocked": row[5]}
    except Exception as exc:
        logger.warning("Database probe unavailable (%s)", type(exc).__name__)
        return {"status": "unavailable"}


def preflight(config_dir):
    """Continue independent checks after failure; return no secrets or task content."""
    checks = {}
    for kind in ("operator", "inference", "bridge"):
        try:
            config = load_config(Path(config_dir) / (kind + ".json"), kind)
            checks[kind] = "valid"
            if kind == "operator":
                checks["database"] = database_probe(config.dsn)
        except Exception as exc:
            logger.warning("Configuration probe unavailable (%s)", type(exc).__name__)
            checks[kind] = "unavailable"
            if kind == "operator":
                checks["database"] = {"status": "not_checked"}
    return {"schema": "penny-preflight-v1", "configuration": checks,
            "identity_valid": identity_matches(), "model": MODEL,
            "model_inventory": model_probe(),
            "units": {unit: unit_probe(unit) for unit in UNITS},
            "certified": False}
