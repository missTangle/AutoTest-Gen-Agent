import json
import sys

def convert_json_to_md(json_input, md_output):
    with open(json_input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    lines = [f"# 模块：{data['module']}\n"]

    for suite in data['test_suites']:
        lines.append(f"## 场景：{suite['scene']}\n")
        for case in suite['cases']:
            lines.append(f"### {case['id']}：{case['title']}")
            
            lines.append("- **前置条件**:")
            for p in case['preconditions']:
                lines.append(f"    - {p}") # 这里强制 4 个空格
                
            lines.append("- **操作步骤**:")
            for i, s in enumerate(case['steps'], 1):
                step_str = f"[{s['action']}] {s['object']}"
                if s.get('memo'): step_str += f" ({s['memo']})"
                lines.append(f"    {i}. {step_str}") # 这里强制 4 个空格 + 序号
                
            lines.append("- **预期结果**:")
            for e in case['expected']:
                lines.append(f"    - {e}")
            lines.append("\n---\n")

    with open(md_output, "w", encoding='utf-8') as f:
        f.write("\n".join(lines))

if __name__ == "__main__":
    convert_json_to_md(sys.argv[1], sys.argv[2])