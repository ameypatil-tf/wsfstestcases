# API Security Suite (Auth + BOLA)

This folder contains a generated security regression suite for the uploaded Postman API collection.

## Files

- `generate_security_suite.py` - generator script that transforms a Postman collection into a security test collection.
- `OAO_Refactoring_APIs.security.postman_collection.json` - generated suite from the uploaded source collection.
- `security-suite.environment.template.json` - template environment file for Postman/Newman.
- `authenticate-olb/` - dedicated security suite for `POST /clients/v1/authenticate-online-banking`.

## What the suite validates

For each request in the source collection:

1. Missing `client_id` is rejected (`400/401/403`)
2. Missing `client_secret` is rejected (`400/401/403`)
3. Invalid `client_secret` is rejected (`400/401/403`)
4. Empty auth headers are rejected (`400/401/403`)

For requests that include `:clientId` or `:accountNumber` path references:

5. Tampered object reference is blocked (`400/401/403/404`)

Each test also asserts no internal server error (`!= 500`).
The generator also normalizes malformed `{{BASE_ENDPOINT}}...` URL patterns from source collections before creating tests.

## Regenerate suite

```bash
python3 security-suite/generate_security_suite.py \
  --input "/home/ubuntu/.cursor/projects/workspace/uploads/OAO_Refactoring_APIs.postman_collection.json" \
  --output "/workspace/security-suite/OAO_Refactoring_APIs.security.postman_collection.json"
```

## Run with Newman

Install:

```bash
npm install -g newman
```

Execute:

```bash
newman run "/workspace/security-suite/OAO_Refactoring_APIs.security.postman_collection.json" \
  -e "/workspace/security-suite/security-suite.environment.template.json" \
  --reporters cli,json \
  --reporter-json-export "/workspace/security-suite/newman-security-report.json"
```

## Notes

- Populate real values for `BASE_ENDPOINT`, `WSFS_CLIENT_ID`, and `WSFS_CLIENT_SECRET` before running.
- Keep `INVALID_CLIENT_SECRET` invalid on purpose.
- Set `UNAUTHORIZED_CLIENT_ID` and `UNAUTHORIZED_ACCOUNT_NUMBER` to IDs that your test credential should not access.
