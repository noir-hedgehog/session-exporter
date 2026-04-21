# SessionManager

OpenClaw 会话管理工具集 — 导出、分析、可视化。

![](https://img.shields.io/badge/license-MIT-blue.svg)
![](https://img.shields.io/badge/python-3.10+-green.svg)

## 功能模块

| 模块 | 说明 |
|------|------|
| [session-exporter](./session_exporter/) | 将 OpenClaw 会话导出为 ChatLab 标准格式，支持跨平台聊天记录聚合分析 |
| [session-viewer](./session_viewer/) | 网页版会话查看器，支持 SQLite 存储、全文搜索、分页浏览 |

## 安装

```bash
git clone git@github.com:noir-hedgehog/SessionManager.git
cd SessionManager
```

各模块独立安装：

```bash
# session-exporter
cd session_exporter && pip install -e .

# session-viewer（依赖 Flask）
cd session_viewer && pip install flask
```

## 快速开始

### session-exporter

导出单个会话为 ChatLab JSON：

```bash
python -m chatlab_exporter \
  --input ~/.openclaw/agents/lingxi/sessions/abc123.jsonl \
  --output export.json
```

批量导出所有会话：

```bash
python -m chatlab_exporter --agent lingxi --output ./exports/
```

### session-viewer

导入会话到 SQLite：

```bash
python -m session_importer --all --db ~/.openclaw/sessions.db
```

启动 Web 查看器：

```bash
cd session_viewer
/usr/bin/python3 -c "from viewer.app import app; app.run(host='0.0.0.0', port=8787)"
```

打开 http://localhost:8787 或通过 Tailscale 访问：http://\<mac-mini-ip\>:8787

## 项目计划

### Phase 1: 基础能力 ✅
- [x] session-exporter CLI（JSONL → ChatLab 格式）
- [x] session-viewer Flask Web UI
- [x] SQLite 持久化存储
- [x] 分页加载
- [x] 全文搜索
- [x] Markdown 导出

### Phase 2: 体验优化 🔄
- [ ] thinking 内容展示（折叠/展开）
- [ ] 多 Agent 筛选增强
- [ ] 会话时间轴视图
- [ ] 响应式布局优化

### Phase 3: 数据能力
- [ ] 增量同步（监听 JSONL 变化）
- [ ] 数据统计 Dashboard（消息量趋势、活跃时段）
- [ ] ChatLab 格式完整导出（保留 thinking）

### Phase 4: 生态集成
- [ ] OpenClaw skill 自动备份
- [ ] Memory 文件导入
- [ ] 飞书消息导入（chatlab-exporter 已有方向）
- [ ] 其他平台消息导入

## 技术架构

```
SessionManager/
├── README.md
├── session_exporter/          # ChatLab 格式导出
│   ├── chatlab_exporter/     # Parser + Formatter
│   ├── pyproject.toml
│   ├── README.md
│   └── README_CN.md
└── session_viewer/            # Web 可视化
    ├── session_importer/     # JSONL → SQLite
    ├── viewer/               # Flask App + Templates
    └── pyproject.toml
```

## 未来方向

- **备份层**：原生 JSONL + SQLite 双轨，保留完整信息
- **分析层**：基于 SQLite FTS5 的语义搜索
- **迁移层**：通用格式导出，支持跨 Agent 平台迁移

## 相关项目

- [ChatLab](https://github.com/hellodigua/ChatLab) — 本地聊天记录分析工具
- [OpenClaw](https://github.com/openclaw/openclaw) — 跨平台 AI 助手框架
