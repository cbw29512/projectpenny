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

## Private revision comparison
```sh
python -m penny.runtime.workshop --config ~/.config/penny/operator.json compare REVISION_TASK_UUID
```
Read-only ASCII-escaped JSON: immutable parent and child bytes and SHA-256,
current quality states, admitted improvement brief, exact item additions,
removals and retained order, title/instruction change flags and whether the
original aggregate basis is still current. Pending/invalid/corrupt work
returns status without a comparison. Same text does not prove improvement;
different text does not prove improvement either. Maker still reviews the
new artifact using the existing quality rubric. No public API, approval,
publication or member data. Treat output as confidential.

## Local closed beta operator
Use a fresh random grant UUID per selected tester. A trusted identity adapter
must have verified the member and issued a live session. Commands use the
same private operator config and mode-0600 reviewed local PNG/evidence files.
Inspect produces hashes, not product bytes or an authorization:
```sh
python -m penny.runtime.beta --config ~/.config/penny/operator.json inspect GRANT_UUID \
  --preview-id PREVIEW_UUID --review-id QUALITY_UUID --version BRAND_VERSION --artwork PRIVATE_PNG
```
Export uses the same arguments with action export, both --edition-sha256
and --variant-sha256 from inspection and --confirm. Redirect only to a
protected local file with umask 077 and noclobber. Inspect the actual exported
bytes before grant. Grant uses the same arguments and exact digests plus
--member-id MEMBER_UUID --expires-at UNIX_EPOCH_SECONDS --reviewer-id
REVIEWER_UUID --evidence-ref PRIVATE_REF --evidence-file PRIVATE_FILE
--confirm. Expiry cannot exceed the preview lifetime; no reissue or extension.
Revoke takes GRANT_UUID, reviewer/evidence flags and --confirm only.
No credentials or member tokens on command line. No actual delivery from
this operator CLI; it prepares a proof and records local authorization only.
A future authenticated member delivery adapter must not use operator credentials
in public infrastructure. No live beta invitations or uploads performed.
