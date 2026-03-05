# AutoTest-Gen-Agent 🚀

> **基于 LLM Agent 的端到端测试工程自动化方案** > 打通从非结构化 PRD 到结构化测试用例（XMind/OPML）及自动化脚本的完整链路。

---

## 🌟 核心亮点 (Core Features)

- **Requirement-to-Action 协议化**：通过自定义 Agent Skill，将模糊的需求描述转化为具备 [点击]、[输入]、[断言] 语义的原子化操作流。
- **RAG 经验库增强 (Knowledge Alignment)**：集成通用测试 Checklist 资源库。
  - *实例*：当 PRD 仅描述“开启 Wi-Fi”时，Agent 自动根据 `resource/universal_checklist.txt` 补遗“飞行模式互斥”与“弱网连接超时”用例。
- **逻辑覆盖审计 (Audit Mode)**：内置自检逻辑，自动回溯 PRD 动词与条件（if/else），确保用例覆盖率达 100%。
- **工程化流水线 (Pipeline)**：全自动化工具链，一键产出符合工业评审标准的 XMind/OPML 导图，支持快速落盘与环境隔离。

---

### 🛡️ 质量保障：Audit Mode 产出示例
当 PRD 逻辑复杂时，工具会自动生成审计报告：
> **[逻辑补遗]**
> - 检测到 PRD 提及 "电量低于 20%" 逻辑，已自动补充 "低电量弹窗拦截" 测试用例。
> - 检测到 "忘记网络" 操作，已自动补充 "当前连接态" 与 "非连接态" 的分支覆盖。

---

## 🏗 架构方案 (Architecture)



1. **Input**: Android PRD (Text/Markdown)
2. **Brain**: LLM Agent (v1.5 Skill w/ Audit Mode)
3. **Knowledge**: Local RAG (Universal Checklist)
4. **Adapter**: Python Transformer (MD to OPML)
5. **Output**: XMind Mindmap & Structured TestCase


---

## 📅 项目路线图 (Roadmap)

- [x] **Phase 1: 逻辑建模阶段** (Current)
    - [x] 核心 Skill 逻辑设计 (v1.5)
    - [x] RAG 经验对齐机制
    - [x] XMind 自动化导出工具链
- [ ] **Phase 2: 执行进化阶段** (Next)
    - [ ] 基于 UI_TARS 的视觉定位映射
    - [ ] 自动化生成 Appium 执行脚本
- [ ] **Phase 3: 视觉融合阶段**
    - [ ] 集成视觉稿 (Figma/Screenshot) 识别
    - [ ] 自动校验 UI 布局与视觉断言

---

## 🛠 快速开始 (Quick Start)

### 环境依赖
- Python 3.8+
- OpenClaw (或兼容的 Agent 框架)
- 依赖库: `pip install -r requirements.txt`

### 运行方式
1. 将 `skills/testcase_agent_v1.5.md` 导入你的 Agent 系统。
2. 确保 `resource/universal_checklist.txt` 路径正确。
3. 输入指令：`分析 [需求文件], 出导图`。

---

## 📂 目录结构
```text
.
├── skills/
│   └── testcase_agent_v1.5.md      # 核心 Agent Skill 定义文件
├── scripts/
│   └── md_to_opml.py               # Markdown 转 OPML 核心转换脚本
├── resource/
│   └── universal_checklist.txt     # 通用测试经验库 (RAG 数据源)
├── output/                         # 默认生成产物存放目录
└── README.md
