from datetime import datetime
import json
import os
import re
import base64
import requests
import shutil
import xml.etree.ElementTree as ET
from appium import webdriver
from appium.options.common import AppiumOptions

from skill.base_appium_skill import BaseAppiumSkill


# ==========================================
# 1. 核心工具类：本地对齐与 XML 解析
# ==========================================
class LocalUtils:
    @staticmethod
    def parse_bounds(bounds_str):
        """解析 XML 里的 [left,top][right,bottom] 格式"""
        nums = re.findall(r'\d+', bounds_str)
        return [int(n) for n in nums] if nums else [0, 0, 0, 0]

    @staticmethod
    def find_id_by_coords(xml_source, target_point, screen_size):
        """
        本地对齐：将 UI_TARS 的 0-1000 坐标映射回真机并抓取 ID
        """
        try:
            root = ET.fromstring(xml_source.encode('utf-8'))
            real_x = target_point[0] * screen_size['width'] / 1000
            real_y = target_point[1] * screen_size['height'] / 1000
            
            best_node = None
            for node in root.iter():
                bounds = node.get('bounds')
                if bounds:
                    l, t, r, b = LocalUtils.parse_bounds(bounds)
                    if l <= real_x <= r and t <= real_y <= b:
                        best_node = node # 覆盖逻辑，获取最深层节点
            
            return best_node.get('resource-id') if best_node is not None else None
        except Exception as e:
            print(f"解析 XML 失败: {e}")
            return None

# ==========================================
# 2. 视觉代理：火山引擎 Doubao-Seed 动态寻址
# ==========================================
class VisionAgent:
    def __init__(self, api_key, endpoint_id, is_mock=False):
        self.api_key = api_key
        self.endpoint_id = endpoint_id
        self.url = "https://ark.cn-beijing.volces.com/api/v3/responses"
        self.is_mock = is_mock

    def _encode_image(self, image_path):
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def get_action_point(self, step, case_title, screenshot_path):
        """
        根据业务 JSON 字段动态构造通用 Prompt
        """
        if self.is_mock:
            print(f"  [Mock] 模拟识别: '{step['action']} {step['object']}'")
            return [500, 320]

        # 动态提取业务语义
        action = step.get('action', '定位')
        target = step.get('object', '目标元素')
        
        base64_image = self._encode_image(screenshot_path)
        
        # 构造通用的视觉推理 Prompt
        # 移除任何关于“设置”或“桌面”的特定硬编码，改为基于业务字段的通用指令
        dynamic_prompt = (
            f"任务目标：在图中定位并准备执行操作：{action} “{target}”。\n"
            f"当前场景上下文：{case_title}\n"
            "规则：\n"
            "1. 忽略顶部状态栏图标（如电量、时间、信号）。\n"
            f"2. 聚焦于“{target}”对应的完整交互区域（如整行条目或开关按钮），而非仅文字部分。\n" # 增加这一行增强语义
            "3. 仅输出该元素的中心坐标，格式为 [x, y]。禁止任何多余的解释文字。\n"
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.endpoint_id,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_image", "image_url": f"data:image/png;base64,{base64_image}"},
                        {"type": "input_text", "text": dynamic_prompt}
                    ]
                }
            ]
        }

        try:
            print(f"正在向火山引擎推理: {action} {target}...")
            response = requests.post(self.url, headers=headers, json=payload, timeout=60)
            # 如果报 400，这里会打印出详细的错误原因，非常有帮助
            if response.status_code != 200:
                print(f"❌ API 报错详情: {response.text}")
                response.raise_for_status()

            result = response.json()

            # 解析返回结果
            content = ""
            for item in result.get('output', []):
                for msg in item.get('content', []):
                    if 'text' in msg: content = msg['text']
                    elif 'output_text' in msg: content = msg['output_text']
            
            # 使用最后匹配原则提取 [x, y]
            numbers = re.findall(r'(\d+)[, \s]+(\d+)', content)
            if numbers:
                last_match = numbers[-1]
                return [int(last_match[0]), int(last_match[1])]
            return None
        except Exception as e:
            print(f"视觉推理 API 失败: {e}")
            return None

