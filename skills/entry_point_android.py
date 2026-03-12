# OpenClaw 的主执行入口
from appium import webdriver
from appium.options.common import AppiumOptions

from executor import run_hydration
from main_replay import run_reply
from utils.report_generator import ReportGenerator

def openclaw_main_task(json_case_path, output_asset_json_path, asset_json_path, task_mode="HYDRATE"):
    # 1. OpenClaw 统一管理 Driver 的启动
    print("--- OpenClaw: 正在启动全局驱动 ---")
    options = AppiumOptions()
    options.set_capability("platformName", "Android")
    options.set_capability("automationName", "UiAutomator2")
    options.set_capability("deviceName", "emulator-5554")
    options.set_capability("noReset", True)
    options.set_capability("appium:newCommandTimeout", 300)  # 给 AI 预留 5 分钟


    driver = webdriver.Remote("http://localhost:4723", options=options)

    try:
        if task_mode == "HYDRATE":
            run_hydration(driver, json_case_path, output_asset_json_path)

        elif task_mode == "REPLAY":
            updated_data = run_reply(driver, asset_json_path)
            gen=ReportGenerator(updated_data)
            gen.generate_markdown()

    finally:
        # 4. OpenClaw 统一回收钥匙
        print("--- OpenClaw: 任务结束，关闭驱动 ---")

        try:
            if driver:
                # 动态获取当前的包名
                target_pkg = driver.current_package
                # 强制停止设置 App，下次启动它会回到主界面
                # 增加防御性判断：不要误杀了系统桌面（Launcher）
                # 典型的桌面包名：com.google.android.apps.nexuslauncher, com.android.launcher
                if target_pkg and "launcher" not in target_pkg.lower():
                    print(f"  🔍 探测到当前运行应用: {target_pkg}")
                    driver.terminate_app(target_pkg)
                    print(f"  ✅ 已重置应用状态")
                else:
                    # 如果就在桌面，或者没识别到，就按一下 HOME 键作为兜底
                    driver.press_keycode(3)
                    print("  🏠 处于桌面或未知应用，执行 Home 键返回")

                # 检查 session 是否还在，防止 double-quit 或销毁已失效 session
                driver.quit()
        except Exception:
            print("💡 驱动 Session 已自动失效，无需手动关闭。")


if __name__=="__main__":
    json_case_path="/Users/susiecheng/Documents/AI_Agent/Skills/output/TC_NetworkSettings_2026-03-11.json"
    asset_path="../output/hydrated_result_debug.json"
    # openclaw_main_task(json_case_path,asset_path,asset_path,"HYDRATE")
    openclaw_main_task(json_case_path, asset_path, asset_path, "REPLAY")