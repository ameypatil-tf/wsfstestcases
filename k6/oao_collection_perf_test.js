import http from "k6/http";
import { check, sleep } from "k6";
import { SharedArray } from "k6/data";

const MAX_RESPONSE_MS = Number(__ENV.MAX_RESPONSE_MS || 2000);
const P95_RESPONSE_MS = Number(__ENV.P95_RESPONSE_MS || 3000);
const THINK_TIME_MIN = Number(__ENV.THINK_TIME_MIN || 0.5);
const THINK_TIME_MAX = Number(__ENV.THINK_TIME_MAX || 2.0);
const BASE_ENDPOINT = (__ENV.BASE_ENDPOINT || "").replace(/\/+$/, "");
const REQUEST_NAME_PATTERN = __ENV.REQUEST_NAME_PATTERN || "";

const requests = new SharedArray("oao-postman-requests", () =>
  JSON.parse(open("./oao_requests.json")),
);

let requestNameRegex = null;
if (REQUEST_NAME_PATTERN) {
  try {
    requestNameRegex = new RegExp(REQUEST_NAME_PATTERN);
  } catch (error) {
    throw new Error(
      `Invalid REQUEST_NAME_PATTERN regex: "${REQUEST_NAME_PATTERN}". ${String(error)}`,
    );
  }
}

const selectedRequests = requestNameRegex
  ? requests.filter((requestDefinition) => requestNameRegex.test(requestDefinition.name))
  : requests;

function parseVuCount(value, fallback) {
  const count = Number(value || fallback);
  return Number.isFinite(count) && count >= 0 ? count : fallback;
}

function randomThinkTimeSeconds() {
  const min = Math.max(0, THINK_TIME_MIN);
  const max = Math.max(min, THINK_TIME_MAX);
  return min + Math.random() * (max - min);
}

function substituteEnvironmentVariables(value) {
  if (typeof value !== "string") {
    return value;
  }

  return value
    .replaceAll("{{BASE_ENDPOINT}}", BASE_ENDPOINT)
    .replaceAll("{{WSFS_CLIENT_ID}}", __ENV.WSFS_CLIENT_ID || "")
    .replaceAll("{{WSFS_CLIENT_SECRET}}", __ENV.WSFS_CLIENT_SECRET || "");
}

function normalizeUrl(rawUrl) {
  let populated = substituteEnvironmentVariables(rawUrl);

  if (
    BASE_ENDPOINT &&
    populated.startsWith(BASE_ENDPOINT) &&
    populated.length > BASE_ENDPOINT.length &&
    populated.charAt(BASE_ENDPOINT.length) !== "/"
  ) {
    populated = `${BASE_ENDPOINT}/${populated.slice(BASE_ENDPOINT.length)}`;
  }

  return populated.replace(/([^:]\/)\/+/g, "$1");
}

function buildHeaders(requestHeaders, hasBody) {
  const headers = {};
  for (const [key, value] of Object.entries(requestHeaders || {})) {
    headers[key] = substituteEnvironmentVariables(value);
  }

  if (
    hasBody &&
    !Object.keys(headers).some(
      (headerName) => headerName.toLowerCase() === "content-type",
    )
  ) {
    headers["Content-Type"] = "application/json";
  }

  return headers;
}

export const options = {
  stages: [
    {
      duration: __ENV.RAMP_UP_DURATION || "1m",
      target: parseVuCount(__ENV.RAMP_UP_VUS, 5),
    },
    {
      duration: __ENV.STEADY_DURATION || "3m",
      target: parseVuCount(__ENV.STEADY_VUS, 5),
    },
    {
      duration: __ENV.RAMP_DOWN_DURATION || "1m",
      target: 0,
    },
  ],
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: [`p(95)<${P95_RESPONSE_MS}`],
    checks: ["rate>0.95"],
  },
};

export function setup() {
  if (!BASE_ENDPOINT) {
    throw new Error(
      "BASE_ENDPOINT is required. Example: BASE_ENDPOINT=https://api.example.com",
    );
  }

  if (selectedRequests.length === 0) {
    throw new Error(
      `No requests matched REQUEST_NAME_PATTERN="${REQUEST_NAME_PATTERN}".`,
    );
  }
}

export default function () {
  for (const requestDefinition of selectedRequests) {
    const method = requestDefinition.method.toUpperCase();
    const hasBody = requestDefinition.body !== null && requestDefinition.body !== undefined;
    const body = hasBody ? substituteEnvironmentVariables(requestDefinition.body) : null;
    const url = normalizeUrl(requestDefinition.rawUrl);

    const response = http.request(method, url, body, {
      headers: buildHeaders(requestDefinition.headers, hasBody),
      tags: {
        request_name: requestDefinition.name,
      },
    });

    const checksPassed = check(response, {
      [`${requestDefinition.name} status is 2xx/3xx`]: (r) =>
        r.status >= 200 && r.status < 400,
      [`${requestDefinition.name} response time under ${MAX_RESPONSE_MS}ms`]: (r) =>
        r.timings.duration <= MAX_RESPONSE_MS,
    });

    if (!checksPassed) {
      console.error(
        `[${requestDefinition.name}] status=${response.status} duration_ms=${response.timings.duration} url=${url}`,
      );
    }

    sleep(randomThinkTimeSeconds());
  }
}
