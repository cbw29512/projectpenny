# Historical timeline v0.1 — reviewed business outcomes
Migration 029 adds immutable disclosure reviews for terminal experiment
events and append-only suppression records. Source event must exist in
the business history; outcome kind/time derives from measured count and
target or recorded stop/rejection, never model prose. Preview binds a
private source digest; trusted admin confirms exact digest and separately
reviewed disclosure evidence. One disclosure per source, exact replay,
conflicting references fail. No automatic publication. No selection
claim of complete history: admin must review successes AND setbacks;
coverage reconciliation is a future gate. Current scope is terminal
business events only, not upgrades, financial milestones or incidents.
Local recent candidate read returns up to 20 fixed event kinds and UTC
day timestamps, newest first; no IDs, evidence, titles or free text.
Suppression replaces an event in the current view with a generic dated
correction; original stays private, cannot reactivate on replay. No
arbitrary replacement facts or public transport. Dates/rare outcomes
still require privacy review; cached copies cannot be retroactively
withdrawn by local suppression alone. Guardian reuses existing private
progress review capability. Tests synthetic, no deployment. Next: build
timeline browser consumer and approved cached transport; later add typed
upgrade/incident/milestone source records and completeness controls.
