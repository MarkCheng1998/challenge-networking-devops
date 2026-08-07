# IPSec VPN 自动化配置规划文档
## Fortigate 与 Palo Alto 之间的 IPSec VPN

> 本文档详细说明 Fortigate 与 Palo Alto 防火墙之间 IPSec VPN 配置自动化的完整规划方案。

---

## 1. 参数定义

### 1.1 网络拓扑

```
┌─────────────────┐                        ┌─────────────────┐
│   Site A        │                        │   Site B        │
│  Fortigate      │     IPSec Tunnel       │  Palo Alto      │
│  10.10.10.0/24  │◄──────────────────────►│  10.20.20.0/24  │
│  WAN: 200.1.1.1 │   169.255.1.0/30       │  WAN: 200.2.2.2 │
└─────────────────┘                        └─────────────────┘
```

### 1.2 WAN 接口地址

| 设备 | WAN IP | 角色 |
|------|--------|------|
| Fortigate (Site A) | 200.1.1.1/30 | VPN 隧道一端 |
| Palo Alto (Site B) | 200.2.2.2/30 | VPN 隧道另一端 |

### 1.3 本地网络

| 站点 | 本地网络 | 说明 |
|------|----------|------|
| Site A (Fortigate) | 10.10.10.0/24 | 数据网络 |
| Site B (Palo Alto) | 10.20.20.0/24 | 数据网络 |

### 1.4 隧道网络

| 参数 | 值 |
|------|----|
| 隧道子网 | 169.255.1.0/30 |
| Fortigate 隧道 IP | 169.255.1.1/30 |
| Palo Alto 隧道 IP | 169.255.1.2/30 |

### 1.5 Phase 1 参数（IKE）

| 参数 | 值 | 说明 |
|------|----|------|
| IKE 版本 | IKEv2 | 推荐使用 IKEv2 |
| 加密算法 | AES-256-CBC | 强加密 |
| 认证算法 | SHA-256 | 安全哈希 |
| DH 组 | Group 14 (2048-bit) | 安全的 Diffie-Hellman 组 |
| 认证方式 | Pre-Shared Key (PSK) | 预共享密钥 |
| PSK | `MySecurePSK!2024` | 示例密钥（实际部署应使用强密钥） |
| 生命周期 | 86400 秒 (24小时) | Phase 1 SA 生命周期 |

### 1.6 Phase 2 参数（IPSec）

| 参数 | 值 | 说明 |
|------|----|------|
| 加密算法 | AES-256-CBC | ESP 加密 |
| 认证算法 | SHA-256 | ESP 认证 |
| DH 组 | Group 14 (2048-bit) | PFS（完美前向保密） |
| 生命周期 | 3600 秒 (1小时) | Phase 2 SA 生命周期 |
| 模式 | Tunnel Mode | 隧道模式 |

---

## 2. 工具/API 识别

### 2.1 Fortigate 可用工具

| 工具/API | 说明 | 适用场景 |
|----------|------|----------|
| **FortiOS REST API** | FortiOS 7.0+ 原生 REST API，支持通过 HTTPS 管理 VPN 配置 | 推荐：自动化首选方案 |
| **FortiManager API** | 集中管理平台 API，适合大规模部署 | 大型企业多设备管理 |
| **SSH + CLI** | 通过 SSH 连接执行 CLI 命令（使用 Netmiko/Paramiko） | 兼容旧版本或不支持 API 的设备 |
| **Ansible** | 使用 `fortios` 模块集合 | 基础设施即代码 |
| **Terraform** | FortiOS Provider | 基础设施即代码 |

**FortiOS REST API 示例端点：**
```
POST https://<fortigate-ip>/api/v2/cmdb/vpn.ipsec/phase1-interface
POST https://<fortigate-ip>/api/v2/cmdb/vpn.ipsec/phase2-interface
POST https://<fortigate-ip>/api/v2/cmdb/firewall/policy
```

### 2.2 Palo Alto 可用工具