# ==========================================
# 3. 执行引擎：自动化流水线
# ==========================================
class Hydrator(BaseAppiumSkill):
    def __init__(self, driver, vision_agent):
        super().__init__(driver) # 关键：调用基类构造函数，完成 driver 注入
        self.vision_agent = vision_agent
        self.sample_dir="debug_screenshots"


    def cleanup(self):
        """
        清理本次 Session 产生的所有临时采样文件
        """
        try:
            if os.path.exists(self.sample_dir):
                # 方案 A：直接删除整个文件夹
                shutil.rmtree(self.sample_dir)
                # 方案 B：如果想保留文件夹只删内容
                # for file in os.listdir(self.sample_dir):
                #     os.remove(os.path.join(self.sample_dir, file))
                print(f"✨ [Cleanup] 已成功清理采样缓存目录: {self.sample_dir}")
        except Exception as e:
            print(f"⚠️ [Cleanup] 清理失败: {e}")

    def hydrate_step(self, step, case_title):
        """
        单步执行：视觉识别 -> 本地对齐 -> 资产固化 -> 点击执行
        """
        print(f"\n[Step] {step.get('action')} {step.get('object')}")

        # 1. 现场采样
        # shot_path = "current_env.png"
        # 1. 创建专门的临时截图目录
        debug_dir = "debug_screenshots"
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)

        # 2. 生成动态文件名：用时间戳或 UUID，甚至带上步骤名，方便排查
        timestamp = datetime.now().strftime("%H%M%S_%f")
        target_name = step.get('object', 'unknown').replace(" ", "_")
        shot_path = os.path.join(debug_dir, f"sample_{timestamp}_{target_name}.png")

        print(f"  [Hydrating] 分析目标: {step.get('object')} -> 采样保存至: {shot_path}")


        self.driver.save_screenshot(shot_path)
        raw_xml = self.driver.page_source
        
        # 2. 动态视觉寻址 (注入业务字段)
        point = self.vision_agent.get_action_point(step, case_title, shot_path)
        
        if point:
            # 3. 寻找 DOM 锚点
            found_id = LocalUtils.find_id_by_coords(raw_xml, point, self.screen_size)
            
            # 4. 资产固化到 JSON
            # 这种方式不会触碰 step 里的 assert_plan / memo / id
            if "automation_meta" not in step:
                step["automation_meta"] = {}
                
            step["automation_meta"].update({
                "last_known_coord": point,
                "resource_id": found_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S") # 建议用动态时间
            })
            
            # 5. 换算像素执行点击
            action = step.get('action')
            if not any(word in action for word in ["验证", "检查", "观察", "断言", "Assert"]):
                px_x = point[0] * self.screen_size['width'] / 1000
                px_y = point[1] * self.screen_size['height'] / 1000
                self.driver.tap([(px_x, px_y)])
                print(f"  ⚡ 执行点击: {point}")
            else:
                print(f"  👁️ 仅验证动作，跳过物理点击。")

            has_plan = "YES" if step.get("assert_plan") else "NO"
            print(f"  ✅ 成功：ID={found_id}, 坐标={point}, 携带断言计划: {has_plan}")
            return True,step
        else:
            print(f"  ❌ 失败：AI 未能定位目标。")
            return False,step


# ==========================================
# 4. 入口：Main 流程
# ==========================================
def get_default_driver():
    """默认的 Driver 启动逻辑"""
    options = AppiumOptions()
    options.set_capability("platformName", "Android")
    options.set_capability("automationName", "UiAutomator2")
    options.set_capability("deviceName", "emulator-5554")
    options.set_capability("noReset", True)
    return webdriver.Remote("http://localhost:4723", options=options)

