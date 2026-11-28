# Cloud database operator commands
Run from the reviewed checkout on the trusted Linux operator host.
The protected configuration reader uses POSIX owner/mode and no-follow
checks; Windows-native execution is not supported. Never paste DSNs into
chat, commit them, pass them as command arguments, or store them in the
website. Keep parent directories and release tree trusted.

1. Review the exact migration manifest, offline:
   `python -m netlify.security.operator plan`
2. After provider billing, TLS trust and dedicated database are verified,
   have the trusted provider administrator create a dedicated NOLOGIN owner,
   empty penny_mailbox schema and five restricted login roles. Do not change
   shared database grants or assume provider supports this arrangement.
3. Create a protected mode-0600 JSON file in your private directory with
   exactly database, login, dsn, owner, roles. The login is the installer
   principal with permission to SET ROLE to the owner. The roles object has
   member, bridge, maintenance, projection_writer, projection_reader keys;
   all seven principals distinct. DSN must use explicit verify-full and CA
   trust, host, database, user, password; no ambient PG variables.
4. Run the confirmed install only against the reviewed dedicated database:
   `python -m netlify.security.operator install --config ~/.config/penny/cloud-install.json --release-sha256 REVIEWED_DIGEST --confirm`
5. Independently probe each of the five runtime logins using a separate
   protected JSON file with exactly database, login, dsn, scope:
   `python -m netlify.security.operator probe --config ~/.config/penny/cloud-reader.json`

The installer does not create roles, purchase resources, provision a database,
enable routes, repair grants outside the mailbox schema or upgrade an existing
installation. Probe checks are read-only, not production certification.
No provider credential or live database was accessed by this increment.
