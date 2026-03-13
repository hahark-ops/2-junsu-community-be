import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  stages: [
    { duration: "1m", target: 20 },
    { duration: "3m", target: 20 },
    { duration: "1m", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<1000"],
  },
};

const BASE_URL = __ENV.BASE_URL;

if (!BASE_URL) {
  throw new Error("BASE_URL environment variable is required");
}

export default function () {
  const responses = [
    http.get(`${BASE_URL}/`),
    http.get(`${BASE_URL}/login.html`),
    http.get(`${BASE_URL}/v1/posts`),
  ];

  responses.forEach((response) => {
    check(response, {
      "status is 200": (r) => r.status === 200,
    });
  });

  sleep(1);
}
