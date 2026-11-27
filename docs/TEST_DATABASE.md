# Migration-complete disposable test schema
All database integration suites use one fixture. Each test receives a random
isolated schema in the dedicated penny_test database. The fixture applies
every migration in sorted order and drops only its own schema at cleanup.
Do not use partial schema fixtures for tests exercising the current scheduler.
The personal recall migration introduced a shared scheduler dependency that
older partial fixtures lacked; CI run 45733530865 exposed 12 errors.

Fault injection now uses an insert-rejecting trigger for candidate writes
instead of dropping a table referenced by later migrations. Existing rollback
assertions, concurrency tests, admission limits, and privacy tests are retained.
Tests discover contiguous migration numbering and assert key current tables.
This does not implement production migration orchestration or upgrade/restore drills.

## CI queue discipline
Feature branches with an open PR use the pull_request trigger only; main
retains push testing. Superseded runs in the same workflow/ref concurrency
group are canceled. Both Python/PostgreSQL and Node jobs remain mandatory
for release certification. This reduces duplicate future work; it does
not cancel legacy ungrouped runs or resolve hosted runner/billing capacity.
