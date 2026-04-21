# session-exporter

将 [OpenClaw](https://github.com/openclaw/openclaw) Agent 对话记录导出为 [ChatLab](https://github.com/hellodigua/ChatLab) 标准格式的工具，支持本地 AI 分析。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-green.svg)

## 功能特点

- **解析 OpenClaw JSONL 会话** — 处理嵌套内容块，自动跳过 thinking/tool 块
- **ChatLab 标准输出** — 生成合规 JSON/JSONL，可直接导入 ChatLab
- **批量导出** — 一条命令导出所有历史会话
- **零依赖** — 纯 Python，无外部包要求

## 安装

```bash
git clone git@github.com:noir-hedgehog/session-exporter.git
cd session-exporter
pip install -e .
```

## 快速开始

### 导出单个会话

```bash
python -m chatlab_exporter \
  --input ~/.openclaw/agents/lingxi/sessions/abc123.jsonl \
  --output export.json
```

### 批量导出某个 Agent 的所有会话

```bash
python -m chatlab_exporter \
  --agent lingxi \
  --output ./exports/
```

### 指定会话名称

```bash
python -m chatlab_exporter \
  --input session.jsonl \
  --name "我的对话" \
  --output export.json
```

## 输出格式

导出为 [ChatLab 标准格式](https://chatlab.fun/standard/chatlab-format.html)：

```json
{
  "chatlab": {
    "version": "0.0.1",
    "exportedAt": 1703001600,
    "generator": "chatlab-exporter"
  },
  "meta": {
    "name": "会话名称",
    "platform": "openclaw",
    "type": "private"
  },
  "members": [
    { "platformId": "user", "accountName": "User" },
    { "platformId": "hecate", "accountName": "Hekate" }
  ],
  "messages": [
    {
      "sender": "user",
      "accountName": "User",
      "timestamp": 1703001600,
      "type": 0,
      "content": "你好！"
    }
  ]
}
```

## 消息类型映射

| 内容类型     | ChatLab 类型 |
|-------------|-------------|
| `text`      | 0 (文字)     |
| `image`     | 1 (图片)     |
| `thinking`  | _跳过_       |
| `tool_call` | _跳过_       |
| `tool_result` | _跳过_     |

> **说明：** `thinking`、`tool_call`、`tool_result` 等内部块会被跳过，导出的是干净的对话文本，方便在 ChatLab 中做分析。

## 项目结构

```
session-exporter/
├── chatlab_exporter/
│   ├── __init__.py
│   ├── parser.py       # 解析 OpenClaw JSONL 文件
│   ├── formatter.py     # 转换为 ChatLab 格式
│   └── cli.py          # CLI 入口
├── pyproject.toml
├── README.md
└── test_cli.py
```

## ChatLab 使用流程

1. 导出会话：`python -m chatlab_exporter --agent lingxi --output ./exports/`
2. 打开 ChatLab → 导入 → 选择导出的 `.json` 文件
3. 使用 ChatLab 的 SQL Lab 或 AI Agent 分析对话模式

## 相关项目

- [ChatLab](https://github.com/hellodigua/ChatLab) — 本地 AI 聊天记录分析工具
- [OpenClaw](https://github.com/openclaw/openclaw) — 跨平台 AI 助手框架