| 工具/API | 说明 | 适用场景 |
|----------|------|----------|
| **Palo Alto XML API** | 原生 XML API，支持所有配置操作 | 推荐：自动化首选方案 |
| **Panorama API** | 集中管理平台 API | 大规模部署 |
| **SSH + CLI** | 通过 SSH 连接执行 CLI 命令 | 兼容旧版本 |
| **Ansible** | 使用 `paloaltonetworks.panos` 模块集合 | 基础设施即代码 |
| **Terraform** | PAN-OS Provider | 基础设施即代码 |

**Palo Alto XML API 示例：**
```
https://<paloalto-ip>/api/?type=config&action=set&xpath=/config/devices/entry[@name='localhost.localdomain']/network/ike/gateway/entry[@name='VPN-GW']&element=<...>&key=<api-key>
```

### 2.3 推荐方案

**推荐使用 REST/XML API + SSH 回退的混合方案：**

1. **主方案**：通过 API 进行配置（FortiOS REST API + Palo Alto XML API）
2. **回退方案**：API 不可用时通过 SSH + CLI 执行配置
3. **验证**：两种方式都使用 SSH 执行验证命令

理由：
- API 方式更稳定、更安全（无需明文传输 CLI 命令）
- SSH 方式兼容性更好，适合旧版本设备
- 混合方案保证了灵活性和可靠性

---

## 3. 自动化步骤

### 3.1 前置准备

```
┌─────────────────────────────────┐
│ 1. 收集参数（IP、PSK、网络等）    │
│ 2. 验证设备可达性（ping/SSH）     │
│ 3. 获取 API Token / SSH 凭据     │
└──────────────┬──────────────────┘
               │
               ▼
```

### 3.2 Fortigate 侧配置步骤

```
┌──────────────────────────────────────────┐
│ Step 1: 创建地址对象                       │
│  - obj_local_net: 10.10.10.0/24          │
│  - obj_remote_net: 10.20.20.0/24         │
├──────────────────────────────────────────┤
│ Step 2: 配置 Phase 1 (IKE Gateway)        │
│  - 接口: wan1                             │
│  - 对端IP: 200.2.2.2                     │
│  - IKE版本: v2                            │
│  - 加密/认证/DH: AES-256/SHA-256/G14     │
│  - PSK认证                                │
├──────────────────────────────────────────┤
│ Step 3: 配置 Phase 2 (IPSec Proposal)     │
│  - 加密/认证: AES-256/SHA-256            │
│  - PFS: Group 14                         │
│  - 生命周期: 3600s                        │
│  - 源网络: 10.10.10.0/24                  │
│  - 目标网络: 10.20.20.0/24                │
├──────────────────────────────────────────┤
│ Step 4: 配置防火墙策略                     │
│  - 源: obj_local_net                      │
│  - 目的: obj_remote_net                   │
│  - 动作: ACCEPT                           │
│  - 出接口: VPN隧道接口                     │
├──────────────────────────────────────────┤
│ Step 5: 配置隧道接口IP                     │
│  - 接口: VPN-Tunnel                       │
│  - IP: 169.255.1.1/30                     │
├──────────────────────────────────────────┤
│ Step 6: 配置静态路由                       │
│  - 目标: 10.20.20.0/24                    │
│  - 下一跳: VPN-Tunnel 接口                 │
└──────────────────────────────────────────┘
```

### 3.3 Palo Alto 侧配置步骤

