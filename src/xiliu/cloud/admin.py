"""Local administration; passwords are prompted and never accepted in command arguments."""

import argparse
import getpass

from xiliu.cloud.config import CloudConfig
from xiliu.cloud.identity import IdentityStore


def main():
    parser = argparse.ArgumentParser(description="息流云端账号管理")
    parser.add_argument("operation", choices=["create", "reset-password"])
    parser.add_argument("username")
    args = parser.parse_args()
    password = getpass.getpass("新密码：")
    if password != getpass.getpass("再次输入："):
        parser.error("两次密码不一致。")
    config = CloudConfig.from_env()
    store = IdentityStore(config.data_dir, max_users=config.max_users)
    if args.operation == "create":
        store.register(args.username, password)
    else:
        store.reset_password(args.username, password)
    print("账号已更新。")


if __name__ == "__main__":
    main()
