"""Platform-agnostic bot config."""

import os

AUTOGPT_FRONTEND_URL: str = os.getenv(
    "AUTOGPT_FRONTEND_URL", "https://platform.agpt.co"
)

# Cache TTL for AutoPilot session IDs (per channel/thread)
SESSION_TTL = 86400  # 24 hours