```
┌──────────────────────────────────────────┐
│ Step 1: 创建地址对象                       │
│  - obj_local_net: 10.20.20.0/24          │
│  - obj_remote_net: 10.10.10.0/24         │
├──────────────────────────────────────────┤
│ Step 2: 配置 IKE Crypto Profile           │
│  - 加密: AES-256                          │
│  - 认证: SHA-256                          │
│  - DH: Group 14                           │
│  - 生命周期: 86400s                        │
├──────────────────────────────────────────┤
│ Step 3: 配置 IKE Gateway                  │
│  - 对端IP: 200.1.1.1                     │
│  - 认证: PSK                              │
│  - IKE版本: IKEv2                         │
│  - 本地接口: ethernet1/1                  │
├──────────────────────────────────────────┤
│ Step 4: 配置 IPSec Crypto Profile         │
│  - 加密: AES-256                          │
│  - 认证: SHA-256                          │
│  - DH: Group 14 (PFS)                    │
│  - 生命周期: 3600s                        │
├──────────────────────────────────────────┤
│ Step 5: 配置 IPSec Tunnel                 │
│  - IKE Gateway: VPN-GW                   │
│  - IPSec Crypto Profile: VPN-Crypto      │
│  - 隧道接口: tunnel.1                     │
├──────────────────────────────────────────┤
│ Step 6: 配置隧道接口                       │
│  - 接口: tunnel.1                         │
│  - IP: 169.255.1.2/30                     │
│  - Virtual Router: default               │
│  - Security Zone: VPN-Zone               │
├──────────────────────────────────────────┤
│ Step 7: 配置静态路由                       │
│  - 目标: 10.10.10.0/24                    │
│  - 下一跳: tunnel.1                       │
├──────────────────────────────────────────┤
│ Step 8: 配置安全策略                       │
│  - 源Zone: VPN-Zone / 目的Zone: trust     │
│  - 源地址: obj_remote_net                 │
│  - 目的地址: obj_local_net                │
│  - 动作: allow                            │
│  (反向策略同理)                            │
├──────────────────────────────────────────┤
│ Step 9: Commit 配置                       │
│  - 提交所有变更到设备                      │
└──────────────────────────────────────────┘
```

### 3.4 自动化脚本流程图

```
START
  │
  ├──► 读取配置参数文件 (JSON/YAML)
  │
  ├──► Fortigate 配置模块
  │      ├── 登录获取 API Token
  │      ├── 创建地址对象
  │      ├── 配置 Phase 1 (IKE Gateway)
  │      ├── 配置 Phase 2 (IPSec Proposal)
  │      ├── 配置防火墙策略
  │      ├── 配置隧道接口IP
  │      ├── 配置静态路由
  │      └── 验证配置
  │
  ├──► Palo Alto 配置模块
  │      ├── 获取 API Key
  │      ├── 创建地址对象
  │      ├── 配置 IKE Crypto Profile
  │      ├── 配置 IKE Gateway
  │      ├── 配置 IPSec Crypto Profile
  │      ├── 配置 IPSec Tunnel
  │      ├── 配置隧道接口
  │      ├── 配置静态路由
  │      ├── 配置安全策略
  │      ├── Commit
  │      └── 验证配置
  │
  ├──► 全局验证
  │      ├── 检查隧道状态 (两端)
  │      ├── 测试连通性 (ping)
  │      └── 生成告警报告
  │
END
```

---

## 4. 跨厂商自动化注意事项

### 4.1 术语映射差异

| 概念 | Fortigate 术语 | Palo Alto 术语 |
|------|---------------|----------------|
| IKE Phase 1 | Phase 1 Interface | IKE Gateway + IKE Crypto Profile |
| IKE Phase 2 | Phase 2 Interface | IPSec Tunnel + IPSec Crypto Profile |
| 防火墙策略 | Firewall Policy | Security Policy |
| 地址对象 | Address | Address Object |
| 接口绑定 | 绑定到 VPN 接口 | 绑定到 Tunnel 接口 |
| 提交配置 | 自动生效 | 需要 Commit 操作 |
| 接口类型 | VPN 接口 | Tunnel 接口 (tunnel.X) |

### 4.2 关键挑战

1. **配置提交机制差异**：
   - Fortigate: API 调用后立即生效，无需额外提交
   - Palo Alto: 需要 `commit` 操作才能使配置生效
   - 解决方案：在 Palo Alto 侧自动化流程最后增加 commit 步骤