def run_hydration(driver, input_json_path, output_json_path):
    """
    OpenClaw Skill 入口：录制与资产固化
    :param driver: Appium Driver 实例
    :param input_json_path: 原始业务逻辑 JSON
    :param output_json_path: 固化后的资产 JSON 路径
    """
    local_driver = driver if driver else get_default_driver()
    try:
        # 1. 初始化 AI 代理
        agent = VisionAgent(
            # 配置信息
            api_key=os.getenv("VOLC_API_KEY"),
            endpoint_id = os.getenv("VOLC_ENDPOINT_ID")
        )

        # 2. 初始化固化引擎
        hydrator = Hydrator(local_driver, agent)
        # 3. 读取原始数据
        with open(input_json_path, "r", encoding="utf-8") as f:
            test_data = json.load(f)

        print(f"🚀 开始录制采样共 {len(test_data['test_suites'])} 个场景...")


        # 4. 执行业务循环
        for suite in test_data["test_suites"]:
            for case in suite["cases"]:
                print(f"▶️ 正在采样用例: {case['title']}")
                for step in case["steps"]:
                    success, hydrated_step = hydrator.hydrate_step(step, case['title'])
                    if not success:
                        print(f"⚠️ 步骤 {step.get('object')} 采样失败，建议检查 AI 配置")

        # 5. 持久化固化后的资产
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False)

        print(f"✅ 资产固化完成，已保存至: {output_json_path}")
        return True

    finally:
        # 无论成功失败，清理现场
        hydrator.cleanup()
        # 关键点：如果是自己启动的，就自己负责关掉；如果是别人传的，保持开启。
        if driver is None and local_driver:
            local_driver.quit()

def main():
    # 配置信息
    VOLC_API_KEY = os.getenv("VOLC_API_KEY")
    VOLC_ENDPOINT_ID = os.getenv("VOLC_ENDPOINT_ID")

    # --- 2. 启动前自检 (Expert Tip: 提前拦截错误) ---
    missing_vars = []
    if not VOLC_API_KEY: missing_vars.append("VOLC_API_KEY")
    if not VOLC_ENDPOINT_ID: missing_vars.append("VOLC_ENDPOINT_ID")
    
    if missing_vars:
        print(f"❌ 启动失败！缺少环境变量配置: {', '.join(missing_vars)}")
        print("💡 请执行以下操作后重试：")
        print("   Windows: setx VOLC_API_KEY \"your_key\"")
        print("   macOS:   export VOLC_API_KEY=\"your_key\"")
        return
    
    options = AppiumOptions()
    options.set_capability("platformName", "Android")
    options.set_capability("automationName", "UiAutomator2")
    options.set_capability("deviceName", "emulator-5554")
    options.set_capability("noReset", True)

    driver = None
    try:
        print("--- 正在初始化设备 ---")
        driver = webdriver.Remote("http://localhost:4723", options=options)
        
        # 初始化
        agent = VisionAgent(VOLC_API_KEY, VOLC_ENDPOINT_ID, is_mock=False) # 调试建议先开 mock
        executor = Hydrator(driver, agent)

        phase1_path = "/output/TC_NetworkSettings_2026-03-11.json"  # 请确保文件名正确
        if not os.path.exists(phase1_path):
            print(f"❌ 错误：找不到原始用例文件 {phase1_path}")
            return

        with open(phase1_path, "r", encoding="utf-8") as f:
            test_data = json.load(f)


        # 遍历执行
        for suite in test_data["test_suites"]:
            for case in suite["cases"]:
                for step in case["steps"]:
                    executor.hydrate_step(step, case["title"])

        # 输出固化后的资产
        with open("../scripts/hydrated_result.json", "w", encoding="utf-8") as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False)
        print("\n🎉 资产固化完成！")

    except Exception as e:
        print(f"运行异常: {e}")
    finally:
        if driver: driver.quit()

if __name__ == "__main__":
    main()