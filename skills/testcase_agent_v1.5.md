# Skill: Requirement-to-TestCase-Agent (v1.5)
## 1. 目标与能力 (Core)
    - 目标: 解析 Android PRD，产出用于 SmartDriver 的 .md 和用于 XMind 的 .opml。
    - 能力: 语义解析、视觉操作拆解、文件自动化落盘、脚本联动转换。

## 2. 操作规范 (Protocols)
 1. 视觉原子化: 步骤限定使用 [点击]、[输入]、[滑动]、[断言]。基于屏幕可见文本/图标描述，禁止后端术语。
 2. MD 层级: # 模块 -> ## 场景 -> ### 用例标题。
 3. 自检机制: 多个 PRD 时需用户确认；路径不明需标注 [路径待确认]。

## 3. 自动化执行流水线 (SOP) —— [严格执行]
 1. **知识对齐与增强 (Pre-processing)**：
    - **读取资源**：解析 PRD 的同时，必须读取 `/resource/universal_checklist.txt`。
    - **提取范畴**：自主判断 Checklist 中相关的测试范畴（如：状态切换、异常边界等）。
    - **指令对齐**：将 Checklist 中的通用经验转化为适用于当前 PRD 的原子化操作建议。
 2. **核心用例生成 (Core Generation)**：
    - **全场景覆盖**：基于 PRD 逻辑 + Checklist 增强建议，统一产出 MD 内容。
    - **逻辑审计 (Audit Mode)**：
      - 提取 PRD 中所有动作（动词）和条件（if/else）。
      - 确保用例 100% 覆盖上述逻辑。若不满足，自动在末尾追加 `[逻辑补遗]` 章节。
    - **整合补遗**：将来自 Checklist 的补遗标记为 `[经验补遗]`，来自审计的标记为 `[逻辑补遗]`。
 3. **文件持久化 (File Persistence)**：
    - **落盘写入**：强制 UTF-8 编码将上述完整内容写入 `output_dir` 下的 .md 文件。
    - **汇总表生成**：在文件末尾自动附加“自动化参数汇总表”。
 4  **格式转换与转换 (Transformation)**：
    - **脚本执行**：文件落盘后，立即执行以下绝对路径命令（严禁在对话框展示大段代码）：
 5. **反馈**: 仅报告 .md 和 .opml 的最终存储路径。

python3 /skills/md_to_opml.py "{md_path}" "{opml_path}"
    - 变量说明：其中 {md_path} 为刚生成的 Markdown 文件路径，{opml_path} 为目标 OPML 文件路径。

    - **静默原则**：仅反馈最终存储的 .md 和 .opml 路径，无需展示审计过程和代码。


## 4. 默认命名与路径规则 (Naming & Paths)
若用户未指定参数，强制执行以下默认逻辑：
 - output_dir: 默认使用当前 Skill 目录：/skills/output/。
 - file_name: 默认规则为 TC_[需求文件名简写]_[当前日期].md（例如：TC_Network_20260303.md）。
 - opml_path: 必须与 .md 同名同路径，仅后缀改为 .opml。


## 5. 示例输出参考 (Standard Template)
输入需求： “用户在搜索框输入 Battery 后，能进入电池设置页。”

输出 MD 内容样例：
```markdown
# 模块：系统搜索与导航
## 场景：通过搜索进入电池设置
### TC-01：正常搜索并跳转
- **前置条件**: 手机处于主屏幕
- **操作步骤**:
    1. - [点击] 文本 "Search" 或 搜索框图标
    2. - [输入] "Battery" 在 搜索区域
    3. - [点击] 搜索结果中的文本 "Battery"
- **预期结果**:
    - [断言] 屏幕标题显示包含 "Battery" 关键字

### 汇总表（自动化专用）
| 用例ID | 步骤流 | 预期关键字 |
| :--- | :--- | :--- |
| TC-01 | click("Search") -> type("Battery") -> click("Battery") | "Battery" |
```

## 6. 参数与路径 (Parameters)
 - output_dir: 指定存放目录（不存在则自动创建）。
 - file_name: 默认 TC_[需求名]_[日期].md。
 - 环境依赖: 本地 /skills/md_to_opml.py。


## 7. 快捷指令 (Shortcuts)
 - 导图流: "分析 [文件]，出导图" -> (执行全流水线)
 - 文档流: "生成用例 MD，不要导图" -> (仅执行至写入 MD)
