# utils/report_generator.py
import os
from datetime import datetime


class ReportGenerator:
    def __init__(self, case_data, output_dir="reports"):
        self.case_data = case_data
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def generate_markdown(self):
        # 如果 self.case_data 是 None，或者不是字典，直接退散
        if not isinstance(self.case_data, dict):
            print("❌ 严重错误：ReportGenerator 接收到的数据不是有效的字典对象！")
            return

        # 获取 test_suites 列表，如果拿不到就给空列表
        suites = self.case_data.get('test_suites', [])
        if not suites:
            print("⚠️ 警告：没有找到任何测试场景数据。")
            return

        # 现在的写法：安全计算总数
        total_cases = sum(len(s.get('cases', [])) for s in suites)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(self.output_dir, f"TestReport_{timestamp}.md")

        lines = [
            f"# 🚀 OpenClaw AI 测试回放报告",
            f"- **执行时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **测试设备**: Android Emulator (5554)",
            f"- **总用例数**: {total_cases}",
            "\n---",
            "## 📋 详细执行日志"
        ]

        for suite in self.case_data.get('test_suites', []):
            scene_name = suite.get('scene', '未命名场景')
            lines.append(f"### 📂 场景: {scene_name}")

            for case in suite.get('cases', []):
                steps = case.get('steps', [])
                # 计算用例状态：如果所有步骤 automation_meta.status 都是 PASS 则 OK
                all_pass = all(s.get('automation_meta', {}).get('status') == "PASS" for s in steps)
                status_icon = "✅" if all_pass else "❌"

                lines.append(f"#### {status_icon} 用例: {case.get('title', '无标题')}")
                lines.append(f"- **ID**: `{case.get('id', 'N/A')}`")

                # 生成步骤详情表
                lines.append("| 序号 | 动作 | 目标对象 | 状态 | 视觉断言判定依据 | 最后坐标 |")
                lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")

                for idx, step in enumerate(steps):
                    meta = step.get('automation_meta', {})
                    status = meta.get('status', 'PENDING')
                    reason = meta.get('ai_verified_reason', '未填写原因')
                    coord = meta.get('last_known_coord', 'N/A')

                    # 给状态上色
                    status_text = f"**{status}**" if status == "PASS" else f"~~{status}~~"
                    screenshot_path = meta.get("screenshot_path")
                    screenshot_link = f" [🖼️查看截图]({screenshot_path})" if screenshot_path else ""

                    row = f"| {idx + 1} | {step['action']} | {step['object']} | {status_text} | {reason}{screenshot_link} | `{coord}` |"


                    lines.append(row)
                lines.append("\n")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"✨ 报告已生成: {file_path}")
        return file_path