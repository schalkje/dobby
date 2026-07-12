Run these checks in parallel where possible.

**Check Azure CLI and the azure-devops extension**
```bash
az version --output json
```
- If `az` is not found → stop: "Azure CLI is not installed. Install from https://learn.microsoft.com/cli/azure/install-azure-cli"
- If `azure-devops` is not listed under `extensions` → install it: `az extension add --name azure-devops`
  - Symptom that the extension is missing: any `az devops ...` or `az boards ...` command fails with `'devops' is misspelled or not recognized by the system.`
  - On corporate networks the install may fail with `SSL: CERTIFICATE_VERIFY_FAILED` (self-signed certificate in chain — typical for TLS-inspecting proxies).
    - **Preferred fix**: point Python/`az` at a CA bundle that includes the corporate root certificate. Set these env vars (User scope on Windows, or in the user's shell rc):
      - `REQUESTS_CA_BUNDLE` = `<path-to-cacert.pem>`
      - `AZURE_CLI_CA_BUNDLE` = `<path-to-cacert.pem>`
      - `SSL_CERT_FILE` = `<path-to-cacert.pem>`
      - The bundle should be `certifi`'s `cacert.pem` with the corporate root certificate appended.
      - Verify with: `az devops project list --organization <org-url> --output json` (no SSL bypass needed).
    - **Last-resort workaround** (insecure, only if no bundle is available yet): `AZURE_CLI_DISABLE_CONNECTION_VERIFICATION=1`. This disables TLS verification — use only to unblock and then switch to the CA bundle approach.

**Check Python availability**
```bash
python --version
```
- If `python` is not found → stop: "Python 3 is required for the markdown field helper scripts. Install from https://python.org"
- Only stdlib is needed — no pip packages required.

**Check authentication and show identity**
```bash
az account show --query "{user:user.name, tenant:tenantId}" --output json
```
- If this fails → stop: "Run: `az login`"
- Display the logged-in user so they can confirm it's the right account.
