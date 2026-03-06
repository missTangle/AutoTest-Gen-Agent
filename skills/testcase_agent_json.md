# Skill: TestCase-JSON-Engine (v2.0)

## 1. 核心目标
解析 Android PRD，产出 100% 结构化的 JSON 数据，作为导图和文档的“单一事实源”。

## 2. 自动化执行流水线 (SOP) —— [严格执行]
 1. **逻辑审计 (Audit Mode)**：提取 PRD 动作与条件，对齐 Checklist 经验补遗。
 2. **结构化生成 (JSON Generation)**：
    - **禁止**直接输出 Markdown 正文。
    - **强制**输出符合以下 Schema 的 JSON 代码块：
    ```json
    {
      "module": "模块名称",
      "test_suites": [
        {
          "scene": "场景名称",
          "cases": [
            {
              "id": "TC-01",
              "title": "用例标题",
              "preconditions": ["条件1", "条件2"],
              "steps": [{"action": "点击", "object": "对象", "memo": "备注"}],
              "expected": ["预期结果1"]
            }
          ]
        }
      ]
    }
    ```
 3. **文件持久化与转换 (Persistence & Transformation)**：
    - 将 JSON 写入 `output_dir` 下的 `.json` 文件。
    - 立即调用 Python 脚本进行分发：
      - `/Users/susiecheng/Documents/AI_Agent/Skills/venv/bin/python /Users/susiecheng/Documents/AI_Agent/Skills/json_to_opml.py "{json_path}" "{opml_path}"`
      - `/Users/susiecheng/Documents/AI_Agent/Skills/venv/bin/python /Users/susiecheng/Documents/AI_Agent/Skills/json_to_markdown.py "{json_path}" "{md_path}"`

## 3. 命名规则
 - json_path: TC_[需求名]_[日期].json
 - opml_path: 同名 .opml
 - md_path: 同名 .md