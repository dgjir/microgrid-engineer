# 微电网工程师 (Microgrid Engineer)

微电网系统设计、仿真与优化专家插件。覆盖交流/直流/混合微电网架构设计、分布式能源集成、电力电子变流器建模、保护方案设计、能量管理系统（EMS）策略、稳态/暂态/短路分析、多时间尺度仿真等专业领域。

## 安装

`ash
codex plugin install --from https://github.com/<your-username>/microgrid-engineer
`

安装后在 Codex 中即可使用插件中的 Skill 和 MCP 工具。

## 包含内容

### Skills（AI Agent 角色）

| Skill | 用途 |
|-------|------|
| microgrid-system-engineer | 微电网系统工程师 — 架构设计、DER 集成、控制策略、EMS、经济分析 |
| microgrid-simulation-expert | 微电网仿真专家 — 建模工具选择、仿真建模、联合仿真、HIL 测试、模型验证 |

### MCP 工具（工程计算）

| 工具名 | 功能 |
|--------|------|
| microgrid-cable-sizing | 电缆选型计算（基于载流量和压降） |
| microgrid-battery-sizing | 电池储能容量配置（LFP 电芯串并联计算） |
| microgrid-pv-yield | 光伏年发电量估算 |
| microgrid-transformer-sizing | 变压器容量选型（含温升/海拔修正） |
| microgrid-planning-study | 微电网规划研究（容量配置 + 能量平衡 + 经济性） |

### 脚本工具

| 脚本 | 功能 |
|------|------|
| scripts/load_profile_generator.py | 生成合成负载曲线（含居民/商业/工业混合 + 季节性修正） |

## AI Agent 使用说明

### 触发条件

当用户提出以下类型的问题时，AI Agent 应自动使用本插件的 Skill：

- **系统设计类**：\"设计一个微电网\"、\"光伏+储能怎么配\"、\"选什么拓扑结构\"
- **仿真建模类**：\"帮我搭建仿真模型\"、\"用什么工具做暂态分析\"、\"HIL 测试怎么做\"
- **工程计算类**：\"电缆选多大\"、\"电池配多少度\"、\"变压器选多大\"

### Skill 调用指南

#### microgrid-system-engineer — 系统设计流程

AI Agent 应按以下步骤逐步推进：

1. **需求澄清** — 确认场景类型、电压等级、并网/孤岛模式、负载特性
2. **拓扑对比** — 提供 ≥2 种方案对比（AC/DC/混合），用表格呈现优劣
3. **详细设计** — 单线图、设备容量估算、控制策略框图
4. **仿真验证计划** — 指定仿真工具、设计关键场景、提供核心参数
5. **风险分析** — 识别薄弱点（谐振风险、保护选择性不足等），提出缓解措施

#### microgrid-simulation-expert — 仿真工具选择

根据研究类型选择工具：

| 研究类型 | 推荐工具 |
|----------|---------|
| 稳态潮流/短路 | OpenDSS / Pandapower / PowerFactory |
| 电磁暂态 (EMT) | PSCAD / Simulink / PLECS |
| RMS 动态稳定 | PowerFactory / PSS®E |
| 准静态时序 (QSTS) | OpenDSS + Python |
| 实时 HIL | RTDS / OPAL-RT / Typhoon HIL |
| 经济调度 | PyPSA / PowerSimulations.jl |

### MCP 工具调用示例

AI Agent 可通过 MCP 协议直接调用计算工具，工具名前缀为 mcp__microgrid-calc__：

**电缆选型：**
\\\json
{
  "name": "microgrid-cable-sizing",
  "arguments": {
    "current_a": 150,
    "length_m": 80,
    "voltage_v": 400,
    "max_drop_percent": 3,
    "cable_type": "cu",
    "ac": true,
    "power_factor": 0.95
  }
}
\\\

**电池配置：**
\\\json
{
  "name": "microgrid-battery-sizing",
  "arguments": {
    "load_kwh_per_day": 500,
    "backup_hours": 4,
    "depth_of_discharge": 0.8,
    "round_trip_efficiency": 0.92,
    "dc_voltage_v": 800,
    "autonomy_days": 1,
    "cell_voltage_v": 3.2,
    "cell_capacity_ah": 280
  }
}
\\\

**光伏发电量估算：**
\\\json
{
  "name": "microgrid-pv-yield",
  "arguments": {
    "peak_kw": 500,
    "annual_ghi_kwh_m2": 1400,
    "tilt_deg": 30,
    "azimuth_deg": 180,
    "derating_factor": 0.77,
    "latitude_deg": 31
  }
}
\\\

**变压器选型：**
\\\json
{
  "name": "microgrid-transformer-sizing",
  "arguments": {
    "total_apparent_power_kva": 800,
    "future_margin_percent": 20,
    "ambient_temp_c": 35,
    "altitude_m": 500,
    "oil_type": "mineral",
    "cooling_type": "ONAN"
  }
}
\\\

**微电网规划研究：**
\\\json
{
  "name": "microgrid-planning-study",
  "arguments": {
    "pv_kw": 300,
    "wind_kw": 0,
    "bess_kwh": 500,
    "bess_kw": 250,
    "diesel_kw": 200,
    "peak_load_kw": 180,
    "avg_load_kw": 100,
    "pv_capacity_factor": 0.18,
    "wind_capacity_factor": 0,
    "diesel_fuel_cost_per_liter": 7.5,
    "grid_connected": false
  }
}
\\\

### 回答格式要求

AI Agent 回答微电网问题时，应遵循结构化格式：

1. **系统上下文** — 拓扑、规模、电压等级、运行模式
2. **工程分析** — 计算过程、方案对比、设备选型依据
3. **仿真计划** — 用什么工具建模、关键参数
4. **实施指导** — 保护整定、EMS 逻辑、通信方案

引用标准时需注明编号（如 IEEE 1547-2018、IEC 61850-7-420、GB/T 33589）。

## MCP 服务依赖

MCP 工具需要 Python 3 环境及以下依赖：

\\\ash
pip install numpy
\\\

Codex 在安装插件后会自动启动 .mcp.json 中配置的 MCP 服务。

## 项目结构

\\\
microgrid-engineer/
├── .codex-plugin/
│   └── plugin.json          # 插件清单
├── .mcp.json                # MCP 服务配置
├── skills/
│   ├── microgrid-system-engineer/
│   │   └── SKILL.md         # 系统工程师 Skill
│   └── microgrid-simulation-expert/
│       └── SKILL.md         # 仿真专家 Skill
├── scripts/
│   ├── mcp_server.py        # MCP 计算服务
│   └── load_profile_generator.py  # 负载曲线生成
├── assets/                  # 资源文件
└── hooks/                   # 钩子脚本
\\\

## 适用标准

- IEEE 1547-2018 — DER 并网互联要求
- IEEE 2030.7/2030.8 — 微电网控制器规范与测试
- IEC 61850-7-420 — DER 通信逻辑节点
- IEC 62898 — 微电网规划与设计指南
- GB/T 33589/33593 — 中国分布式能源并网标准
- GB/T 36274 — 微电网 EMS 技术规范

## License

MIT
