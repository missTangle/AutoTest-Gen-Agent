# AutoTest-Gen-Agent 🚀

> **从“需求语义”到“视觉证据”的端到端 AI 测试代理**
> 本项目不仅实现了测试用例的自动化生成，更通过视觉感知能力，打造了具备 **自动化固化 (Hydration)**、**智能回放 (Replay)** 与 **异常自愈 (Self-Healing)** 能力的测试闭环。

---

## 🌟 核心进化 (Advanced Features)

- **Requirement-to-Action (语义转换器)**
基于自定义 Agent Skill，将模糊的 PRD 动词转化为具备业务逻辑的操作流，并集成 RAG 经验库自动补遗 Checklist 场景。
- **Semantic-First Locating (意图优先定位)**
针对 Android 系统应用 ID 高频重复的痛点，引入 **“语义指纹打分模型”**。优先利用文字锚点，辅以空间位置权重，实现复杂长列表下的精准定位。
- **Hydration & Self-Healing (固化与自愈)**
  - **固化**：首次运行通过 AI 实时解析 UI，将坐标与 ID 自动 **Back-fill** 至测试资产。
  - **自愈**：UI 改版后，触发视觉重定向静默修复元数据，实现自动化脚本的“零维护”。
- **Full-Space Discovery (全空间搜索)**
内置 **Scroll-to-Find 机制**，支持动态滑动搜索。配合屏幕指纹校验（MD5 对比），有效防止无限加载页面下的滑动死循环。
- **Multi-Level Visual Assertion (多级视觉断言)**
支持 L1 (Text) 到 L3 (Visual Agent) 的深度判定，可识别“图标置灰”、“网络禁用”等复杂视觉状态。

---

## 📦 全生命周期交付物 (Full-Lifecycle Deliverables)

本项目打通了测试工程的完整链路，输出不仅仅是脚本，更是标准化的质量资产：

### 1. 逻辑评审层 (Phase 1: Logic Modeling)

自动产出 **XMind/OPML 脑图**，用于业务评审，确保 100% 需求覆盖。

Agent 执行汇报 (Execution Logs)
、、、markdown
当执行指令 `分析 [需求], 出导图` 后，Agent 会产出如下标准汇报：

> ### 🤖 执行汇报 (TestCase-JSON-Engine v2.0)

> **✅ 全流程完成！**
>
>
> | 产物类型       | 文件路径                                | 用途       |
> | ---------- | ----------------------------------- | -------- |
> | 📄 JSON 数据 | `output/TC_NightMode_20260105.json` | 单一事实源    |
> | 🧠 OPML 导图 | `output/TC_NightMode_20260105.opml` | XMind 导入 |
> | 📝 MD 文档   | `output/TC_NightMode_20260105.md`   | 标准测试用例   |
>
>
> **SOP 状态：** 逻辑审计 ✅ | 结构化生成 ✅ | 转换渲染 ✅
>
> **用例树预览：**
>
> ```text
> └── 系统设置 - 夜间模式
>     ├── 夜间模式基础功能 (2 用例)
>     ├── 夜间模式与自动亮度交互 (3 用例)
>     └── ... (更多详见导图)
> ```

多维度产物交付 (Multi-format Outputs)


### 🛡️ 质量保障：Audit Mode 产出示例

当 PRD 逻辑复杂时，工具会自动生成审计报告：

> **[逻辑补遗]**

> - 检测到 PRD 提及 "电量低于 20%" 逻辑，已自动补充 "低电量弹窗拦截" 测试用例。

> - 检测到 "忘记网络" 操作，已自动补充 "当前连接态" 与 "非连接态" 的分支覆盖。

### 2. 执行验收层 (Phase 2: Visual Evidence)

自动捕获执行现场，生成带 **AI 判定理由** 与 **失败截图链接** 的 Markdown 报告：


| 序号  | 动作  | 目标对象          | 状态       | 视觉断言判定依据         | 现场证据                                      |
| --- | --- | ------------- | -------- | ---------------- | ----------------------------------------- |
| 1   | 点击  | Network       | **PASS** | 找到文字锚点，页面跳转成功    | `[295, 365]`                              |
| 2   | 点击  | Airplane mode | ~~FAIL~~ | 开关处于关闭状态，不符合预期开启 | [🖼️查看截图](reports/evidence/fail_TC02.png) |
| 3   | 观察  | Internet      | **PASS** | 图标呈置灰状态，符合禁用预期   | [🖼️查看截图](reports/evidence/pass_TC03.png) |


---

## 🏗 架构方案 (Architecture)

1. **Input**: Android PRD (Text/Markdown)
2. **Analysis**: LLM Agent (Audit Mode) -> 产出 XMind 评审脑图
3. **Hydration**: 首次运行，通过视觉感知完成 **元数据固化 (Back-fill)**
4. **Replay**: 执行“语义对齐 -> 滑动搜索 -> 视觉断言”的闭环回放
5. **Output**: 结构化资产 (JSON) & 视觉回放报告 (MD)

---

## 📅 项目路线图 (Roadmap)

- **Phase 1: 逻辑建模阶段** (Completed)
  - RAG 经验对齐与 XMind 自动化导出工具链
- **Phase 2: 执行进化阶段** (Current)
  - 基于视觉语义的 **Hydrate/Replay** 闭环
  - 智能滑动搜索与“语义指纹”打分引擎
  - L1-L3 多级视觉断言与自动取证
- **Phase 3: 视觉融合阶段** (Next)
  - 集成 Figma 视觉稿 AI 对比校验
  - 自动化生成跨端（iOS/Android）执行脚本

---

## 🛠 快速开始 (Quick Start)

```bash
# 1. 启动逻辑审计与用例生成
python scripts/json_to_opml.py --prd prd_file.md

# 2. 执行自动化回放并生成视觉报告
python entry_point_android.py --case output/TC_Network_2026.json --mode REPLAY

```

---

## 📂 目录结构

```text
.
├── output
│   ├── TC_NightMode_20260305.json
│   ├── TC_NightMode_20260305.md
│   └── TC_NightMode_20260305.opml
├── PRD
├── project_structure.txt
├── README.md
├── requirements.txt
├── resource
│   ├── RequirementDocument_NetworkSettings.txt
│   └── universal_checklist.txt
├── scripts
│   ├── json_to_markdown.py
│   ├── json_to_opml.py
│   ├── md_to_opml.py
│   └── md_to_xmind.py
└── skills
    ├── entry_point_android.py
    ├── main_replay.py
    ├── testcase_agent_new.md
    ├── testcase_agent_v1.5.md
    └── utils
        └── report_generator.py
```