2. **API 格式差异**：
   - Fortigate: REST API，JSON 格式
   - Palo Alto: XML API，XML 格式
   - 解决方案：为每个厂商实现独立的 API 客户端模块

3. **隧道接口编号差异**：
   - Fortigate: 使用命名接口（如 "VPN-Tunnel"）
   - Palo Alto: 使用编号隧道接口（如 tunnel.1）
   - 解决方案：参数化接口命名，在配置模板中处理

4. **Phase 1/Phase 2 配置粒度差异**：
   - Fortigate: Phase 1 和 Phase 2 在单个接口配置中关联
   - Palo Alto: 需要分别创建 Crypto Profile、Gateway 和 Tunnel 对象
   - 解决方案：在自动化脚本中按厂商分别处理配置顺序

5. **IKE 提议顺序**：
   - 不同厂商的 IKE 提议匹配顺序可能不同
   - 需确保双方配置的加密参数完全一致
   - 解决方案：使用标准化参数配置模板，避免使用默认值

6. **NAT 穿透**：
   - 双方都需要启用 NAT-T
   - Fortigate: 默认启用
   - Palo Alto: 需要在 IKE Gateway 中启用
   - 解决方案：显式配置 NAT-T

### 4.3 安全注意事项

- PSK 不应硬编码在脚本中，应从环境变量或密钥管理服务读取
- API Token/Key 应定期轮换
- SSH 连接应使用密钥认证而非密码
- 所有自动化操作应记录审计日志
- 配置变更前应自动备份当前配置

---

## 5. 配置验证和告警策略

### 5.1 验证方法

#### Fortigate 验证命令

```bash
# 检查 IKE Phase 1 状态
diagnose vpn ike gateway list

# 检查 IPSec Phase 2 状态
diagnose vpn tunnel list

# 检查隧道接口
diagnose vpn tunnel stats

# 检查路由
diagnose ip route list

# Ping 测试
execute ping 169.255.1.2
execute ping source 10.10.10.1 10.20.20.1
```

#### Palo Alto 验证命令

```bash
# 检查 IKE Phase 1 状态
show vpn ike-sa

# 检查 IPSec Phase 2 状态
show vpn ipsec-sa

# 检查隧道接口
show interface tunnel.1

# 检查路由
show routing route

# Ping 测试
ping source 10.20.20.1 host 10.10.10.1
```

### 5.2 API 验证

#### Fortigate REST API 验证
```http
GET https://<fortigate-ip>/api/v2/monitor/vpn/ipsec
GET https://<fortigate-ip>/api/v2/monitor/vpn/ssl
```

#### Palo Alto XML API 验证
```http
https://<paloalto-ip>/api/?type=op&cmd=<show><vpn><ike-sa></ike-sa></vpn></show>&key=<api-key>
https://<paloalto-ip>/api/?type=op&cmd=<show><vpn><ipsec-sa></ipsec-sa></vpn></show>&key=<api-key>
```

### 5.3 验证检查清单

| 检查项 | 方法 | 期望结果 | 告警级别 |
|--------|------|----------|----------|
| Phase 1 SA 建立 | API/CLI 查询 | 状态为 established/up | 严重 |
| Phase 2 SA 建立 | API/CLI 查询 | 状态为 up | 严重 |
| 隧道接口UP | CLI 查询 | 接口状态为 up | 严重 |
| 隧道IP连通性 | Ping 隧道IP | 100% 成功率 | 严重 |
| 本地网络连通性 | Ping 对端本地IP | 100% 成功率 | 严重 |
| 路由表正确 | CLI 查询路由 | 目标网络通过隧道接口可达 | 警告 |
| 防火墙策略正确 | API/CLI 查询 | 允许双向流量 | 警告 |
| 配置参数匹配 | 对比双方配置 | Phase 1/2 参数一致 | 严重 |
| 无多余配置 | 对比期望配置 | 无非标准配置 | 信息 |

### 5.4 告警机制

