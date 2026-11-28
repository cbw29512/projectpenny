"""Fixed service database scopes; never accept model-selected routines."""
from dataclasses import dataclass
import re

NAME=re.compile(r"[a-z][a-z0-9_]{0,62}")
SCOPES={
    "inference":("penny_inference_begin()","penny_inference_finish(uuid,text)",
                 "penny_inference_claim(uuid)","penny_inference_personal_recall(uuid,uuid,uuid)",
                 "penny_inference_business_recall(uuid,uuid,uuid)",
                 "penny_inference_complete_draft(uuid,uuid,uuid,text)"),
    "bridge":("penny_bridge_admit(uuid,uuid,uuid,bigint,text)",
              "penny_bridge_ack(uuid,uuid,uuid)","penny_bridge_pending_reply(uuid)",
              "penny_bridge_record_delivery(uuid,uuid,text)","penny_bridge_reserve()",
              "penny_bridge_defer(integer,text)","penny_bridge_reject(uuid,uuid,uuid)",
              "penny_community_receipt_exists(uuid,uuid)",
              "penny_community_admit(uuid,uuid,uuid,uuid,text,bigint,bigint)",
              "penny_community_reserve()"),
    "projection":("penny_activity_reserve(text)","penny_activity_finish(text)",
                  "penny_activity_inputs()"),
}


@dataclass(frozen=True,slots=True)
class RoleAudit:
    ready: bool
    issues: tuple[str,...]


def valid_name(name):
    return type(name) is str and NAME.fullmatch(name) is not None


def valid_schema(schema):
    return (valid_name(schema) and schema not in ("public","information_schema")
            and not schema.startswith("pg_"))
