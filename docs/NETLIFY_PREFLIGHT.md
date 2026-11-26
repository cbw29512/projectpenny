# Hosted database preflight (read-only audit)
No matching Penny project was returned by the connected Netlify project's
name search. Do not assume a project ID or create a hosting project yet.
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
deployment target and isolated credentials remain unverified. Do not move
migrations or install provisioning packages until explicit launch approval.
