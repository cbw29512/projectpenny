# Bounded private communication worker
Local migration 015: default-disabled bridge control, persistent next-attempt
timestamp, sticky block reason, confirmed remote rejection marker.
One cycle acquires a database-wide advisory lock on a dedicated connection,
reserves a 60-second minimum cooldown before effects, checks local pause and
identity, then performs at most one narrow HTTP operation. No scheduler
transaction held across network. Existing live receipt takes priority over
a new claim. Ack retries use same task/fence; approved answer retries use
same text/fence; failed terminal tasks can be rejected and marked confirmed.
No automatic retry inside a cycle. Empty and waiting cycles return normally;
429/503 persist backoff, unauthorized/conflict block until operator review,
uncertain claim delays at least 15 minutes. No unattended loop is installed.
Tests use real disposable local PostgreSQL and mocked HTTPS client, including
full claim/admit/ack/draft/approve/deliver sequence and simulated restarts.
This is not an end-to-end deployed Netlify test. A crash after remote claim
but before local receipt may lose that question until expiry; no automatic
reclaim. An in-flight send cannot be atomically revoked across databases.
Session advisory lock can be lost with DB connection; hard operation deadline,
supervisor, real operator interface, credit accounting, retention and actual
provider setup remain necessary. Fixed 60-second polling is provisional:
at most 1440 cycles/day if continuously scheduled, not a verified free-tier
budget. No spend or live service.

A second integration suite uses separate cloud/local schemas in disposable PostgreSQL, real mailbox routines, local worker and release gate, and synthetic inference. It exercises one complete private question/reply plus cross-member isolation. HTTP/TLS, scoped provider connections and actual model remain outside that test.
