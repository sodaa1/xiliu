from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class CloudConfig:
    data_dir: Path
    public_origin: str
    master_key: str = field(repr=False)
    secure_cookies: bool = True
    session_seconds: int = 86400
    signup_enabled: bool = True
    max_users: int = 100
    login_limit: int = 10
    signup_limit: int = 5
    trial_daily_limit: int = 100

    def __post_init__(self):
        parsed = urlsplit(self.public_origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.netloc != parsed.netloc.lower()
        ):
            raise ValueError("公开地址必须是完整且不含路径的 Origin。")
        if (parsed.scheme != "https" or not self.secure_cookies) and (
            parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or self.secure_cookies
        ):
            raise ValueError("公开部署必须使用 HTTPS 和安全 Cookie。")
        try:
            decoded = base64.urlsafe_b64decode(self.master_key.encode("ascii"))
        except (ValueError, UnicodeError):
            decoded = b""
        if len(decoded) != 32:
            raise ValueError("必须提供有效的 32 字节加密主密钥。")
        if (
            min(
                self.session_seconds,
                self.max_users,
                self.login_limit,
                self.signup_limit,
                self.trial_daily_limit,
            )
            < 1
        ):
            raise ValueError("云端限制必须为正整数。")
        object.__setattr__(self, "data_dir", self.data_dir.resolve())

    @classmethod
    def from_env(cls) -> CloudConfig:
        return cls(
            data_dir=Path(os.environ.get("XILIU_CLOUD_DATA_DIR", "/data")),
            public_origin=os.environ.get("XILIU_CLOUD_ORIGIN", ""),
            master_key=os.environ.get("XILIU_CLOUD_MASTER_KEY", ""),
            secure_cookies=os.environ.get("XILIU_CLOUD_LOCAL_HTTP", "0") != "1",
            session_seconds=int(os.environ.get("XILIU_CLOUD_SESSION_SECONDS", "86400")),
            signup_enabled=os.environ.get("XILIU_CLOUD_SIGNUP", "1") == "1",
            max_users=int(os.environ.get("XILIU_CLOUD_MAX_USERS", "100")),
        )
