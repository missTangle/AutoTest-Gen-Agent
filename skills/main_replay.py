import math
import time
from datetime import datetime

from appium import webdriver
from appium.options.common import AppiumOptions
from appium.webdriver.common.appiumby import AppiumBy

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput

from skill.base_appium_skill import BaseAppiumSkill


# ==========================================
# 1. 核心工具类：空间距离计算
# ==========================================
class ReplayUtils:
    @staticmethod
    def calculate_distance(p1, p2):
        """计算两个物理像素坐标点之间的欧几里得距离"""
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    @staticmethod
    def find_best_match(elements, target_coord, screen_size):
        """
        在同 ID 元素中，寻找物理中心最接近 target_coord 的元素
        target_coord: 归一化坐标 [0-1000]
        """
        best_element = None
        min_distance = float('inf')
        
        target_px_x = target_coord[0] * screen_size['width'] / 1000
        target_px_y = target_coord[1] * screen_size['height'] / 1000

        for el in elements:
            try:
                location = el.location
                size = el.size
                el_center_x = location['x'] + size['width'] / 2
                el_center_y = location['y'] + size['height'] / 2
                
                dist = ReplayUtils.calculate_distance(
                    (target_px_x, target_px_y), 
                    (el_center_x, el_center_y)
                )
                
                if dist < min_distance:
                    min_distance = dist
                    best_element = el
            except:
                continue
                
        return best_element, min_distance


