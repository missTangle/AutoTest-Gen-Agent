import re
import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom


def convert_md_to_opml(md_input, opml_output):
    # 创建 OPML 基础结构
    root = ET.Element("opml", version="2.0")
    head = ET.SubElement(root, "head")
    ET.SubElement(head, "title").text = "Generated Test Cases"
    body = ET.SubElement(root, "body")

    # 初始层级追踪，body 视为第 0 层
    stack = [(0, body)]

    with open(md_input, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('|'): continue  # 跳过空行和表格

            # 匹配标题 (# ## ###)
            match = re.match(r'^(#+)\s+(.*)', line)
            if match:
                level = len(match.group(1))
                text = match.group(2)

                # 调整层级栈
                while stack and stack[-1][0] >= level:
                    stack.pop()

                parent = stack[-1][1]
                new_node = ET.SubElement(parent, "outline", text=text)
                stack.append((level, new_node))

            # 匹配列表项 (- [动作])
            elif line.startswith('-'):
                text = line.lstrip('- ').strip()
                if stack:
                    ET.SubElement(stack[-1][1], "outline", text=text)

    # 导出并美化 XML
    xml_str = ET.tostring(root, encoding='utf-8')
    reparsed = minidom.parseString(xml_str)
    with open(opml_output, "w", encoding='utf-8') as f:
        f.write(reparsed.toprettyxml(indent="  "))


if __name__ == "__main__":
    if len(sys.argv)!=3:
        print("❌ 错误：参数数量不正确！")
        print("用法示例：python3 md_to_opml.py <输入路径> <输出路径>")
        print(f"当前收到的参数列表: {sys.argv}")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    convert_md_to_opml(input_path, output_path)