# Netlify Workshop draft rehearsal
Prerequisites: Maker has checked credit balance and auto-recharge, approved
one manual draft deployment, installed/logged into Netlify CLI separately,
and checked out the exact reviewed commit. Do not deploy from main or
attach production secrets. The GitHub connector does not deploy files.

From the repository root run the existing tests:
```powershell
node --test tests/web/*.test.mjs
python -m unittest discover -s tests -p test_workshop_smoke.py -v
```
The smoke functions are outside the default functions directory; the
normal netlify.toml remains static only. Explicit draft command:
```powershell
netlify deploy --site 28c495fc-f47a-427b-9ee2-95d4eadd2d8d --dir website --functions netlify/workshop-functions
```
Do not add --prod. Use the exact returned unique HTTPS draft URL
(the 24-character deploy ID plus --projectpenny.netlify.app).
If the deploy is access-protected, do not remove protection for a test;
record inconclusive and use an approved authenticated test procedure.
Confirm both code-based rules in the deploy post-processing log.
The public smoke response contains only a fixed status marker, no real data.
After verifying the draft URL and reviewing charges, run once:
```powershell
python -m penny.runtime.workshop_smoke --host <draft-hostname> --confirm
```
Replace the placeholder with the actual hostname (no scheme or path).
At most 13 sequential requests, fixed two paths, no retries or credentials.
Observed 503 marker plus 429 for each route is necessary but not sufficient:
verify post-processing details, deploy ID, no alternative route to the
runtime, and provider logs. Inconclusive means stop and investigate, not
raise the request rate or retry indefinitely. Production activation
requires a separate review; draft observations cannot certify production.
No actual live rehearsal performed by this change.

References:
https://docs.netlify.com/api-and-cli-guides/cli-guides/get-started-with-cli/
https://docs.netlify.com/manage/security/secure-access-to-sites/rate-limiting/