```
验证流程:
┌──────────────┐     ┌──────────────────┐     ┌───────────────┐
│ 执行验证命令  │────►│ 对比期望状态      │────►│ 生成告警报告   │
│ (API/CLI)    │    │ (参数/状态匹配)   │     │ (分级告警)     │
└──────────────┘     └──────────────────┘     └───────┬───────┘
                                                      │
                                    ┌─────────────────┼─────────────────┐
                                    │                 │                 │
                                    ▼                 ▼                 ▼
                              ┌──────────┐     ┌──────────┐     ┌──────────┐
                              │ 严重告警  │     │ 警告告警  │     │ 信息通知  │
                              │ (邮件+   │     │ (邮件    │     │ (日志    │
                              │  日志)   │     │  通知)   │     │  记录)   │
                              └──────────┘     └──────────┘     └──────────┘
```

**告警级别定义：**

- **严重 (Critical)**: VPN 隧道无法建立、Phase 1/2 SA 失败、连通性测试失败
  - 触发动作：发送告警邮件 + 写入错误日志 + 脚本退出码 1
- **警告 (Warning)**: 路由缺失、策略不完整、参数轻微偏差
  - 触发动作：发送通知邮件 + 写入警告日志
- **信息 (Info)**: 发现非标准配置、额外对象存在
  - 触发动作：仅写入信息日志

### 5.5 回退策略

如果自动化配置后验证失败：

1. **自动回退**：脚本从备份恢复配置
2. **手动回退**：发送告警邮件，附带手动回退步骤
3. **保留备份**：每次配置变更前自动备份当前配置

---

## 6. 附录

### 6.1 配置参数模板 (JSON)

```json
{
  "fortigate": {
    "host": "200.1.1.1",
    "api_token": "<fortigate-api-token>",
    "wan_interface": "wan1",
    "tunnel_name": "VPN-to-PA",
    "tunnel_ip": "169.255.1.1",
    "tunnel_subnet": "255.255.255.252",
    "local_subnet": "10.10.10.0/24",
    "remote_subnet": "10.20.20.0/24",
    "remote_peer": "200.2.2.2",
    "psk": "MySecurePSK!2024",
    "phase1": {
      "ike_version": 2,
      "encryption": "aes256",
      "authentication": "sha256",
      "dh_group": 14,
      "lifetime": 86400
    },
    "phase2": {
      "encryption": "aes256",
      "authentication": "sha256",
      "dh_group": 14,
      "lifetime": 3600
    }
  },
  "paloalto": {
    "host": "200.2.2.2",
    "api_key": "<paloalto-api-key>",
    "wan_interface": "ethernet1/1",
    "tunnel_interface": "tunnel.1",
    "tunnel_ip": "169.255.1.2",
    "tunnel_subnet": "255.255.255.252",
    "local_subnet": "10.20.20.0/24",
    "remote_subnet": "10.10.10.0/24",
    "remote_peer": "200.1.1.1",
    "psk": "MySecurePSK!2024",
    "ike_crypto_profile": "VPN-IKE-Crypto",
    "ike_gateway": "VPN-GW",
    "ipsec_crypto_profile": "VPN-IPSec-Crypto",
    "ipsec_tunnel": "VPN-Tunnel",
    "vpn_zone": "VPN-Zone",
    "phase1": {
      "ike_version": "ikev2",
      "encryption": "aes-256-cbc",
      "authentication": "sha256",
      "dh_group": "group14",
      "lifetime": 86400
    },
    "phase2": {
      "encryption": "aes-256-cbc",
      "authentication": "sha256",
      "dh_group": "group14",
      "lifetime": 3600
    }
  }
}
```

### 6.2 示例 CLI 配置命令

#### Fortigate CLI 配置

