#!/usr/bin/env python3
"""Generate an auth-focused security test suite from a Postman collection."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


UNAUTHORIZED_STATUS_SCRIPT = [
    'pm.test("Request is rejected", function () {',
    "  pm.expect([401, 403]).to.include(pm.response.code);",
    "});",
]

UNAUTHORIZED_OR_NOT_FOUND_SCRIPT = [
    'pm.test("Unauthorized object access is blocked", function () {',
    "  pm.expect([401, 403, 404]).to.include(pm.response.code);",
    "});",
]

NO_INTERNAL_ERROR_SCRIPT = [
    'pm.test("No internal server error", function () {',
    "  pm.expect(pm.response.code).to.not.equal(500);",
    "});",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an auth/authorization security collection from a Postman collection."
    )
    parser.add_argument("--input", required=True, help="Path to source Postman collection")
    parser.add_argument("--output", required=True, help="Path to generated security collection")
    return parser.parse_args()


def flatten_request_items(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    requests: List[Dict[str, Any]] = []
    for item in items:
        if "request" in item:
            requests.append(item)
        for child in item.get("item", []):
            requests.extend(flatten_request_items([child]))
    return requests


def clean_headers(headers: List[Dict[str, Any]], header_key: str) -> List[Dict[str, Any]]:
    key = header_key.lower()
    return [header for header in headers if header.get("key", "").lower() != key]


def upsert_header(headers: List[Dict[str, Any]], header_key: str, value: str) -> List[Dict[str, Any]]:
    cleaned = clean_headers(headers, header_key)
    cleaned.append({"key": header_key, "value": value, "type": "text"})
    return cleaned


def has_object_reference(url: Any) -> bool:
    if isinstance(url, str):
        lowered = url.lower()
        return ":clientid" in lowered or ":accountnumber" in lowered

    raw = str(url.get("raw", "")).lower()
    if ":clientid" in raw or ":accountnumber" in raw:
        return True

    for variable in url.get("variable", []):
        key = str(variable.get("key", "")).lower()
        if key in {"clientid", "accountnumber"}:
            return True

    return False


def tamper_object_reference(url: Any) -> Any:
    tampered = copy.deepcopy(url)
    if not isinstance(tampered, dict):
        return tampered

    for variable in tampered.get("variable", []):
        key = str(variable.get("key", "")).lower()
        if key == "clientid":
            variable["value"] = "{{UNAUTHORIZED_CLIENT_ID}}"
        elif key == "accountnumber":
            variable["value"] = "{{UNAUTHORIZED_ACCOUNT_NUMBER}}"

    return tampered


def build_test_event(exec_lines: List[str]) -> List[Dict[str, Any]]:
    return [
        {
            "listen": "test",
            "script": {
                "type": "text/javascript",
                "exec": exec_lines + NO_INTERNAL_ERROR_SCRIPT,
            },
        }
    ]


def build_variant_item(
    *,
    source_name: str,
    base_request: Dict[str, Any],
    variant_name: str,
    headers: List[Dict[str, Any]],
    test_script: List[str],
    tamper_url: bool = False,
) -> Dict[str, Any]:
    request = copy.deepcopy(base_request)
    request["header"] = headers
    if tamper_url:
        request["url"] = tamper_object_reference(request.get("url", {}))

    return {
        "name": f"{source_name} :: {variant_name}",
        "request": request,
        "event": build_test_event(test_script),
        "response": [],
    }


def generate_security_collection(source: Dict[str, Any]) -> Dict[str, Any]:
    request_items = flatten_request_items(source.get("item", []))

    auth_negative_items: List[Dict[str, Any]] = []
    bola_items: List[Dict[str, Any]] = []

    for item in request_items:
        source_name = item.get("name", "Unnamed Request")
        base_request = item.get("request", {})
        base_headers = copy.deepcopy(base_request.get("header", []))

        missing_client_id = clean_headers(base_headers, "client_id")
        auth_negative_items.append(
            build_variant_item(
                source_name=source_name,
                base_request=base_request,
                variant_name="Missing client_id",
                headers=missing_client_id,
                test_script=UNAUTHORIZED_STATUS_SCRIPT,
            )
        )

        missing_client_secret = clean_headers(base_headers, "client_secret")
        auth_negative_items.append(
            build_variant_item(
                source_name=source_name,
                base_request=base_request,
                variant_name="Missing client_secret",
                headers=missing_client_secret,
                test_script=UNAUTHORIZED_STATUS_SCRIPT,
            )
        )

        invalid_client_secret = upsert_header(
            base_headers, "client_secret", "{{INVALID_CLIENT_SECRET}}"
        )
        auth_negative_items.append(
            build_variant_item(
                source_name=source_name,
                base_request=base_request,
                variant_name="Invalid client_secret",
                headers=invalid_client_secret,
                test_script=UNAUTHORIZED_STATUS_SCRIPT,
            )
        )

        empty_credentials = upsert_header(
            upsert_header(base_headers, "client_id", ""), "client_secret", ""
        )
        auth_negative_items.append(
            build_variant_item(
                source_name=source_name,
                base_request=base_request,
                variant_name="Empty auth headers",
                headers=empty_credentials,
                test_script=UNAUTHORIZED_STATUS_SCRIPT,
            )
        )

        if has_object_reference(base_request.get("url", {})):
            tampered_headers = copy.deepcopy(base_headers)
            bola_items.append(
                build_variant_item(
                    source_name=source_name,
                    base_request=base_request,
                    variant_name="BOLA tampered object reference",
                    headers=tampered_headers,
                    test_script=UNAUTHORIZED_OR_NOT_FOUND_SCRIPT,
                    tamper_url=True,
                )
            )

    generated = {
        "info": {
            "_postman_id": "deaa6cd3-0427-4e57-a59f-f7fdd0f27db4",
            "name": f'{source.get("info", {}).get("name", "API")} - Security Auth Suite',
            "description": (
                "Generated security regression suite focused on authentication and "
                "object authorization negative tests."
            ),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": [
            {
                "name": "Auth Header Negative Tests",
                "item": auth_negative_items,
            },
            {
                "name": "Object Authorization (BOLA) Tests",
                "item": bola_items,
            },
        ],
        "event": [],
        "variable": [
            {"key": "BASE_ENDPOINT", "value": "https://api.example.com"},
            {"key": "WSFS_CLIENT_ID", "value": ""},
            {"key": "WSFS_CLIENT_SECRET", "value": ""},
            {"key": "INVALID_CLIENT_SECRET", "value": "invalid-secret"},
            {"key": "UNAUTHORIZED_CLIENT_ID", "value": "0000000000"},
            {"key": "UNAUTHORIZED_ACCOUNT_NUMBER", "value": "000000000"},
        ],
    }

    return generated


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    with input_path.open("r", encoding="utf-8") as source_file:
        source_collection = json.load(source_file)

    generated_collection = generate_security_collection(source_collection)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(generated_collection, output_file, indent=2)
        output_file.write("\n")

    auth_count = len(generated_collection["item"][0]["item"])
    bola_count = len(generated_collection["item"][1]["item"])
    print(
        f"Generated security suite at {output_path} "
        f"(auth tests: {auth_count}, bola tests: {bola_count})"
    )


if __name__ == "__main__":
    main()
