# 完整网页版部署

本部署包包含账号独立工作区、资料与附件、计划、助手、用户自有模型 API，以及每账号累计 5 次的可选公共模型试用。免登录入口 `/demo/` 是独立游客构建，使用示例资料和模拟回复。

需要 Linux 主机、Docker Engine 与 Docker Compose v2。当前只支持单实例、单 worker，不要横向扩容。准备至少 2 核、2 GiB 内存和足够的持久磁盘；应用容器默认上限 1.5 GiB，文档解析子进程另有限额。

## 配置与启动

在仓库根目录执行：

```sh
cp deploy/cloud/.env.example deploy/cloud/.env
docker run --rm python:3.12-slim-bookworm python -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

把生成的值填入 `.env` 中的 `XILIU_CLOUD_MASTER_KEY`，另行备份；这个加密密钥以后保持不变。将 `XILIU_CLOUD_ORIGIN` 设为精确公开地址，例如 `https://app.example.com`，不带末尾斜杠或路径。`XILIU_CLOUD_DOMAIN` 填同一域名，不带协议。

把 Cloudflare 域名或子域名的 A 记录指向主机公网 IPv4，开放主机的 80、443 端口，然后启动：

```sh
docker compose --env-file deploy/cloud/.env -f deploy/cloud/compose.yaml --profile https up -d --build --wait
```

Caddy 提供 HTTPS，并实时转发聊天流。若使用 Cloudflare 代理，使用 Full (strict) 回源加密模式。浏览器打开配置的公开地址即可注册；页面中的“先体验一下”无需账号。

没有服务器时，先在具有 Docker 的本机验收：把 Origin 改为 `http://127.0.0.1:8765`，`XILIU_CLOUD_LOCAL_HTTP=1`，启动时省略 `--profile https`。测试端口只绑定本机地址，不要改成公网监听。公开部署必须恢复 HTTPS 配置。

## 模型与试用

用户登录后在设置中填写自己的模型地址和 API Key。每个工作区的配置独立加密，不继承服务器个人模型配置。

站点管理员可选择填写 `XILIU_CLOUD_TRIAL_API_KEY`、`XILIU_CLOUD_TRIAL_MODEL` 和兼容的 `XILIU_CLOUD_TRIAL_BASE_URL`。不配置时，界面如实显示公共试用未开放，自有 API 仍可使用。试用按账号累计 5 次，全站每天默认 100 次、最多同时 4 次，每账号同时 1 次；配置的公共模型费用由管理员承担。

试用仅用于当前聊天，不保存为用户模型配置，也不供后台任务使用。连接失败或尚未开始生成时失败会返还；开始生成后停止、超时仍计次。进程中断后无法证明未生成的已发送请求保守计次；同一请求标识不重复推理。

## 权限、容量与网络

云端保留工作区业务操作，关闭宿主命令、任意文件、软件安装、自定义 Skill、stdio MCP 和本机桌面模型上传。联网搜索和 AI 热点来源目前显示未配置。GitHub 资讯与链接标题可用。桌面程序的本机能力保持原有行为。

应用以 UID 10001 运行，无 Linux capabilities，根文件系统只读；只有 `/data` 持久卷与受限临时目录可写。网络守卫单独持有 NET_ADMIN，应用不能修改规则。它与应用共享网络命名空间，在内核层拒绝内网、元数据与特殊 IPv4 地址，并拒绝新建 IPv6 出站连接，仅允许公网 HTTP(S)、Docker DNS 和本机健康检查。API 地址需要可访问的公网 IPv4；域名同时有 A/AAAA 时优先使用校验后的 IPv4。模型与向量客户端还逐次校验全部 DNS 结果并连接固定 IP，保留正确 TLS 主机名。

默认每账号工作区 100 MiB，单附件 20 MiB，每账号同时 2 段聊天、8 个请求，最多 20 个自动任务。公共聊天有输入、输出、调用次数和时长上限；过长上下文提示压缩或新建对话。初期注册容量默认 100 个账号，可通过配置关闭注册。升级容量前应重新评估资源和备份策略。

## 管理、备份与升级

```sh
docker compose --env-file deploy/cloud/.env -f deploy/cloud/compose.yaml exec app python -m xiliu.cloud.admin reset-password username
docker compose --env-file deploy/cloud/.env -f deploy/cloud/compose.yaml logs --tail 80 app
```

升级前停止写入并备份完整数据卷及独立保存的主密钥。详见[账号恢复与同步基础](cloud-operations.md)。恢复文件后确保 UID/GID 10001 可以读写数据卷。不要执行 `down -v` 删除真实资料卷；CI 仅对一次性验收卷使用它。

当前未实现桌面登录、双向同步和离线冲突合并，只保留稳定工作区身份、实体版本及删除记录。GitHub Pages 原演示站继续保留，不会变成此后端服务。

## 验收

GitHub Actions 的 `Verify cloud deployment` 构建实际镜像，创建两个账号验证资料/附件/计划隔离、游客静态资源、未配置试用、注销、同卷重启、备份恢复到新卷及真实网络出口。成功运行会提供 `xiliu-cloud-source` 源码部署包。当前机器未安装 Docker，本机代码与浏览器测试不能替代该容器验收。

配置依据：[Compose 服务与共享网络命名空间](https://docs.docker.com/reference/compose-file/services/)、[多阶段镜像构建](https://docs.docker.com/build/building/multi-stage/)。