class SmartAsserter:
    def __init__(self, driver, ui_tars_client, json_path, retry_count=2, retry_interval=2):
        """
        :param retry_count: 视觉识别失败后的重试次数
        :param retry_interval: 每次重试前的等待时间（秒）
        """
        self.driver = driver
        self.ai = ui_tars_client
        self.json_path = json_path
        self.retry_count = retry_count
        self.retry_interval = retry_interval

        with open(json_path, 'r', encoding='utf-8') as f:
            self.case_data = json.load(f)

    # --- 1. 定义结构化 Prompt 模板 ---
    PROMPT_TEMPLATES = {
        "TEXT_EXISTS": {
            "instruction": "验证截图中是否存在指定文字锚点：'{anchor}'。",
            "rule": "1. 仅寻找视觉可见的文字内容。2. 忽略背景噪音。",
            "example": '{"passed": true, "element_meta": {"id": null, "x": 450, "y": 120}, "reason": "找到目标文字"}'
        },
        "CHECKED_STATUS": {
            "instruction": "定位文字 '{anchor}' 及其关联的开关/复选框，验证其选中状态是否为 '{expect_val}'。",
            "rule": (
                "1. 定位组件：寻找与 '{anchor}' 文字相邻的 Switch 或 Checkbox 控件。\n"
                "2. 状态识别：观察滑块位置（左 vs 右）、颜色（高亮 vs 置灰/白色）或勾选标志。\n"
                "3. 判定逻辑：预期为 'true' 对应开启/勾选；'false' 对应关闭/未勾选。"
            ),
            "example": '{"passed": false, "element_meta": {"id": "com.android.settings:id/switch_widget", "x": 900, "y": 450}, "reason": "状态不符"}'
        },
        "VISUAL_AGENT": {
            "instruction": "作为 UI 验证专家，请判断图中 '{anchor}' 的当前状态是否符合预期：'{expect_val}'。",
            "rule": (
                "1. 综合分析：结合文字、颜色（如置灰）、图标符号（如状态角标）及上下文语义进行判定。\n"
                "2. 判定原则：只要视觉传达的意图与预期一致（如预期关闭，实际通过图标或文字表达了关闭），即为 passed: true。\n"
                "3. 坐标定位：若检测到目标，请返回其中心点绝对像素坐标 [x, y]。"
            ),
            "example": '{"passed": boolean, "element_meta": {"x": int, "y": int}, "reason": "简述判定依据"}'
        }
    }

    def _capture_evidence(self, suite_idx, case_idx, step_idx):
        evidence_dir = os.path.join("reports", "evidence")
        if not os.path.exists(evidence_dir):
            os.makedirs(evidence_dir)

        filename = f"fail_S{suite_idx}_C{case_idx}_ST{step_idx}.png"
        filepath = os.path.join(evidence_dir, filename)
        self.driver.save_screenshot(filepath)
        # 返回相对路径，方便 Markdown 引用
        return f"evidence/{filename}"

    # --- 2. 核心执行入口 ---
    def execute_step_with_assert(self, suite_idx, case_idx, step_idx, auto_retry=True):
        """
        :param auto_retry: 是否开启重试，供后续针对特定步骤灵活关闭
        """
        step = self.case_data['test_suites'][suite_idx]['cases'][case_idx]['steps'][step_idx]
        plan = step.get("assert_plan")

        print(f"进入断言，step:{step},plan:{plan}")

        if not plan or plan.get("strategy") == "NONE":
            strategy_name = plan.get("strategy") if plan else "UNDEFINED"
            print(f"⏩ [Skip Assert] step:{step_idx + 1}, strategy:{strategy_name}，跳过校验")
            return True

        # 1. 尝试缓存加速
        cached_meta = step.get("automation_meta")
        if cached_meta and plan["strategy"] != "VISUAL_AGENT":
            if self._try_quick_assert(plan, cached_meta):
                print(f"strategy:{plan['strategy']}, 通过缓存数据快速验证")
                return True

        # 2. 启动视觉分析（带重试循环）
        print("⬇️启动视觉分析.......")
        attempts = self.retry_count + 1 if auto_retry else 1
        last_result = None

        for i in range(attempts):
            print(f"🔍 [AI Analyze] 尝试第 {i + 1} 次校验: {plan['strategy']}")
            screenshot = self.driver.get_screenshot_as_base64()
            try:
                result = self._call_ui_tars(plan, screenshot)
                if result is None:
                    raise ValueError("AI 返回格式非法")
                passed = result.get("passed")

                if result and passed:
                    print(f"✅断言成功，开始回填")
                    # 断言成功，立即执行回填并返回
                    if result.get("element_meta"):
                        self._back_fill(suite_idx, case_idx, step_idx, result["element_meta"], result["reason"],passed)
                    return True

                last_result = result
                if i < attempts - 1:
                    print(f"⏳ 断言未通过，{self.retry_interval}s 后重试...")
                    time.sleep(self.retry_interval)
            except Exception as e:
                print(f"⚠️ 断言执行异常: {e}")
                # 即使失败了，也要确保 back_fill 能被调用，记录下失败状态
                self._back_fill(suite_idx, case_idx, step_idx, {}, f"断言异常: {str(e)}", passed=False)

        # 3. 最终失败处理
        if last_result and last_result.get("element_meta"):
            # 即使最终失败（比如状态不对），也回填位置信息，方便后续排查或自愈
            print(f"❌最终断言失败，仍回填信息，方便排查")
            img_path = self._capture_evidence(suite_idx, case_idx, step_idx)
            meta_to_save = last_result.get("element_meta", {})
            meta_to_save["screenshot_path"] = img_path
            self._back_fill(suite_idx, case_idx, step_idx, meta_to_save, last_result["reason"], False)



        return False

    # --- 3. 视觉分析逻辑 (Analyze) ---
    def _call_ui_tars(self, plan, screenshot):
        strategy = plan["strategy"]
        template = self.PROMPT_TEMPLATES[strategy]
        anchor = plan["anchor"]
        # 如果 expect_val 为空，我们给它一个默认的“存在且正常”的语义
        expect = plan.get("expect_val") or "正常显示并可见"

        # --- 深度定制 System Prompt ---
        # 将 instruction 提升到系统指令级别，确保模型明白它的核心任务
        # 获取模板，如果 strategy 不存在，默认使用 VISUAL_VLM
        template = self.PROMPT_TEMPLATES.get(strategy, self.PROMPT_TEMPLATES["VISUAL_AGENT"])

        # 获取 rule，如果模板里没写 rule，给一个通用的通用规则
        rule_content = template.get("rule", "请基于视觉直觉和上下文语义进行判定。")

        system_prompt = (
            f"{template['instruction'].format(anchor=anchor, expect_val=expect)}\n\n"
            f"【执行规则】\n{rule_content}\n\n"
            "【输出格式】\n仅返回标准 JSON，禁止解释。JSON KEY只能使用双引号，不要使用单引号\n"
            f"参考格式：{template['example']}"
        )

        # User Prompt 此时只需强调“请基于此截图执行分析”
        user_prompt = f"请分析当前屏幕截图，'{anchor}' 元素的表现是否符合：{expect}。"

        try:
            # 调用 UI_TARS 接口
            response = self.ai.chat(
                system=system_prompt,
                prompt=user_prompt,
                image_base64=screenshot
            )
            # 兼容处理：有些模型会返回 ```json ... ``` 块
            content = response.strip().replace('```json', '').replace('```', '').replace('```', '')
            if "'" in content and '"' not in content:
                content = content.replace("'", '"')
            return json.loads(content)
        except Exception as e:
            print(f"❌ UI_TARS 解析失败: {e}")
            return None

    # --- 4. 回填持久化逻辑 (Back-fill) ---
    def _back_fill(self, s_idx, c_idx, st_idx, meta, reason, passed):
        """
        将 AI 发现的物理属性精准回填到内存和文件
        """
        step = self.case_data['test_suites'][s_idx]['cases'][c_idx]['steps'][st_idx]
        # 获取旧的 meta，保留可能存在的原始信息
        old_meta = step.get("automation_meta", {})

        # 构造元数据
        new_meta = {
            "status": "PASS" if passed else "FAIL",  # 新增状态
            "resource_id": meta.get("id") or old_meta.get("resource_id"),
            "last_known_coord": [meta.get("x"), meta.get("y")],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ai_verified_reason": reason
        }

        # 更新内存数据
        step["automation_meta"] = new_meta

        # 持久化到 JSON 文件 (确保鲁棒性：写入临时文件再改名，防止写入崩溃)
        temp_path = self.json_path + ".tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(self.case_data, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, self.json_path)
        print(f"💾 [Back-fill] 已更新步骤元数据并持久化到文件")

    # --- 5. 快速断言辅助 ---
    def _try_quick_assert(self, plan, meta):
        # 此处使用 Appium 原生逻辑根据缓存的 ID 检查状态
        # 为了简洁暂略，逻辑基本是：driver.find_element(id).get_attribute('checked')
        return False

