# Hosted database preflight (read-only audit)
2026-11-27: Maker approved using the existing Netlify Pro team allowance.
Created the empty project projectpenny on team cbw29512 (Pro).
Provider project ID: 28c495fc-f47a-427b-9ee2-95d4eadd2d8d.
Management URL: https://app.netlify.com/projects/projectpenny.
Target hostname: projectpenny.netlify.app. No published deploy yet;
HTTPS, project access policy and credit/recharge settings not certified.
No database, domain, credit purchase or plan upgrade performed.
Netlify's database guidance confirms @netlify/database package presence can
trigger provisioning on deploy; active database compute and bandwidth consume
credits. Existing mailbox migrations deliberately remain outside automatic
Netlify migration path. No package installation or provisioning in this PR.
Reference: https://docs.netlify.com/build/data-and-storage/netlify-database/

Operator-side audit_role(conn,schema,role,scope) checks actual effective
permissions within the dedicated mailbox schema: privileged flags, inherited
role membership, schema ownership/CREATE/USAGE, owner flags, direct relation
and column access, sequences, exact routine execution, grant option,
definer ownership and pinned search_path. Report readiness or issue codes;
no mutations and no automatic remediation. Run for every provisioned scope
using trusted read-only catalog access before enabling any runtime, and
after migration/role changes. Check results against the exact expected
migration set. Tests use disposable local PostgreSQL only.
Limitations: no assertion of whole-database isolation, other schema/object
types, function body authenticity, provider support for login roles, TLS
connectivity, or simultaneous permission changes. Runtime principal checks
still needed. Real provider account permissions, credit/edge settings,
live deployment and isolated credentials remain unverified. Do not move
migrations or install provisioning packages until explicit launch approval.
