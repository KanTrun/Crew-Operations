"""Check actual fb_auto_send_enabled value and KV override."""
import os

# Load .env like the app does
from dotenv import load_dotenv

load_dotenv(override=False)

print("NHIPQUAN_FB_AUTO_SEND env =", repr(os.environ.get("NHIPQUAN_FB_AUTO_SEND")))

from ca_api.services.fb_moderation import _policy_runtime, fb_auto_send_enabled  # noqa: E402

print("KV fb_policy_runtime =", _policy_runtime())
print("fb_auto_send_enabled() =", fb_auto_send_enabled())