# ==========================================
# 3. 回放引擎
# ==========================================
class ReplayEngine(BaseAppiumSkill):
    def __init__(self, driver, asserter):
        super().__init__(driver) # 注入 OpenClaw 提供的 driver
        self.asserter = asserter  # 组合 SmartAsserter
        # self.screen_size = self.driver.get_window_size()
        # 定义滑动参数
        self.start_y = self.screen_size['height'] * 0.7
        self.end_y = self.screen_size['height'] * 0.3
        self.center_x = self.screen_size['width'] / 2

    def _seek_element(self, target_id, target_coord, target_text=None, max_swipes=3):
        """
        探测并滑寻元素：如果在当前页找不到符合距离条件的元素，则尝试滑动
        """
        for i in range(max_swipes + 1):  # +1 是为了包含“不滑动直接找”的第一次尝试
            candidates = self.driver.find_elements(AppiumBy.ID, target_id)

            # 这里的逻辑优化：不仅找最近，还要找“对”
            best_el = None
            min_dist = float('inf')

            # 物理目标坐标（用于计算距离）
            target_px = (
                target_coord[0] * self.screen_size['width'] / 1000,
                target_coord[1] * self.screen_size['height'] / 1000
            )

            for el in candidates:
                # --- 1. 文本一票通过制 ---
                try:
                    current_text = el.text
                    if target_text and target_text.strip() == current_text.strip():
                        print(f"  ✨ 文本完美匹配锁定: '{current_text}'")
                        return el, 0
                except:
                    pass  # 忽略获取 text 失败的节点

                # 距离逻辑：计算中心点距离
                loc = el.location
                sz = el.size
                # 否则按距离找
                el_center = (loc['x'] + sz['width'] / 2, loc['y'] + sz['height'] / 2)
                dist = ReplayUtils.calculate_distance(target_px, el_center)

                if dist < min_dist:
                    min_dist = dist
                    best_el = el

            # 只有距离小于 150px 且当前节点在屏幕可视范围内才认为找到了
            # (避免点到被顶部/底部状态栏遮挡的半个元素)
            if best_el and (min_dist < 50 or min_dist == 0):
                return best_el, min_dist

            # 如果没找到，或者找到的那个太远了，说明目标可能被挤出屏幕了
            if i < max_swipes:
                print(f"  🔍 距离偏移过大({int(min_dist)}px)，目标可能在视口外，执行第 {i + 1} 次滑寻...")
                # 执行滑动：从屏幕下方滑向上方
                self.driver.swipe(
                    self.screen_size['width'] / 2, self.screen_size['height'] * 0.7,
                    self.screen_size['width'] / 2, self.screen_size['height'] * 0.3,
                    800
                )
                time.sleep(1.5)

        return None, float('inf')

    def scroll_and_find(self, target_id, max_swipes=5):
        """
        循环执行滑动并寻找目标 ID
        """
        for i in range(max_swipes):
            candidates = self.driver.find_elements(AppiumBy.ID, target_id)
            if candidates:
                # 找到了，但还要确保它在屏幕中心区域，避免点到被遮挡的边缘
                return candidates

            print(f"  🔍 屏幕内未找到 {target_id}，执行第 {i + 1} 次向上滑动...")
            # 从屏幕 80% 高度滑到 20%
            self.driver.swipe(
                self.screen_size['width'] / 2, self.screen_size['height'] * 0.8,
                self.screen_size['width'] / 2, self.screen_size['height'] * 0.2,
                1000  # 滑动耗时
            )
            time.sleep(1)  # 等待列表回弹稳定
        return []

    def _do_swipe(self, direction="up"):
        """
        实现受控滑动
        direction="up": 手指向上滑，内容向下滚（寻找下方的元素）
        direction="down": 手指向下滑，内容向上滚（寻找上方的元素）
        """
        # 获取屏幕尺寸，增加防御性容错
        size = self.driver.get_window_size()
        width = size['width']
        height = size['height']

        # 计算滑动起始和终点坐标 (避开边缘，取中心 60% 区域)
        center_x = width / 2
        top_y = height * 0.25
        bottom_y = height * 0.75

        try:
            if direction == "up":
                print(f"  🎬 执行滑动: [手指向上] (寻找下方内容)")
                # 从下往上滑
                self.driver.swipe(center_x, bottom_y, center_x, top_y, 800)
            else:
                print(f"  🎬 执行滑动: [手指向下] (寻找上方内容)")
                # 从上往下滑
                self.driver.swipe(center_x, top_y, center_x, bottom_y, 800)

            # 滑动后的惯性等待，确保 UI 树刷新
            time.sleep(1.2)
        except Exception as e:
            print(f"  ❌ 滑动失败: {e}")

    def calculate_score(self, element, target_text, meta):
        """计算候选元素的综合得分"""
        score = 0
        try:
            # 1. 文本评分 (核心权重: 100)
            current_text = element.text.strip()
            if current_text:  # 只要有文字就打印出来，看看抓到的是什么
                print(f" [Debug] 扫描到文字: '{current_text}' vs 目标: '{target_text}'")

                # 深度清洗逻辑：
                current_clean = current_text.replace('\u00a0', ' ').strip().lower()
                target_clean = target_text.replace('\u00a0', ' ').strip().lower()

                # 为了彻底排除干扰，我们甚至可以在调试时打印出它们的 repr() 看看真实面目
                print(f"    [Trace] current_repr: {repr(current_clean)}")
                print(f"    [Trace] target_repr: {repr(target_clean)}")

                if current_clean == target_clean:
                    score += 100
                elif target_clean in current_clean or current_clean in target_clean:
                    score += 80


            # 2. 坐标距离评分 (消歧义权重: 30)
            target_coord = meta.get("last_known_coord")
            if target_coord:
                target_px = (
                    target_coord[0] * self.screen_size['width'] / 1000,
                    target_coord[1] * self.screen_size['height'] / 1000
                )
                loc = element.location
                sz = element.size
                center = (loc['x'] + sz['width'] / 2, loc['y'] + sz['height'] / 2)
                dist = ReplayUtils.calculate_distance(target_px, center)
                # 300px 内线性衰减
                score += max(0, 30 * (1 - dist / 300))

            # 3. ID 评分 (辅助权重: 20)
            if element.get_attribute("resource-id") == meta.get("resource_id"):
                score += 20
        except Exception as e:
            print(f"异常：{e}")
            return 0
        return score


    def _dispatch_action(self, element, step):
        """
        动作分发器：执行具体的物理操作
        """
        action = step.get("action", "")
        content = step.get("memo", "")  # 兼容输入场景，memo 暂时充当输入值

        try:
            if "点击" in action:
                element.click()
                print("    ⚡ 执行 [点击] 成功")
            elif "输入" in action:
                element.clear()
                element.send_keys(content)
                print(f"    ⌨️ 执行 [输入] 成功: '{content}'")
            elif "长按" in action:
                actions = ActionChains(self.driver)
                # 移动到元素并按下，等待1.5秒后释放
                actions.click_and_hold(element).pause(1.5).release().perform()
                print("    👆 执行 [长按] 成功")
            else:
                # 默认执行点击，保持鲁棒性
                element.click()
                print(f"    ⚡ 执行默认动作 [点击] 成功")
            return True
        except Exception as e:
            print(f"    ❌ 动作分发执行失败: {str(e)}")
            return False


    def _perform_physical_action(self, step):
        target_text = step.get("object")
        action = step.get('action')
        meta = step.get("automation_meta", {})


        last_screen_fingerprint = set()
        current_direction = "up"  # 初始方向
        has_switched_direction = False

        # 记录寻址过程中发现的最佳模糊匹配选手 (score, element)
        best_backup_candidate = None

        print(f"\n[Replay] 执行动作: {action} {target_text}")

        for i in range(10):  # 最多尝试 5 次滑寻
            current_screen_texts = set()
            scored_list = []
            # 获取当前所有元素
            candidates = self.driver.find_elements(AppiumBy.XPATH, "//*")

            for el in candidates:
                try:
                    # 获取文本并存入当前屏指纹
                    txt = el.text.strip()
                    if txt: current_screen_texts.add(txt)

                    score = self.calculate_score(el, target_text, meta)
                    if score > 0:
                        scored_list.append((score, el))
                except:
                    continue

            # 1. 评分决策
            scored_list.sort(key=lambda x: x[0], reverse=True)
            if scored_list:
                best_score, best_el = scored_list[0]
                # 策略：如果达到了 100 分（完美匹配），直接执行，无需犹豫
                if best_score >= 100:
                    print(f"  🎯 完美匹配! 分数: {int(best_score)}")
                    return self._dispatch_action(best_el, step)
                    # if action == "点击":
                    #     best_el.click()
                    # return True

                # 策略：如果是 80-99 分（模糊匹配），我们不立即点，而是记录下来
                # 继续滑动，直到滑到底部还没找到 100 分，再回头点这个 80 分的“备胎”
                if best_score >= 80:
                    if best_backup_candidate is None or best_score > best_backup_candidate[0]:
                        print(f"  💡 发现疑似目标 '{best_el.text}' (Score: {int(best_score)})，暂存并继续搜寻完美项...")
                        best_backup_candidate = (best_score, best_el)

            # 2. 触底/触顶检测逻辑 ---
            # i > 0 确保至少滑动过一次再对比
            if i > 0 and current_screen_texts.issubset(last_screen_fingerprint):
                if not has_switched_direction:
                    print(f"  🔄 沿 {current_direction} 方向已到底，开始反向搜寻...")
                    current_direction = "down"  # 掉头
                    has_switched_direction = True
                    last_screen_fingerprint = set()  # 清空指纹，重新开始判定新方向的底部
                    # 掉头后先滑一下，避免死循环
                    self._do_swipe(direction=current_direction)
                    continue
                else:
                    print("  🛑 全局搜寻完毕（双向均触底），未发现目标。")
                    break
            last_screen_fingerprint = current_screen_texts  # 更新指纹

            # 3. 执行当前方向的滑动
            print(f"  🔍 第 {i + 1} 次尝试未果，沿 {current_direction} 方向滑寻...")
            self._do_swipe(direction=current_direction)
            time.sleep(1.5)

        # --- 最终兜底：如果整个列表滑完了都没 100 分，才启动备胎 ---
        if best_backup_candidate:
            score, el = best_backup_candidate
            print(f"  ⚠️ 未找到完美匹配，执行最高分备胎点击 (Score: {int(score)}): '{el.text}'")
            return self._dispatch_action(el, step)

        print(f"  ❌ 最终失败：未能定位到文本 '{target_text}'")
        return False

    def execute_step(self, suite_idx, case_idx, step_idx):
        """
        融合逻辑：执行动作 -> 结果断言 -> 自动回填
        """
        # 获取当前步骤数据
        suite = self.asserter.case_data['test_suites'][suite_idx]
        case = suite['cases'][case_idx]
        step = case['steps'][step_idx]
        action = step.get("action", "")
        target_text = step.get("object")

        print(f"\n🚀 [Step {step_idx + 1}] 动作: {action} {target_text}")
        # --- 核心拦截：如果是验证/观察，只尝试定位/感知，不触发物理动作 ---
        # 如果是验证类动作，不触发物理点击/输入，确保 UI 状态不被破坏
        passive_keywords = ["验证", "观察", "检查", "Assert", "Verify", "Observe"]
        is_passive_action = any(k in action for k in passive_keywords)
        if is_passive_action:
            print(f"  👁️ [感知模式] 检测到验证步，跳过物理交互，直接进入断言...")
            action_success = True  # 验证步的成功与否由断言阶段决定
        else:
            # 物理交互动作：点击、输入、长按等
            action_success = self._perform_physical_action(step)
            if not action_success:
                print(f"  ⚠️ 物理定位未发现完美目标，将尝试在断言阶段通过 AI 视觉自愈...")

        # 即使动作没找到，断言器也会通过 UI_TARS 截图看一眼，
        # 如果是因为页面没滑到位，AI 会在断言失败时返回坐标，下一次回填后就对了。
        time.sleep(1.5)  # 等待动作后的 UI 稳定
        print(f"  🔍 进入断言阶段...")
        # 调用 SmartAsserter 的核心方法
        assert_passed = self.asserter.execute_step_with_assert(
            suite_idx, case_idx, step_idx, auto_retry=True
        )

        return assert_passed


    def execute_step_old(self, step):
        """执行固化资产中的单步操作"""
        meta = step.get("automation_meta")
        if not meta:
            print(f"  ⏩ 跳过步骤: '{step.get('object')}' (未固化)")
            return False

        target_id = meta.get("resource_id")
        target_coord = meta.get("last_known_coord")

        # 提取步骤中的 object 作为文本参考（例如 "Internet选项"）
        target_text = step.get("object")
        
        print(f"\n[Replay] 执行动作: {step.get('action')} {step.get('object')}")
        print(f"\n[Replay] 正在寻找: {step.get('object')} (ID: {target_id})")

        # 策略 1: 核心策略：滑寻 + 空间距离匹配
        if target_id:
            best_el, dist = self._seek_element(target_id, target_coord, target_text)
            if best_el:
                best_el.click()
                print(f"  🎯 成功: 经过 {target_id} 匹配并点击 (偏移: {int(dist)}px)")
                return True

        # 2. 极端兜底：如果滑了几次都找不到 ID，且当前步骤在逻辑上必须执行
        # 我们可以选择在当前屏幕的原始坐标点一下（万一 ID 变了但位置没变）
        print("  ⚠️ 滑寻未果，尝试在原始固化坐标执行兜底点击...")
        px_x = target_coord[0] * self.screen_size['width'] / 1000
        px_y = target_coord[1] * self.screen_size['height'] / 1000
        self.driver.tap([(px_x, px_y)])
        print(f"  ✅ 成功: 直接点击坐标 [{px_x}, {px_y}]")
        return True


