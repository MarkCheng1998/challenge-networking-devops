# Challenge Networking - DevOps

> Mercado Libre - 候选人实验室 - 网络技术自动化挑战

本项目实现 Cisco 交换机 VLAN 配置自动化（通过 Web 前端），并规划 Fortigate 与 Palo Alto 之间 IPSec VPN 的自动化配置方案。

---

## 项目结构

```
challenge-networking-devops/
├── README.md                         # 项目说明文档
├── requirements.txt                  # Python 依赖
├── .gitignore
├── app.py                            # Flask Web 应用主入口
├── templates/
│   └── index.html                    # VLAN 配置前端界面
├── static/
│   ├── style.css                     # 前端样式
│   └── script.js                     # 前端交互逻辑
├── backend/
│   ├── __init__.py
│   └── switch_config.py              # Cisco 交换机自动化后端（VLAN/主机名/保存/备份/验证）
├── backups/                          # 配置备份文件目录
├── docs/
│   └── vpn_ipsec_plan.md             # Part 2: IPSec VPN 自动化规划文档
└── scripts/
    ├── fortigate_vpn_config.py       # Fortigate VPN 配置脚本（REST API）
    ├── paloalto_vpn_config.py        # Palo Alto VPN 配置脚本（XML API）
    └── test_connectivity.py          # IPSec 隧道连通性测试脚本
```

---

## 第一部分：Cisco 交换机 VLAN 配置自动化

### 功能概述

| 功能 | 描述 |
|------|------|
| VLAN 配置 | 通过 Web 界面输入 VLAN ID 和名称，自动在 Cisco 交换机上创建 VLAN |
| 主机名修改 | 通过 Web 界面设置交换机主机名（默认: SWITCH_AUTOMATIZADO） |
| 配置保存 | 自动执行 `write memory` 将配置保存到 NVRAM |
| 配置备份 | 自动备份当前配置到本地文件（文件名含主机名和时间戳） |
| 配置验证 | 配置完成后自动验证 VLAN 和主机名是否与期望一致，偏差时显示告警 |
| 模拟模式 | 无需真实交换机即可演示完整流程（用于测试和展示） |

### 预配置 VLAN

| VLAN ID | 名称 | 用途 |
|---------|------|------|
| 10 | VLAN_DATOS | 数据网络 |
| 20 | VLAN_VOZ | 语音网络 |
| 50 | VLAN_SEGURIDAD | 安全网络 |

### 安装和运行

#### 1. 安装依赖

```bash
# 克隆仓库
git clone https://github.com/<your-username>/challenge-networking-devops.git
cd challenge-networking-devops

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# 安装依赖
pip install -r requirements.txt
```

#### 2. 运行 Web 应用

```bash
python app.py
```

应用启动后，在浏览器中访问: **http://localhost:5000**

#### 3. 使用前端界面

1. **交换机连接信息**: 输入交换机 IP、用户名、密码和 SSH 端口
   - 如无真实设备，勾选「模拟模式」即可演示完整流程
2. **主机名**: 输入目标主机名（默认: SWITCH_AUTOMATIZADO）
3. **VLAN 配置**: 界面预填了 VLAN 10/20/50，可添加/删除/修改 VLAN
4. **执行配置**: 点击「执行自动化配置」按钮
   - 脚本将依次执行: 连接交换机 → 配置VLAN → 修改主机名 → 保存到NVRAM → 备份配置 → 验证配置
5. **查看结果**: 右侧面板显示每一步的执行状态和验证告警
6. **仅验证**: 如需单独验证当前配置，点击「仅验证配置」按钮

### 后端技术栈

- **Flask**: Web 框架，提供 REST API 和页面渲染
- **Netmiko**: 网络自动化库，通过 SSH 连接 Cisco 交换机
- **正则表达式**: 解析 `show vlan brief` 和 `show running-config` 输出进行验证

### 验证逻辑说明

配置验证会检查以下内容：
1. **主机名匹配**: 当前主机名是否与期望值一致
2. **VLAN 存在性**: 每个期望 VLAN 是否存在
3. **VLAN 名称匹配**: VLAN 名称是否与期望值一致
4. **非标准配置检测**: 是否存在不在期望列表中的额外 VLAN

告警级别：
- ⚠ **严重告警**: VLAN 缺失、名称不匹配、主机名不匹配
- ℹ **信息通知**: 发现非标准 VLAN（不影响期望配置）

---

## 第二部分：IPSec VPN 自动化规划

### 文档位置

详细规划文档: [`docs/vpn_ipsec_plan.md`](docs/vpn_ipsec_plan.md)

### 文档内容

- **参数定义**: WAN IP、本地网络、隧道网络 (169.255.1.0/30)、Phase 1/2 参数
- **工具/API 识别**: FortiOS REST API、Palo Alto XML API、SSH+CLI、Ansible、Terraform
- **自动化步骤**: 两端设备的完整配置流程（地址对象→IKE→IPSec→隧道→策略→路由）
- **跨厂商注意事项**: 术语映射、配置提交机制、API 格式、接口编号等差异
- **验证和告警策略**: CLI/API 验证方法、检查清单、告警分级、回退策略

### 示例脚本（可选交付物）

| 脚本 | 说明 |
|------|------|
| `scripts/fortigate_vpn_config.py` | 通过 FortiOS REST API 配置 IPSec VPN |
| `scripts/paloalto_vpn_config.py` | 通过 XML API 配置 Palo Alto IPSec VPN |
| `scripts/test_connectivity.py` | 测试 IPSec 隧道连通性（Ping + 状态验证） |

---

## 测试环境说明

- **第一部分**: 可使用 Cisco Packet Tracer 或 GNS3 搭建 Cisco 交换机模拟环境
  - 也可以直接使用「模拟模式」进行演示，无需任何网络设备
- **第二部分**: VPN 配置为规划文档，无需实际环境。示例脚本可在真实设备上运行

---

## Git 提交历史

本项目使用 Git 进行版本控制，提交历史如下：

| 提交 | 说明 |
|------|------|
| 1 | 初始化项目结构和基础文件 (.gitignore, requirements.txt) |
| 2 | 实现后端 Cisco 交换机配置模块 (switch_config.py) |
| 3 | 开发 Flask Web 前端和 API (app.py, templates, static) |
| 4 | 实现配置验证和告警机制 |
| 5 | 编写 IPSec VPN 自动化规划文档 (vpn_ipsec_plan.md) |
| 6 | 添加 Fortigate/Palo Alto VPN 示例脚本和连通性测试 |
| 7 | 完善 README 文档 |

---

## 技术要点

1. **分层架构**: 前端（Flask/HTML/CSS/JS）→ API 层 → 后端自动化层（Netmiko）
2. **模拟模式**: 内置模拟器，无设备时可完整演示流程
3. **验证驱动**: 配置后自动验证，确保配置正确性
4. **安全备份**: 每次配置变更自动备份，文件名含主机名和时间戳
5. **跨厂商兼容**: VPN 规划覆盖 Fortigate 和 Palo Alto 的差异处理
