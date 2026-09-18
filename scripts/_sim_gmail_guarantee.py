"""Verify the AI always asks for Gmail at least once before booking (or customer refused/provided)."""
import os
import tempfile

os.environ["NHIPQUAN_DB"] = os.path.join(tempfile.mkdtemp(), "sim7.db")
os.environ["NHIPQUAN_AUTO_RESERVATION"] = "1"
os.environ["NHIPQUAN_SEED_DEMO"] = "1"

from ca_api.persist import init_db  # noqa: E402

init_db()

from ca_agents.ag_concierge import handle_reservation  # noqa: E402

GMAIL_KEYWORDS = ("gmail", "email", "địa chỉ gmail", "dia chi gmail")


def run_scenario(name, turns, phone):
    print(f"\n=== {name} ===")
    state = None
    gmail_asked = 0
    for i, text in enumerate(turns, 1):
        text = text.replace("PHONE", phone)
        t = handle_reservation(text, psid=f"sim_{name}", session_state=state)
        reply = t.suggested_reply.lower()
        if any(k in reply for k in GMAIL_KEYWORDS):
            gmail_asked += 1
        print(f"  T{i} [{text[:40]}] -> {t.action_type} | gmail_asked_so_far={gmail_asked}")
        print(f"      reply: {t.suggested_reply[:100]}")
        state = t.extracted_data
    booked = state.get("status") == "confirmed"
    print(f"  => BOOKED={booked} | GMAIL_ASKED_TOTAL={gmail_asked}")
    return booked, gmail_asked


results = []

# Scenario 1: normal flow with gmail
b, g = run_scenario("normal", [
    "Mình muốn đặt bàn 4 người lúc 19h tối nay",
    "SĐT PHONE",
    "email khachhang@gmail.com, đúng rồi",
], "0912345678")
results.append(("normal", b, g))

# Scenario 2: no gmail, refused in turn 3
b, g = run_scenario("nogmail", [
    "Mình muốn đặt bàn 4 người lúc 19h tối nay",
    "SĐT PHONE",
    "mình không có gmail",
    "Đúng rồi em ơi",
], "0912345679")
results.append(("nogmail", b, g))

# Scenario 3: no gmail refused in turn 2 (same turn as phone)
b, g = run_scenario("nogmail_turn2", [
    "Mình muốn đặt bàn 4 người lúc 19h tối nay",
    "SĐT PHONE, mình không có gmail",
], "0912345680")
results.append(("nogmail_turn2", b, g))

# Scenario 4: all info + no gmail in first message
b, g = run_scenario("allinfo_nogmail", [
    "đặt bàn 4 người 19h tối nay, SĐT PHONE, mình không có gmail",
], "0912345681")
results.append(("allinfo_nogmail", b, g))

print("\n\n========== SUMMARY ==========")
for name, booked, gmail_asked in results:
    # Guarantee: booked AND (gmail asked at least once OR customer refused/provided)
    print(f"  {name:20s} booked={booked} gmail_asked={gmail_asked}")