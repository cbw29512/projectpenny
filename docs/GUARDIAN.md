# Guardian — initial enforcement boundary
## Objective
Separate authorization from model judgment. This slice permits private local draft generation and storage, plus worker-only staging and fenced internal recall, and administrator-only reviewed memory approval/revocation. It is not a semantic safety classifier, a sandbox, or a public publishing authorization.

## State
Actor: worker, model, member, administrator. Capability: generate draft, store draft, publish, read private memory, write memory, stage quarantined candidate, network, shell, spend, change identity, change entitlement. Decision: allowed, reason code, policy version. Identity manifest: canonical version and SHA-256 of approved prompt bytes.

## Logic
Trusted worker checks pinned identity and authorizes generation before calling the brain. A completed result must meet private draft shape limits and pass the store-draft capability check before fenced completion. The model and public members have no authorized capabilities at this boundary. Even administrator external actions are denied here: future dedicated interfaces must enforce specific approvals. Unknown actor/capability values fail closed; do not deserialize user assertions as authority. Log decision codes only, not content. No new tools or network paths. The narrowly scoped candidate capability does not grant trusted-memory writes or unrestricted memory recall; see [memory intake](MEMORY_INTAKE.md).
The identity pin detects accidental prompt drift; repository/process write access must be restricted separately. A hash is not proof of semantic personality consistency. Model output can contain false or manipulative claims: do not publish it. Independent evidence validation, owner-scoped memory, audit persistence, actual process sandboxing, spending approvals, signed release provenance and live behavioral evaluations remain required. Emergency stop currently pauses admission/dispatch, not active inference; do not claim immediate termination.

## Tests
Known allowlist, all other combinations denied, invalid types, identity mismatch, invalid draft bounds, worker blocks before model invocation on policy failure, no completion on draft denial. No model or external calls required.
