# Public UI presets. Keep model IDs out of persistence schemas.
# DeepSeek canonical Flash name checked against official docs on 2026-10-07.
MODEL_CATALOG = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-5.6-terra", "gpt-5.6-sol", "gpt-5.6-luna"],
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "models": ["deepseek-flash", "deepseek-v4-pro", "deepseek-v4-flash"],
    },
}
