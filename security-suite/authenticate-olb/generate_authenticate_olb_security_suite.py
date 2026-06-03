#!/usr/bin/env python3
"""Generate a targeted security regression suite for authenticate-online-banking API."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Dict, List

REQUEST_REJECTED_SCRIPT = [
    'pm.test("Security negative case is rejected", function () {',
    "  pm.expect([400, 401, 403, 404, 422]).to.include(pm.response.code);",
    "});",
]

NO_SERVER_ERROR_SCRIPT = [
    'pm.test("No internal server error", function () {',
    "  pm.expect(pm.response.code).to.not.equal(500);",
    "});",
]

DEFAULT_HEADERS = [
    {"key": "Content-Type", "value": "application/json", "type": "text"},
    {"key": "client_id", "value": "{{WSFS_CLIENT_ID}}", "type": "text"},
    {"key": "client_secret", "value": "{{WSFS_CLIENT_SECRET}}", "type": "text"},
]

BASE_PAYLOAD = {
    "routingNumber": "7688123459",
    "userId": "username@1",
    "password": "Password#1",
    "clientId": "0001014726",
    "channel": "CodeConnect",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate security Postman collection for authenticate-online-banking endpoint."
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output Postman collection path.",
    )
    return parser.parse_args()


def headers_without(header_name: str) -> List[Dict[str, str]]:
    lowered = header_name.lower()
    return [h for h in DEFAULT_HEADERS if h["key"].lower() != lowered]


def headers_with(header_name: str, value: str) -> List[Dict[str, str]]:
    cleaned = headers_without(header_name)
    cleaned.append({"key": header_name, "value": value, "type": "text"})
    return cleaned


def headers_with_credentials(client_id: str, client_secret: str) -> List[Dict[str, str]]:
    updated = copy.deepcopy(DEFAULT_HEADERS)
    for header in updated:
        key = header["key"].lower()
        if key == "client_id":
            header["value"] = client_id
        elif key == "client_secret":
            header["value"] = client_secret
    return updated


def build_request_item(
    name: str,
    body_payload: Dict[str, Any],
    headers: List[Dict[str, str]],
) -> Dict[str, Any]:
    return {
        "name": name,
        "request": {
            "method": "POST",
            "header": headers,
            "body": {
                "mode": "raw",
                "raw": json.dumps(body_payload, indent=2),
                "options": {"raw": {"language": "json"}},
            },
            "url": {
                "raw": "{{BASE_ENDPOINT}}/clients/v1/authenticate-online-banking",
                "host": ["{{BASE_ENDPOINT}}"],
                "path": ["clients", "v1", "authenticate-online-banking"],
            },
        },
        "event": [
            {
                "listen": "test",
                "script": {
                    "type": "text/javascript",
                    "exec": REQUEST_REJECTED_SCRIPT + NO_SERVER_ERROR_SCRIPT,
                },
            }
        ],
        "response": [],
    }


def with_removed_field(payload: Dict[str, Any], field_name: str) -> Dict[str, Any]:
    mutated = copy.deepcopy(payload)
    mutated.pop(field_name, None)
    return mutated


def generate_collection() -> Dict[str, Any]:
    cases: List[Dict[str, Any]] = []

    cases.append(
        build_request_item(
            "Missing client_id header",
            copy.deepcopy(BASE_PAYLOAD),
            headers_without("client_id"),
        )
    )
    cases.append(
        build_request_item(
            "Missing client_secret header",
            copy.deepcopy(BASE_PAYLOAD),
            headers_without("client_secret"),
        )
    )
    cases.append(
        build_request_item(
            "Invalid client_secret header",
            copy.deepcopy(BASE_PAYLOAD),
            headers_with("client_secret", "{{INVALID_CLIENT_SECRET}}"),
        )
    )
    cases.append(
        build_request_item(
            "Empty client credential headers",
            copy.deepcopy(BASE_PAYLOAD),
            headers_with_credentials("", ""),
        )
    )

    body_missing_password = with_removed_field(BASE_PAYLOAD, "password")
    cases.append(
        build_request_item("Missing password field", body_missing_password, copy.deepcopy(DEFAULT_HEADERS))
    )

    body_empty_password = copy.deepcopy(BASE_PAYLOAD)
    body_empty_password["password"] = ""
    cases.append(
        build_request_item("Empty password", body_empty_password, copy.deepcopy(DEFAULT_HEADERS))
    )

    body_missing_user = with_removed_field(BASE_PAYLOAD, "userId")
    cases.append(
        build_request_item("Missing userId field", body_missing_user, copy.deepcopy(DEFAULT_HEADERS))
    )

    body_empty_user = copy.deepcopy(BASE_PAYLOAD)
    body_empty_user["userId"] = ""
    cases.append(build_request_item("Empty userId", body_empty_user, copy.deepcopy(DEFAULT_HEADERS)))

    tampered_client_payload = copy.deepcopy(BASE_PAYLOAD)
    tampered_client_payload["clientId"] = "{{UNAUTHORIZED_CLIENT_ID}}"
    cases.append(
        build_request_item(
            "Tampered body clientId",
            tampered_client_payload,
            copy.deepcopy(DEFAULT_HEADERS),
        )
    )

    invalid_channel_payload = copy.deepcopy(BASE_PAYLOAD)
    invalid_channel_payload["channel"] = "InvalidChannel"
    cases.append(
        build_request_item(
            "Invalid channel value",
            invalid_channel_payload,
            copy.deepcopy(DEFAULT_HEADERS),
        )
    )

    long_user_payload = copy.deepcopy(BASE_PAYLOAD)
    long_user_payload["userId"] = "u" * 512
    cases.append(
        build_request_item(
            "Overlong userId",
            long_user_payload,
            copy.deepcopy(DEFAULT_HEADERS),
        )
    )

    sqli_payload = copy.deepcopy(BASE_PAYLOAD)
    sqli_payload["userId"] = "' OR '1'='1"
    cases.append(
        build_request_item(
            "SQLi style userId payload",
            sqli_payload,
            copy.deepcopy(DEFAULT_HEADERS),
        )
    )

    numeric_user_payload = copy.deepcopy(BASE_PAYLOAD)
    numeric_user_payload["userId"] = 123456
    cases.append(
        build_request_item(
            "Wrong type userId numeric",
            numeric_user_payload,
            copy.deepcopy(DEFAULT_HEADERS),
        )
    )

    missing_routing_payload = with_removed_field(BASE_PAYLOAD, "routingNumber")
    cases.append(
        build_request_item(
            "Missing routingNumber",
            missing_routing_payload,
            copy.deepcopy(DEFAULT_HEADERS),
        )
    )

    return {
        "info": {
            "_postman_id": "fcdfbf99-0b72-49da-bf4a-926f2ef68b7d",
            "name": "Authenticate OLB - Security Suite",
            "description": (
                "Targeted security regression suite for /clients/v1/authenticate-online-banking "
                "negative authentication and input abuse scenarios."
            ),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": [
            {
                "name": "Authenticate OLB Negative Security Cases",
                "item": cases,
            }
        ],
        "event": [],
        "variable": [
            {"key": "BASE_ENDPOINT", "value": "https://api-uat.wsfsbank.com"},
            {"key": "WSFS_CLIENT_ID", "value": ""},
            {"key": "WSFS_CLIENT_SECRET", "value": ""},
            {"key": "INVALID_CLIENT_SECRET", "value": "invalid-secret"},
            {"key": "UNAUTHORIZED_CLIENT_ID", "value": "0000000000"},
        ],
    }


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)
    collection = generate_collection()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(collection, handle, indent=2)
        handle.write("\n")

    total_cases = len(collection["item"][0]["item"])
    print(f"Generated {total_cases} authenticate OLB security test cases at {output_path}")


if __name__ == "__main__":
    main()
