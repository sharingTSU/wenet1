"""
验证模块导入路径是否正确
"""
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

print("当前工作目录:", os.getcwd())
print("脚本目录:", SCRIPT_DIR)
print("Python路径:", sys.path[:3])
print()

try:
    from config import StressTestConfig, TestCriteria
    print("[OK] config.py 导入成功")
    config = StressTestConfig()
    print("  - 默认最大并发:", config.test_criteria.max_concurrent)
except Exception as e:
    print("[ERROR] config.py 导入失败:", e)
    import traceback
    traceback.print_exc()

try:
    from resource_monitor import ResourceMonitor, get_hardware_info
    print("[OK] resource_monitor.py 导入成功")
except Exception as e:
    print("[ERROR] resource_monitor.py 导入失败:", e)

try:
    from latency_measurer import LatencyMeasurer, LatencySummary
    print("[OK] latency_measurer.py 导入成功")
except Exception as e:
    print("[ERROR] latency_measurer.py 导入失败:", e)

try:
    from report_generator import ReportGenerator
    print("[OK] report_generator.py 导入成功")
except Exception as e:
    print("[ERROR] report_generator.py 导入失败:", e)

try:
    from client import WebSocketStreamingClient, AudioStreamer
    print("[OK] client.py 导入成功")
except Exception as e:
    print("[ERROR] client.py 导入失败:", e)

try:
    from stress_engine import StressTestEngine
    print("[OK] stress_engine.py 导入成功")
except Exception as e:
    print("[ERROR] stress_engine.py 导入失败:", e)

print()
print("检查模板目录...")
template_dir = os.path.join(SCRIPT_DIR, 'templates')
index_html = os.path.join(template_dir, 'index.html')
if os.path.exists(index_html):
    print("[OK] 模板文件存在:", index_html)
else:
    print("[ERROR] 模板文件不存在:", index_html)

print()
print("=" * 50)
print("验证完成!")
print("=" * 50)