```
# 地址对象
config firewall address
    edit "obj_local_net"
        set subnet 10.10.10.0 255.255.255.0
    next
    edit "obj_remote_net"
        set subnet 10.20.20.0 255.255.255.0
    next
end

# Phase 1
config vpn ipsec phase1-interface
    edit "VPN-to-PA"
        set interface "wan1"
        set ike-version 2
        set peertype any
        set proposal aes256-sha256-dh14
        set remote-gw 200.2.2.2
        set psksecret MySecurePSK!2024
    next
end

# Phase 2
config vpn ipsec phase2-interface
    edit "VPN-to-PA-P2"
        set phase1name "VPN-to-PA"
        set proposal aes256-sha256
        set dhgrp 14
        set src-subnet 10.10.10.0 255.255.255.0
        set dst-subnet 10.20.20.0 255.255.255.0
    next
end

# 隧道接口IP
config system interface
    edit "VPN-to-PA"
        set ip 169.255.1.1 255.255.255.252
    next
end

# 防火墙策略
config firewall policy
    edit 1
        set srcintf "VPN-to-PA"
        set dstintf "internal"
        set srcaddr "obj_remote_net"
        set dstaddr "obj_local_net"
        set action accept
        set schedule "always"
        set service "ALL"
    next
    edit 2
        set srcintf "internal"
        set dstintf "VPN-to-PA"
        set srcaddr "obj_local_net"
        set dstaddr "obj_remote_net"
        set action accept
        set schedule "always"
        set service "ALL"
    next
end

# 静态路由
config router static
    edit 1
        set dst 10.20.20.0 255.255.255.0
        set device "VPN-to-PA"
    next
end
```

#### Palo Alto CLI 配置

```
# 地址对象
set network address obj_local_net ip-netmask 10.20.20.0/24
set network address obj_remote_net ip-netmask 10.10.10.0/24

# IKE Crypto Profile
set network ike crypto-profiles ike-crypto-profiles VPN-IKE-Crypto encryption aes-256-cbc
set network ike crypto-profiles ike-crypto-profiles VPN-IKE-Crypto authentication sha256
set network ike crypto-profiles ike-crypto-profiles VPN-IKE-Crypto dh-group group14
set network ike crypto-profiles ike-crypto-profiles VPN-IKE-Crypto lifetime hours 24

# IKE Gateway
set network ike gateway VPN-GW authentication pre-shared-key key MySecurePSK!2024
set network ike gateway VPN-GW protocol ikev2 ike-crypto-profile VPN-IKE-Crypto
set network ike gateway VPN-GW protocol ikev2 dpd enable
set network ike gateway VPN-GW peer-address ip 200.1.1.1
set network ike gateway VPN-GW local-address interface ethernet1/1

# IPSec Crypto Profile
set network ipsec-crypto-profiles ipsec-crypto-profiles VPN-IPSec-Crypto esp encryption aes-256-cbc
set network ipsec-crypto-profiles ipsec-crypto-profiles VPN-IPSec-Crypto esp authentication sha256
set network ipsec-crypto-profiles ipsec-crypto-profiles VPN-IPSec-Crypto dh-group group14
set network ipsec-crypto-profiles ipsec-crypto-profiles VPN-IPSec-Crypto lifetime hours 1

# IPSec Tunnel
set network tunnel ipsec VPN-Tunnel auto-key ike-gateway VPN-GW
set network tunnel ipsec VPN-Tunnel auto-key ipsec-crypto-profile VPN-IPSec-Crypto
set network tunnel ipsec VPN-Tunnel tunnel-interface tunnel.1

# 隧道接口
set network interface tunnel tunnel.1 ip 169.255.1.2/30
set network interface tunnel tunnel.1 virtual-router default

# 安全区域
set zone VPN-Zone network layer3 tunnel.1

# 静态路由
set network virtual-router default routing-table ip static-route 10.10.10.0/24 destination 10.10.10.0/24
set network virtual-router default routing-table ip static-route 10.10.10.0/24 interface tunnel.1

# 安全策略
set rulebase security rules Allow-VPN-Inbound from VPN-Zone to trust source obj_remote_net destination obj_local_net action allow
set rulebase security rules Allow-VPN-Outbound from trust to VPN-Zone source obj_local_net destination obj_remote_net action allow

# 提交配置
commit
```
