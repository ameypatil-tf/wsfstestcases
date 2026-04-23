# wsfstestcases

## k6 performance test from Postman collection

The Postman collection was converted to a k6 test:

- Script: `k6/oao_collection_perf_test.js`
- Request definitions: `k6/oao_requests.json`

### What is included

- Ramp-up / steady / ramp-down stages
- Think time between API calls
- Checks for:
  - Status code (`2xx/3xx`)
  - Response time per request (`MAX_RESPONSE_MS`)
- Thresholds for global failure rate, checks pass rate, and p95 duration

### Required environment variables

- `BASE_ENDPOINT` (example: `https://api.example.com`)
- `WSFS_CLIENT_ID`
- `WSFS_CLIENT_SECRET`

### Optional tuning variables

- `RAMP_UP_DURATION` (default: `1m`)
- `RAMP_UP_VUS` (default: `5`)
- `STEADY_DURATION` (default: `3m`)
- `STEADY_VUS` (default: `5`)
- `RAMP_DOWN_DURATION` (default: `1m`)
- `THINK_TIME_MIN` seconds (default: `0.5`)
- `THINK_TIME_MAX` seconds (default: `2.0`)
- `MAX_RESPONSE_MS` (default: `2000`)
- `P95_RESPONSE_MS` (default: `3000`)
- `REQUEST_NAME_PATTERN` (optional regex; runs only matching request names)

### Example run

```bash
BASE_ENDPOINT="https://api.example.com" \
WSFS_CLIENT_ID="your-client-id" \
WSFS_CLIENT_SECRET="your-client-secret" \
RAMP_UP_VUS=10 \
STEADY_VUS=20 \
k6 run k6/oao_collection_perf_test.js
```

### Example: run only one endpoint

```bash
BASE_ENDPOINT="https://api.example.com" \
WSFS_CLIENT_ID="your-client-id" \
WSFS_CLIENT_SECRET="your-client-secret" \
REQUEST_NAME_PATTERN="Client APIs / Customer Inquiry" \
RAMP_UP_VUS=1 \
STEADY_VUS=1 \
k6 run k6/oao_collection_perf_test.js
```