import os
import json
from volcenginesdkarkruntime import Ark

# ==========================================
# 1. 严格复刻 executor.py 中的客户端封装
# ==========================================
class UITarsClient:
    def __init__(self):
        # 严格遵循 executor.py：从环境变量读取，绝不写死在代码里
        self.api_key = os.environ.get("VOLC_API_KEY")
        self.endpoint_id = os.environ.get("VOLC_ENDPOINT_ID")
        self.url = "https://ark.cn-beijing.volces.com/api/v3"

        if not self.api_key or not self.endpoint_id:
            raise ValueError("❌ 错误：请先设置环境变量 VOLC_API_KEY 和 VOLC_ENDPOINT_ID")

        # 初始化 Ark 客户端
        self.client = Ark(api_key=self.api_key, base_url=self.url)

    def chat(self, system, prompt, image_base64):
        """
        封装 Ark 视觉模型的调用逻辑
        """
        response = self.client.chat.completions.create(
            model=self.endpoint_id,
            messages=[
                {
                    "role": "system",
                    "content": system
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            # 视觉模型通常不需要太高的温度
            temperature=0.01,
        )
        return response.choices[0].message.content

# ==========================================
# 2. 统一初始化入口
# ==========================================
def init_ui_tars_client():
    """
    供 main_replay 调用的初始化函数
    """
    try:
        client = UITarsClient()
        print(f"✅ [executor逻辑] UI_TARS 客户端初始化成功")
        return client
    except Exception as e:
        print(f"❌ UI_TARS 初始化失败: {e}")
        raise e


class AppiumReplaySkill:
    def __init__(self, driver, case_file_path):
        self.driver = driver
        # 初始化我们之前的两个核心组件
        self.asserter = SmartAsserter(case_file_path)
        self.executor = ReplayEngine(driver, self.asserter)

    def execute_task(self):
        """
        OpenClaw Skill 的入口函数
        """
        case_data = self.asserter.case_data
        for suite_idx, suite in enumerate(case_data['test_suites']):
            print(f"--- 场景: {suite['scene']} ---")
            for case_idx, case in enumerate(suite['cases']):
                self._run_single_case(suite_idx, case_idx)

    def _run_single_case(self, suite_idx, case_idx):
        case = self.asserter.case_data['test_suites'][suite_idx]['cases'][case_idx]
        print(f"\n▶️ 开始回放用例: {case['title']}")

        for step_idx in range(len(case['steps'])):
            # 这里调用我们重构后的 execute_step
            # 它内部已经包含了：动作分发 -> 拦截观察步 -> 视觉断言 -> 自动回填
            success = self.executor.execute_step(suite_idx, case_idx, step_idx)

            if not success:
                print(f"❌ 步骤 {step_idx + 1} 失败，中断当前用例。")
                break

# ==========================================
# 3. 入口函数
# ==========================================
def run_reply(driver, asset_file_path):
    tars_client = init_ui_tars_client()
    try:
        print("🚀 启动 Appium 回放引擎...")
        asserter = SmartAsserter(
            driver=driver,
            ui_tars_client=tars_client,
            json_path=asset_file_path,
            retry_count=2,
            retry_interval=3
        )

        engine = ReplayEngine(driver, asserter)

        # --- 按顺序回放 ---
        for s_idx, suite in enumerate(asserter.case_data['test_suites']):
            print(f"\n--- 场景: {suite['scene']} ---")
            for c_idx, case in enumerate(suite['cases']):
                for st_idx, _ in enumerate(case['steps']):
                    # 一键完成：滑寻、点击、AI断言、坐标回填
                    success = engine.execute_step(s_idx, c_idx, st_idx)
                    time.sleep(2)

                    if not success:
                        print(f"❌ 流程在步骤 {st_idx + 1} 彻底失败，中断用例")
                        break

        print("\n🎉 所有用例回放完成！")
        return asserter.case_data

    except Exception as e:
        print(f"❌ 回放过程中出现异常: {e}")
    finally:
        return asserter.case_data
        if driver:
            driver.quit()

def main_replay():
    # --- 配置 Appium ---
    options = AppiumOptions()
    options.set_capability("platformName", "Android")
    options.set_capability("automationName", "UiAutomator2")
    options.set_capability("deviceName", "emulator-5554")
    options.set_capability("noReset", True)

    tars_client = init_ui_tars_client()

    driver = None
    try:
        print("🚀 启动 Appium 回放引擎...")
        driver = webdriver.Remote("http://127.0.0.1:4723", options=options)


        
        # --- 加载资产 ---
        asset_file = "../scripts/hydrated_result.json"
        with open(asset_file, "r", encoding="utf-8") as f:
            test_data = json.load(f)

        asserter = SmartAsserter(
            driver=driver,
            ui_tars_client=tars_client,
            json_path=asset_file,
            retry_count=2,
            retry_interval=3
        )

        engine = ReplayEngine(driver, asserter)

        # --- 按顺序回放 ---
        for s_idx, suite in enumerate(asserter.case_data['test_suites']):
            print(f"\n--- 场景: {suite['scene']} ---")
            for c_idx, case in enumerate(suite['cases']):
                for st_idx, _ in enumerate(case['steps']):
                    # 一键完成：滑寻、点击、AI断言、坐标回填
                    success = engine.execute_step(s_idx, c_idx, st_idx)
                    time.sleep(2)

                    if not success:
                        print(f"❌ 流程在步骤 {st_idx + 1} 彻底失败，中断用例")
                        break

        print("\n🎉 所有用例回放完成！")

    except Exception as e:
        print(f"❌ 回放过程中出现异常: {e}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main_replay()