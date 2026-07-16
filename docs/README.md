# theNanGuos 文档地图

本目录保存纳入版本控制的正式事实源。根目录 [`README.md`](../README.md) 负责启动入口；本文件负责告诉维护者和 Coding Agent 应从哪里读取或修改某类事实。

## 按目标阅读

| 目标 | 首选文档 | 继续阅读 |
|---|---|---|
| 理解产品定位、范围和用户流程 | [PRD](product/PRD.md) | [功能规格](product/SPEC.md) |
| 判断某个功能应如何表现 | [功能规格](product/SPEC.md) | [API 合同](architecture/API_SPEC.md) |
| 调整页面、交互或视觉 | [Web UI 设计](product/WEB_UI_DESIGN.md) | [信息架构](architecture/INFORMATION_ARCHITECTURE.md) |
| 理解系统组件和技术取舍 | [系统架构](architecture/ARCHITECTURE.md) | [Agent 系统](architecture/AGENT_SYSTEM.md) |
| 修改 Agent、Tool、推理或记忆 | [Agent 系统](architecture/AGENT_SYSTEM.md) | [数据模型](architecture/DATA_MODEL.md) |
| 修改字段、枚举或持久化格式 | [数据模型](architecture/DATA_MODEL.md) | [API 合同](architecture/API_SPEC.md) |
| 修改 HTTP、DeepSeek 或 Suno 协议 | [API 合同](architecture/API_SPEC.md) | [功能规格](product/SPEC.md) |
| 查看实施顺序 | [实施计划](planning/PLAN.md) | [Work Units](planning/work-units/) |
| 查看当前完成度和验证证据 | [开发状态](planning/STATUS.md) | 不从 PLAN 推断进度 |

## 权威归属

| 信息 | 唯一详细来源 |
|---|---|
| 产品目标、范围、核心对象含义、业务规则 | `product/PRD.md` |
| 用户可观察功能、状态、异常和验收场景 | `product/SPEC.md` |
| 页面结构、组件、交互和视觉基线 | `product/WEB_UI_DESIGN.md` |
| 系统边界、组件、部署和技术选型 | `architecture/ARCHITECTURE.md` |
| 信息域、拥有者、生命周期和跨域流动 | `architecture/INFORMATION_ARCHITECTURE.md` |
| Agent、Tool、LangGraph、推理、偏好和知识机制 | `architecture/AGENT_SYSTEM.md` |
| 对象字段、枚举、约束、JSON 和文件映射 | `architecture/DATA_MODEL.md` |
| FastAPI、DeepSeek、Suno 请求与响应合同 | `architecture/API_SPEC.md` |
| 建设顺序、依赖、Milestone 和 WU 索引 | `planning/PLAN.md` |
| 当前状态、阻塞、下一步和新鲜验证证据 | `planning/STATUS.md` |

同一事实只在权威文档中完整定义。其他文档使用摘要和相对链接，不复制完整字段表、JSON 或状态表。

## 稳定标识

- 功能：`FR-<AREA>-<NNN>`，例如 `FR-GEN-001`。
- 数据模型：`DM-<ObjectName>`，例如 `DM-SongSpec`。
- API：`API-<AREA>-<NNN>`，例如 `API-GEN-001`。
- Work Unit：`WU-<AREA>-<NNN>`，例如 `WU-KNOW-002`。
- Phase：`P1`–`P9`；Milestone：`M1`–`M5`。

稳定标识不随章节重排改变。

## 变更同步矩阵

| 变更 | 必须检查 |
|---|---|
| 新增用户能力 | PRD、SPEC、PLAN/WU、STATUS；涉及 UI 时检查 Web UI 设计 |
| 修改状态或错误行为 | SPEC、API_SPEC、DATA_MODEL、相关测试 |
| 修改 Agent 或知识策略 | AGENT_SYSTEM、DATA_MODEL、SPEC 安全边界 |
| 修改 Schema 或文件格式 | DATA_MODEL、API_SPEC、迁移/兼容性说明 |
| 修改 API | API_SPEC、SPEC、前后端契约测试 |
| 修改系统组件或依赖 | ARCHITECTURE、相关专题和 PLAN/WU |
| 完成或阻塞任务 | 只更新 STATUS；不在 PLAN 或 WU 写完成勾选 |

## 维护规则

1. `STATUS.md` 是唯一进度看板。
2. WU 定义任务合同，不保存状态值或完成勾选。
3. Mermaid 图后必须有关系表或步骤说明。
4. “当前已实现”必须能追溯到代码或测试；真实供应商未联调不能写成已完成。
5. 正式文档不得包含密钥、Authorization、隐藏推理或完整供应商原始响应。
