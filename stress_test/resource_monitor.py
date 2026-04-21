"""
资源监控模块 - 监控CPU和内存使用情况
"""

import os
import platform
import time
import threading
from typing import Optional, List
from datetime import datetime

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from stress_test.config import ResourceStats, HardwareInfo


class ResourceMonitor:
    """资源监控器 - 监控CPU和内存使用情况"""

    def __init__(self, poll_interval_ms: float = 1000.0):
        """
        初始化资源监控器

        Args:
            poll_interval_ms: 轮询间隔（毫秒）
        """
        self.poll_interval_ms = poll_interval_ms
        self._stats: List[ResourceStats] = []
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._concurrent_clients: int = 0

    def start(self):
        """启动监控"""
        if self._monitoring:
            return

        if not PSUTIL_AVAILABLE:
            raise RuntimeError("psutil library is required for resource monitoring. "
                            "Please install it with: pip install psutil")

        self._monitoring = True
        self._stats.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop(self):
        """停止监控"""
        self._monitoring = False
        if self._monitor_thread is not None:
            self._monitor_thread.join(timeout=5.0)
            self._monitor_thread = None

    def _monitor_loop(self):
        """监控循环"""
        while self._monitoring:
            stats = self._get_current_stats()
            with self._lock:
                self._stats.append(stats)

            time.sleep(self.poll_interval_ms / 1000.0)

    def _get_current_stats(self) -> ResourceStats:
        """获取当前资源统计"""
        if not PSUTIL_AVAILABLE:
            return ResourceStats()

        cpu_percent = psutil.cpu_percent(interval=0)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_gb = memory.used / (1024 ** 3)

        return ResourceStats(
            timestamp=datetime.now().isoformat(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_gb=memory_used_gb,
            concurrent_clients=self._concurrent_clients
        )

    def update_concurrent_clients(self, count: int):
        """更新当前并发客户端数"""
        self._concurrent_clients = count

    def get_stats(self) -> List[ResourceStats]:
        """获取所有统计数据"""
        with self._lock:
            return list(self._stats)

    def get_summary(self) -> dict:
        """获取统计摘要"""
        stats = self.get_stats()

        if not stats:
            return {
                "avg_cpu_percent": 0.0,
                "peak_cpu_percent": 0.0,
                "min_cpu_percent": 0.0,
                "avg_memory_percent": 0.0,
                "peak_memory_percent": 0.0,
                "min_memory_percent": 0.0,
                "sample_count": 0
            }

        cpu_values = [s.cpu_percent for s in stats]
        memory_values = [s.memory_percent for s in stats]

        return {
            "avg_cpu_percent": sum(cpu_values) / len(cpu_values),
            "peak_cpu_percent": max(cpu_values),
            "min_cpu_percent": min(cpu_values),
            "avg_memory_percent": sum(memory_values) / len(memory_values),
            "peak_memory_percent": max(memory_values),
            "min_memory_percent": min(memory_values),
            "sample_count": len(stats)
        }

    def reset(self):
        """重置统计数据"""
        with self._lock:
            self._stats.clear()


def get_hardware_info() -> HardwareInfo:
    """获取硬件配置信息"""
    info = HardwareInfo()

    if PSUTIL_AVAILABLE:
        info.cpu_cores = psutil.cpu_count(logical=False) or 0
        info.cpu_threads = psutil.cpu_count(logical=True) or 0
        info.total_memory_gb = psutil.virtual_memory().total / (1024 ** 3)

        try:
            if platform.system() == "Windows":
                info.cpu_model = platform.processor()
            elif platform.system() == "Linux":
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if line.startswith('model name'):
                            info.cpu_model = line.split(':')[1].strip()
                            break
            elif platform.system() == "Darwin":
                import subprocess
                result = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'],
                                     capture_output=True, text=True)
                info.cpu_model = result.stdout.strip()
        except Exception:
            info.cpu_model = platform.processor()
    else:
        info.cpu_cores = os.cpu_count() or 0
        info.cpu_threads = os.cpu_count() or 0
        info.cpu_model = platform.processor()

    info.os_name = platform.system()
    info.os_version = platform.release()

    return info
