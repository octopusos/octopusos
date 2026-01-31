# NetworkOS Quick Start Guide

## 概述

NetworkOS 提供 Cloudflare Tunnel 管理功能，让你的 AgentOS 可以轻松暴露到公网。

## 前置条件

### 1. 安装 cloudflared

**macOS**:
```bash
brew install cloudflared
```

**Linux (Debian/Ubuntu)**:
```bash
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

**验证安装**:
```bash
cloudflared --version
```

### 2. 获取 Cloudflare Tunnel Token

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 进入 Zero Trust → Access → Tunnels
3. 点击 "Create a tunnel"
4. 选择 "Cloudflared"
5. 输入 tunnel 名称并保存
6. 复制生成的 Token（形如 `eyJhIjoiYWJjMTIzLi4uIn0=`）

## 快速开始

### 1. 创建 Tunnel

```bash
agentos networkos create \
  --name my-webui \
  --hostname my-app.trycloudflare.com \
  --target http://127.0.0.1:8080 \
  --token YOUR_CLOUDFLARE_TOKEN
```

**输出**:
```
✓ Created tunnel: a1b2c3d4-...
  Name: my-webui
  Public: my-app.trycloudflare.com
  Local: http://127.0.0.1:8080

Start with: agentos networkos start a1b2c3d4-...
```

### 2. 启动 Tunnel

```bash
agentos networkos start a1b2c3d4-...
```

**输出**:
```
✓ Started tunnel: my-webui
  Public URL: https://my-app.trycloudflare.com
  Local target: http://127.0.0.1:8080
```

### 3. 访问你的应用

打开浏览器访问: `https://my-app.trycloudflare.com`

## 常用命令

### 列出所有 Tunnel

```bash
agentos networkos list
```

### 查看 Tunnel 状态

```bash
agentos networkos status <tunnel-id>
```

### 查看日志

```bash
agentos networkos logs <tunnel-id> --limit 20
```

### 停止 Tunnel

```bash
agentos networkos stop <tunnel-id>
```

### 删除 Tunnel

```bash
agentos networkos delete <tunnel-id>
```

## 使用场景

### 场景 1: 暴露 WebUI

```bash
# 启动 WebUI
agentos --web

# 创建并启动 tunnel
agentos networkos create \
  --name agentos-webui \
  --hostname my-agentos.trycloudflare.com \
  --target http://127.0.0.1:8080 \
  --token YOUR_TOKEN

agentos networkos start <tunnel-id>
```

现在你可以从任何地方访问你的 AgentOS WebUI！

### 场景 2: 接收 Webhook

```bash
# 创建 webhook tunnel
agentos networkos create \
  --name webhook-receiver \
  --hostname webhooks.your-domain.com \
  --target http://127.0.0.1:9000 \
  --token YOUR_TOKEN

agentos networkos start <tunnel-id>
```

配置你的 webhook 提供商使用 `https://webhooks.your-domain.com`

### 场景 3: 开发环境共享

```bash
# 创建开发环境 tunnel
agentos networkos create \
  --name dev-share \
  --hostname dev.your-domain.com \
  --target http://127.0.0.1:3000 \
  --token YOUR_TOKEN

agentos networkos start <tunnel-id>
```

将 URL 分享给团队成员进行协作开发。

## 故障排查

### Tunnel 无法启动

**问题**: `cloudflared not found`

**解决**:
```bash
# 检查 cloudflared 是否安装
which cloudflared

# 如果未安装，参考前置条件安装
```

### Tunnel 频繁断开

**检查日志**:
```bash
agentos networkos logs <tunnel-id>
```

**可能原因**:
1. Token 无效或过期
2. 网络连接不稳定
3. 本地服务未运行

### 无法访问公网 URL

**检查状态**:
```bash
agentos networkos status <tunnel-id>
```

**验证**:
1. Tunnel 状态是否为 "up"
2. 本地服务是否正常运行
3. Cloudflare DNS 是否生效（可能需要几分钟）

## 最佳实践

### 1. 使用描述性名称

```bash
# ✅ 好的命名
agentos networkos create --name prod-webui ...
agentos networkos create --name staging-api ...

# ❌ 避免
agentos networkos create --name tunnel1 ...
```

### 2. 定期检查健康状态

```bash
# 创建 cron job
*/5 * * * * agentos networkos list | grep "down" && notify-admin
```

### 3. 保护敏感端点

- 使用 Cloudflare Access 添加认证
- 限制允许的 IP 范围
- 启用 HTTPS only

### 4. 监控日志

```bash
# 查看错误日志
agentos networkos logs <tunnel-id> | grep ERROR
```

## 高级功能

### 自定义域名

如果你有自己的域名：

1. 在 Cloudflare 添加你的域名
2. 创建 tunnel 时使用自定义域名
3. 配置 DNS CNAME 记录指向 tunnel

### TCP Tunnel

```bash
agentos networkos create \
  --name ssh-tunnel \
  --hostname ssh.your-domain.com \
  --target localhost:22 \
  --token YOUR_TOKEN \
  --mode tcp
```

## 限制和注意事项

1. **免费版限制**: Cloudflare 免费版有流量限制
2. **Token 安全**: Token 当前明文存储，注意保护
3. **进程管理**: Tunnel 进程随 AgentOS 关闭而停止
4. **网络依赖**: 需要稳定的互联网连接

## 获取帮助

```bash
# 查看命令帮助
agentos networkos --help
agentos networkos create --help

# 查看版本
agentos --version
```

## 相关文档

- [Cloudflare Tunnel 官方文档](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [NetworkOS 实现报告](../NETWORKOS_CLOUDFLARE_TUNNEL_IMPLEMENTATION_REPORT.md)
- [AgentOS 文档](https://github.com/your-org/agentos)

---

**最后更新**: 2026-02-01
**版本**: v0.1.0
