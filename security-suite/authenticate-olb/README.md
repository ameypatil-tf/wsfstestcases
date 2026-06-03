# Authenticate OLB Security Suite

Targeted security regression suite for:

- `POST /clients/v1/authenticate-online-banking`

This suite focuses on negative authentication and input abuse scenarios for the exact API payload you provided.

## Files

- `generate_authenticate_olb_security_suite.py` - generator script for this endpoint.
- `authenticate-olb.security.postman_collection.json` - generated Postman security suite.
- `authenticate-olb.security.environment.template.json` - environment template.

## Included test scenarios

1. Missing `client_id` header
2. Missing `client_secret` header
3. Invalid `client_secret` header
4. Empty client credential headers
5. Missing `password`
6. Empty `password`
7. Missing `userId`
8. Empty `userId`
9. Tampered body `clientId`
10. Invalid `channel`
11. Overlong `userId`
12. SQLi-style `userId` payload
13. Wrong type `userId` (number)
14. Missing `routingNumber`

Each test asserts:

- Response is rejected (`400/401/403/404/422`)
- No internal server error (`!= 500`)

## Regenerate

```bash
python3 /workspace/security-suite/authenticate-olb/generate_authenticate_olb_security_suite.py \
  --output /workspace/security-suite/authenticate-olb/authenticate-olb.security.postman_collection.json
```

## Run with Newman

```bash
newman run "/workspace/security-suite/authenticate-olb/authenticate-olb.security.postman_collection.json" \
  -e "/workspace/security-suite/authenticate-olb/authenticate-olb.security.environment.template.json" \
  --reporters cli,json \
  --reporter-json-export "/workspace/security-suite/authenticate-olb/newman-authenticate-olb-security-report.json"
```

## mTLS note

This UAT endpoint enforces client certificate authentication. To test API-layer behavior, run Newman with your certificate:

```bash
newman run "/workspace/security-suite/authenticate-olb/authenticate-olb.security.postman_collection.json" \
  -e "/workspace/security-suite/authenticate-olb/authenticate-olb.security.environment.template.json" \
  --ssl-client-cert "/path/to/client-cert.pem" \
  --ssl-client-key "/path/to/client-key.pem" \
  --ssl-client-passphrase "<optional-passphrase>"
```
