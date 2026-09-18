"""Test real flow via process_fb_message: does intent get detected as dat_ban, and is gmail asked?"""
import asyncio
import os
import tempfile

os.environ["NHIPQUAN_DB"] = os.path.join(tempfile.mkdtemp(), "sim8.db")
os.environ["NHIPQUAN_AUTO_RESERVATION"] = "1"
os.environ["NHIPQUAN_SEED_DEMO"] = "1"

from ca_api.persist import init_db  # noqa: E402

init_db()

from ca_agents.ag_fbpage import FBMessageInput, process_fb_message  # noqa: E402

GMAIL_KEYWORDS = ("gmail", "email", "địa chỉ gmail", "dia chi gmail")


async def run_turn(psid, text, state):
    out = await process_fb_message(
        FBMessageInput(psid=psid, text=text, message_id=f"m_{psid}_{len(state or [])}", timestamp=float(len(state or []))),
        customer_profile={"psid": psid, "reservation_state": state} if state else {"psid": psid},
    )
    return out


async def scenario(name, turns):
    print(f"\n=== {name} ===")
    state = None
    gmail_asked = 0
    for i, text in enumerate(turns, 1):
        out = await run_turn(f"sim_{name}", text, state)
        reply = (out.response or out.suggested_reply or "").lower()
        if any(k in reply for k in GMAIL_KEYWORDS):
            gmail_asked += 1
        print(f"  T{i} [{text[:45]}] -> intent={out.intent} action={out.action} | gmail_asked={gmail_asked}")
        print(f"      reply: {(out.response or out.suggested_reply or '')[:110]}")
        state = out.reservation_state
    booked = bool(state and state.get("status") == "confirmed")
    print(f"  => BOOKED={booked} | GMAIL_ASKED_TOTAL={gmail_asked}")
    return booked, gmail_asked


async def main():
    results = []
    # Scenario 1: explicit "đặt bàn"
    b, g = await scenario("explicit", [
        "Mình muốn đặt bàn 4 người lúc 19h tối nay",
        "SĐT 0912345678",
        "Đúng rồi em ơi",
    ])
    results.append(("explicit", b, g))

    # Scenario 2: "giữ chỗ" (booking word)
    b, g = await scenario("giucho", [
        "Tối nay 4 người giữ chỗ giúp mình",
        "SĐT 0912345679",
        "ok",
    ])
    results.append(("giucho", b, g))

    # Scenario 3: casual "tối nay 4 người có chỗ không"
    b, g = await scenario("casual", [
        "tối nay 4 người có chỗ không",
        "SĐT 0912345680",
        "ok",
    ])
    results.append(("casual", b, g))

    # Scenario 4: "mình muốn đặt 1 bàn"
    b, g = await scenario("dat1ban", [
        "mình muốn đặt 1 bàn tối nay",
        "SĐT 0912345681",
        "ok",
    ])
    results.append(("dat1ban", b, g))

    print("\n\n========== SUMMARY ==========")
    for name, booked, gmail_asked in results:
        print(f"  {name:12s} booked={booked} gmail_asked={gmail_asked}")


asyncio.run(main())