# Skill: OpenClaw-AI-Test-Pilot-Engine (v4.0)

## 1. 核心目标

驱动 Android 自动化闭环，实现从需求审计到资产固化（Hydrate）及智能自愈回放（Replay）的全链路管理。

## 2. 全局环境变量

- **PROJECT_ROOT**: `/project_name/`
- **PYTHON_ENV**: `python`
- **PATHS**:
  - raw_json_path: `{PROJECT_ROOT}/output/TC_[需求名]_[日期]_raw.json`
  - asset_json_path: `{PROJECT_ROOT}/output/TC_[需求名]_[日期]asset.json`
  - opml_output_path: `{PROJECT_ROOT}/output/TC_[需求名]_[日期].opml`
  - md_output_path: `{PROJECT_ROOT}/output/TC_[需求名]_[日期].md`


## 3. 自动化执行流水线 (SOP) —— [指令级执行]

### Step 1: 需求解析与初始化 (Asset Generation)

- 动作：解析 PRD 文本，产出符合 Schema 的初始 JSON（raw.json）。
- 断言策略映射指南：

  | 策略 (Strategy) | 级别 | 判定逻辑 | 场景示例 |
  | :--- | :--- | :--- | :--- |
  | TEXT_EXISTS | L1 | OCR/Dump 校验预期文字。 | 页面跳转、标题预览。 |
  | CHECKED_STATUS | L2 | 识别控件 Checked 属性。 | 开关开启/关闭。 |
  | VISUAL_AGENT | L3 | 多模态语义理解。 | 图标置灰、转场动画。 |

- JSON 产出模版：

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
          "steps": [
            {
              "action": "点击",
              "object": "夜间模式开关",
              "memo": "备注信息",
              "assert_plan": {
                "strategy": "CHECKED_STATUS", 
                "anchor": "夜间模式",
                "expect_val": "true",
                "level": "L2"
              }
            }
          ],
          "expected": ["开关状态显示为'已开启'"]
        }
      ]
    }
  ]
}
```

- **强制后置动作**：JSON 落地后，必须立即执行转换脚本，生成脑图和文档供人工复核。 
  - 同步 OPML：`{PYTHON_ENV} {PROJECT_ROOT}/scripts/json_to_opml.py "{raw_json_path}" "{opml_output_path}"`
  - 同步 MD：`{PYTHON_ENV} {PROJECT_ROOT}/scripts/json_to_markdown.py "{raw_json_path}" "{md_output_path}"`
  
### Step 2: 资产固化指令 (Action: HYDRATE)

- 执行路径：调用 CLI 进行录制并补全元数据。
- 命令：
  `{PYTHON_ENV} {PROJECT_ROOT}/skill/entry_point_android.py --json_case_path "{raw_json_path}" --output_asset_json_path "{asset_json_path}" --task_mode "HYDRATE"`

### Step 3: 智能自愈回放指令 (Action: REPLAY)

- 执行路径：调用 CLI 执行具备自愈能力的回放。
- 命令：
  `{PYTHON_ENV} {PROJECT_ROOT}/skill/entry_point_android.py --json_case_path "{raw_json_path}" --asset_json_path "{asset_json_path}" --task_mode "REPLAY"`

### 4. 执行约束

- 单一事实源：OPML/MD/Asset 必须严格源自生成的 raw_json。
- 解释器隔离：必须强制使用 {PYTHON_ENV}，严禁调用系统 python。
- 环境幂等：每次执行前后，Agent 需确认 App 状态已由 terminate_app 重置。

