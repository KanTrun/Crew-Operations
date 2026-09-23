"""Tai hien vong doi mode quanverse qua HTTP that: propose -> GET -> confirm -> GET.

MUC DICH: spec `quanverse.spec.ts` "manager walks mode propose -> confirm ->
deactivate" do: bam "De xuat" roi KY VONG nut "Duyet" hien ra. Spec that bai o
buoc do. Script nay kiem tra API tra gi sau `propose` de biet loi nam o API hay
o UI.

Chay: .venv\\Scripts\\python.exe scripts/probe_mode_lifecycle.py [mode]
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
MODE = sys.argv[1] if len(sys.argv) > 1 else "dem_nhac"


def req(method: str, path: str, token: str | None = None, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    if data is not None:
        r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw[:300]


def show_modes(label: str, token: str) -> dict | None:
    st, body = req("GET", "/api/v1/experience/quanverse/modes", token)
    if st != 200:
        print(f"  [{label}] GET modes -> {st} {str(body)[:150]}")
        return None
    row = next((m for m in body.get("modes", []) if m.get("mode") == MODE), None)
    print(
        f"  [{label}] active={row.get('active')}  proposal_status={row.get('proposal_status')!r}  "
        f"proposed_by={row.get('proposed_by')!r}"
    )
    return row


print(f"== Vong doi mode '{MODE}' ==")
st, b = req("POST", "/api/v1/auth/login", body={"username": "lan", "password": "nhipquan"})
print(f"  login -> {st}")
if st != 200:
    raise SystemExit(f"khong dang nhap duoc: {b}")
tok = b["token"]

row = show_modes("truoc", tok)
ui_state = (
    "deactivate (dang bat)" if row and row.get("active")
    else "confirm (cho duyet)" if row and row.get("proposal_status") and row["proposal_status"] != "confirmed"
    else "propose (dang tat)"
)
print(f"  => UI se hien nut: {ui_state}")

print(f"\n-- POST propose --")
st, b = req("POST", f"/api/v1/experience/quanverse/modes/{MODE}/propose", tok)
print(f"  -> {st}  proposal_status={b.get('proposal_status')!r}  confirmed={b.get('confirmed')}")

print(f"\n-- GET lai (day la thu UI doc) --")
row2 = show_modes("sau propose", tok)
waiting = bool(row2 and row2.get("proposal_status") and row2["proposal_status"] != "confirmed" and not row2.get("active"))
print(f"\n  UI co hien nut 'Duyet' khong? {waiting}")
if not waiting:
    print("  => LOI: sau propose, GET khong tra trang thai 'cho duyet'.")
    print("     Spec ky vong nut Duyet hien ra => spec do.")
else:
    print("  => dung: GET tra 'cho duyet'. Neu spec van do thi loi o tang UI.")
    print("\n-- POST confirm --")
    st, b = req("POST", f"/api/v1/experience/quanverse/modes/{MODE}/confirm", tok)
    print(f"  -> {st}  {str(b)[:120]}")
    show_modes("sau confirm", tok)
    print("\n-- POST deactivate (don dep) --")
    st, b = req("POST", f"/api/v1/experience/quanverse/modes/{MODE}/deactivate", tok)
    print(f"  -> {st}")
    show_modes("sau deactivate", tok)
