import json
import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom

def convert_json_to_opml(json_input, opml_output):
    try:
        with open(json_input, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 1. 创建根节点并设置命名空间（虽然 OPML 2.0 没强制，但 Xmind 喜欢规整的）
        root = ET.Element("opml", version="2.0")
        head = ET.SubElement(root, "head")
        ET.SubElement(head, "title").text = data.get('module', 'Test Case Mindmap')

        body = ET.SubElement(root, "body")

        # 核心逻辑：模块 -> 场景 -> 用例 -> 分类 -> 动作
        module_node = ET.SubElement(body, "outline", text=data.get('module', 'Module'))

        for suite in data.get('test_suites', []):
            scene_node = ET.SubElement(module_node, "outline", text=suite.get('scene', 'Scene'))
            
            for case in suite.get('cases', []):
                case_title = f"{case.get('id', 'TC')}: {case.get('title', 'Untitled')}"
                case_node = ET.SubElement(scene_node, "outline", text=case_title)
                
                # 前置条件
                if case.get('preconditions'):
                    pre_node = ET.SubElement(case_node, "outline", text="前置条件")
                    for p in case['preconditions']:
                        ET.SubElement(pre_node, "outline", text=str(p))
                
                # 操作步骤
                steps_node = ET.SubElement(case_node, "outline", text="操作步骤")
                for s in case.get('steps', []):
                    step_text = f"[{s.get('action', '')}] {s.get('object', '')}"
                    if s.get('memo'): step_text += f" ({s['memo']})"
                    ET.SubElement(steps_node, "outline", text=step_text)
                
                # 预期结果
                exp_node = ET.SubElement(case_node, "outline", text="预期结果")
                for e in case.get('expected', []):
                    ET.SubElement(exp_node, "outline", text=str(e))

        # 2. 导出处理：必须包含 xml 声明，且编码为 UTF-8
        xml_data = ET.tostring(root, encoding='utf-8')
        reparsed = minidom.parseString(xml_data)
        
        # Xmind 报错往往是因为第一行缺失了 <?xml version="1.0" encoding="UTF-8"?>
        with open(opml_output, "w", encoding='utf-8') as f:
            f.write(reparsed.toprettyxml(indent="  "))
            
        print(f"✅ 转换成功: {opml_output}")

    except Exception as e:
        print(f"❌ 发生错误: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python json_to_opml.py input.json output.opml")
    else:
        convert_json_to_opml(sys.argv[1], sys.argv[2])