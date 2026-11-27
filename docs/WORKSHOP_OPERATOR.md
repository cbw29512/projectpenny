# Interim private Workshop operator
Local SSH CLI reuses the protected operator configuration; no web route,
deployment, additional credentials or model tools. The NucBox is the sole administration boundary. This local tool remains
the trusted review interface; any future UI is local-only.
From the Penny release directory, using its existing virtualenv:
```sh
python -m penny.runtime.workshop --config ~/.config/penny/operator.json list
python -m penny.runtime.workshop --config ~/.config/penny/operator.json inspect TASK_UUID
```
List returns at most 20 recent records, no content, no certification
claim. Inspect returns ASCII-escaped JSON with artifact, current review
ID, reviewed digest and private export readiness. Never interpret as HTML.
Use real reviewed evidence kept outside Git. Evidence file must be owned
by the current OS user, mode 0600 or stricter, regular, no final symlink,
1–16384 bytes. The trusted local administrator supplies reviewer UUID;
this is an attestation, not an independently authenticated identity.
```sh
python -m penny.runtime.workshop --config ~/.config/penny/operator.json review TASK_UUID \
  --digest CONTENT_SHA256 --source-ref UNIQUE_REVIEW_REF --reviewer-id REVIEWER_UUID \
  --evidence-ref OPAQUE_EVIDENCE_REF --evidence-file PRIVATE_FILE \
  --usefulness pass --accuracy pass --originality pass --privacy pass \
  --completeness pass --confirm
```
Each criterion must be selected based on actual review; example flags
are syntax, not an instruction to pass unreviewed work. Revoke uses
same identity/evidence flags but no check flags. Use a fresh source ref.
Export writes only verified private text bytes to nonterminal stdout.
Use a trusted private directory, umask 077 and shell noclobber:
```sh
(umask 077; set -C; python -m penny.runtime.workshop \
  --config ~/.config/penny/operator.json export TASK_UUID \
  --review-id REVIEW_UUID --digest CONTENT_SHA256 > checklist.txt)
```
Check exit code; a failed command may leave an empty or partial file.
Export is not publication authorization. Existing copies cannot be
retracted after revocation. No actual product or evidence generated here.
No new migration. Unit and disposable PostgreSQL tests only.
