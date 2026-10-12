# Public UI presets. Keep model IDs out of persistence schemas.
# DeepSeek presets use the requested V4 model IDs.
MODEL_CATALOG = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "models": [
            "gpt-5.6-terra",
            "gpt-5.6-sol",
            "gpt-5.6-luna",
            "gpt-6.1-sol",
            "gpt-6-astra",
            "gpt-6-luna",
        ],
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "models": ["deepseek-v4-flash", "deepseek-v4-pro"],
    },
    "mimo": {
        "base_url": "https://api.xiaomimimo.com/v1",
        "models": ["mimo-v2.6-pro", "mimo-v2.6-flash"],
    },
    "custom": {"base_url": "", "models": []},
}
