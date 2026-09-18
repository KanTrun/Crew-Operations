r"""Xác nhận lại các item FAIL trước đó: 8, 27, 28, 29."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://localhost:8000"

def req(method, path, token=None, body=None, timeout=60, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE+path, data=data, method=method)
    if data is not None:
        r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    for k, v in (headers or {}).items():
        r.add_header(k, v)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8", "replace"))
        except Exception:
            return e.code, {}

def login(user):
    st, body = req("POST", "/api/v1/auth/login", body={"username": user, "password": "nhipquan"})
    assert st == 200, f"login {user}: {st} {body}"
    return body["token"]

lan = login("lan")

# Item 8: ANALYZE_WASTE với từ đúng "hao hụt"
st, body = req("POST", "/api/v1/copilot/message", token=lan,
               body={"message": "Báo cáo hao hụt sữa hôm nay thế nào?", "channel": "web"})
intent = body.get("intent") if isinstance(body, dict) else None
print(f"8 ANALYZE_WASTE: st={st} intent={intent}")

# Item 27-29: catchment-survey với Idempotency-Key
st, body = req("POST", "/api/v1/market/catchment-survey", token=lan,
               body={"latitude": 10.8231, "longitude": 106.6297, "core_category": "com_suon_bi_cha"},
               timeout=30, headers={"Idempotency-Key": "verify-plan-260917-b"})
job_id = body.get("data", {}).get("job_id") if isinstance(body, dict) else None
print(f"27 catchment-survey: st={st} job_id={job_id} body={json.dumps(body, ensure_ascii=False)[:300]}")
if job_id:
    st, body = req("GET", f"/api/v1/market/catchment-survey/{job_id}", token=lan)
    print(f"28 job status: st={st} body={json.dumps(body, ensure_ascii=False)[:300]}")
    st, body = req("GET", f"/api/v1/market/catchment-survey/{job_id}/result", token=lan)
    print(f"29 job result: st={st} body={json.dumps(body, ensure_ascii=False)[:300]}")