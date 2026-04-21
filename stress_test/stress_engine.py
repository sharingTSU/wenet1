"""
压力测试引擎 - 核心测试控制逻辑
"""

import asyncio
import threading
import time
import os
from typing import Optional, List, Callable, Any, Dict
from datetime import datetime
from dataclasses import dataclass

from config import (
    StressTestConfig, TestCriteria, TestResult,
    ConcurrentTestResult, TestProgress, HardwareInfo,
    generate_test_id
)
from client import ClientManager
from resource_monitor import ResourceMonitor, get_hardware_info
from latency_measurer import LatencyMeasurer, LatencySummary


@dataclass
class TestPhaseResult:
    """单轮测试阶段结果"""
    concurrent_count: int
    latency_summary: LatencySummary
    resource_summary: dict
    passed: bool
    fail_reason: str = ""


class StressTestEngine:
    """压力测试引擎"""

    def __init__(self, config: StressTestConfig):
        """
        初始化压力测试引擎

        Args:
            config: 测试配置
        """
        self.config = config
        self._running = False
        self._paused = False
        self._progress: Optional[TestProgress] = None
        self._test_result: Optional[TestResult] = None
        self._hardware_info: Optional[HardwareInfo] = None

        self._progress_callback: Optional[Callable[[TestProgress], None]] = None
        self._result_callback: Optional[Callable[[TestResult], None]] = None

        self._resource_monitor: Optional[ResourceMonitor] = None
        self._client_manager: Optional[ClientManager] = None
        self._latency_measurer: Optional[LatencyMeasurer] = None

        self._max_concurrent_achieved: int = 0
        self._concurrent_test_results: List[ConcurrentTestResult] = []

    def set_progress_callback(self, callback: Callable[[TestProgress], None]):
        """设置进度回调"""
        self._progress_callback = callback

    def set_result_callback(self, callback: Callable[[TestResult], None]):
        """设置结果回调"""
        self._result_callback = callback

    def _update_progress(self, progress: TestProgress):
        """更新进度"""
        self._progress = progress
        if self._progress_callback:
            self._progress_callback(progress)

    async def start_test(self) -> TestResult:
        """
        开始压力测试

        Returns:
            完整测试结果
        """
        if self._running:
            raise RuntimeError("Test is already running")

        self._running = True
        self._paused = False
        self._max_concurrent_achieved = 0
        self._concurrent_test_results = []

        self._test_result = TestResult(
            test_id=generate_test_id(),
            start_time=datetime.now().isoformat()
        )

        self._update_progress(TestProgress(
            current_concurrent=0,
            total_concurrent=self.config.test_criteria.max_concurrent,
            status="initializing",
            message="正在初始化测试环境...",
            percentage=0.0
        ))

        self._hardware_info = get_hardware_info()
        self._test_result.hardware_info = self._hardware_info
        self._test_result.engine_params = self.config.engine_params
        self._test_result.test_criteria = self.config.test_criteria
        self._test_result.client_config = self.config.client_config
        self._test_result.audio_files = self.config.audio_files

        if not self.config.audio_files:
            self._test_result.end_time = datetime.now().isoformat()
            self._test_result.summary = {
                "error": "No audio files provided",
                "max_concurrent_achieved": 0
            }
            self._update_progress(TestProgress(
                current_concurrent=0,
                total_concurrent=self.config.test_criteria.max_concurrent,
                status="failed",
                message="错误: 未提供音频文件",
                percentage=100.0
            ))
            self._running = False
            return self._test_result

        self._resource_monitor = ResourceMonitor(poll_interval_ms=500)
        self._client_manager = ClientManager(self.config.client_config)
        self._latency_measurer = LatencyMeasurer()

        await self._run_concurrent_tests()

        self._test_result.max_concurrent_achieved = self._max_concurrent_achieved
        self._test_result.test_results = self._concurrent_test_results
        self._test_result.end_time = datetime.now().isoformat()
        self._test_result.summary = self._generate_summary()

        self._update_progress(TestProgress(
            current_concurrent=self._max_concurrent_achieved,
            total_concurrent=self.config.test_criteria.max_concurrent,
            status="completed",
            message=f"测试完成！最大并发路数: {self._max_concurrent_achieved}",
            percentage=100.0,
            current_test_stats=self._test_result.summary
        ))

        if self._result_callback:
            self._result_callback(self._test_result)

        self._running = False
        return self._test_result

    async def _run_concurrent_tests(self):
        """运行并发测试"""
        criteria = self.config.test_criteria
        audio_files = self.config.audio_files

        self._update_progress(TestProgress(
            current_concurrent=0,
            total_concurrent=criteria.max_concurrent,
            status="running",
            message=f"开始压力测试: 从1路到{criteria.max_concurrent}路并发",
            percentage=0.0
        ))

        current_concurrent = 1

        while self._running and current_concurrent <= criteria.max_concurrent:
            if self._paused:
                await asyncio.sleep(0.1)
                continue

            self._update_progress(TestProgress(
                current_concurrent=current_concurrent,
                total_concurrent=criteria.max_concurrent,
                status="running",
                message=f"[{current_concurrent}/{criteria.max_concurrent}] 准备 {current_concurrent} 路客户端...",
                percentage=(current_concurrent / criteria.max_concurrent) * 100.0
            ))

            test_result = await self._run_single_concurrent_test(
                current_concurrent,
                audio_files,
                criteria
            )

            self._concurrent_test_results.append(test_result)

            if not test_result.passed:
                self._max_concurrent_achieved = current_concurrent - 1
                self._update_progress(TestProgress(
                    current_concurrent=current_concurrent,
                    total_concurrent=criteria.max_concurrent,
                    status="failed",
                    message=f"测试停止: {test_result.fail_reason}",
                    percentage=100.0
                ))
                break
            else:
                self._max_concurrent_achieved = current_concurrent
                self._update_progress(TestProgress(
                    current_concurrent=current_concurrent,
                    total_concurrent=criteria.max_concurrent,
                    status="running",
                    message=f"[{current_concurrent}/{criteria.max_concurrent}] 测试通过: 延迟={test_result.avg_first_packet_latency_ms:.1f}ms, CPU={test_result.peak_cpu_percent:.1f}%",
                    percentage=(current_concurrent / criteria.max_concurrent) * 100.0,
                    current_test_stats={
                        'avg_first_packet_latency_ms': test_result.avg_first_packet_latency_ms,
                        'max_first_packet_latency_ms': test_result.max_first_packet_latency_ms,
                        'peak_cpu_percent': test_result.peak_cpu_percent,
                        'peak_memory_percent': test_result.peak_memory_percent
                    }
                ))

            current_concurrent += 1
            await asyncio.sleep(1.0)

    async def _run_single_concurrent_test(
        self,
        concurrent_count: int,
        audio_files: List[str],
        criteria: TestCriteria
    ) -> ConcurrentTestResult:
        """
        运行单轮并发测试

        Args:
            concurrent_count: 并发数
            audio_files: 音频文件列表
            criteria: 测试条件

        Returns:
            并发测试结果
        """
        result = ConcurrentTestResult(concurrent_count=concurrent_count)

        try:
            self._resource_monitor.reset()
            self._resource_monitor.update_concurrent_clients(concurrent_count)
            self._resource_monitor.start()

            client_ids = list(range(concurrent_count))

            latency_stats = await self._client_manager.run_clients(
                audio_files=audio_files,
                client_ids=client_ids,
                loop_count=1
            )

            self._resource_monitor.stop()

            result.latency_stats = latency_stats
            result.resource_stats = self._resource_monitor.get_stats()

            self._latency_measurer.reset()
            self._latency_measurer.add_multiple(latency_stats)

            latency_summary = self._latency_measurer.analyze()
            resource_summary = self._resource_monitor.get_summary()

            result.avg_first_packet_latency_ms = latency_summary.avg_first_packet_latency_ms
            result.max_first_packet_latency_ms = latency_summary.max_first_packet_latency_ms
            result.min_first_packet_latency_ms = latency_summary.min_first_packet_latency_ms
            result.success_rate = latency_summary.success_rate

            result.avg_cpu_percent = resource_summary.get('avg_cpu_percent', 0.0)
            result.peak_cpu_percent = resource_summary.get('peak_cpu_percent', 0.0)
            result.avg_memory_percent = resource_summary.get('avg_memory_percent', 0.0)
            result.peak_memory_percent = resource_summary.get('peak_memory_percent', 0.0)

            passed, fail_reason = self._check_test_criteria(
                result,
                criteria,
                latency_summary
            )

            result.passed = passed
            result.fail_reason = fail_reason

        except Exception as e:
            result.passed = False
            result.fail_reason = str(e)
            if self._resource_monitor:
                self._resource_monitor.stop()

        return result

    def _check_test_criteria(
        self,
        result: ConcurrentTestResult,
        criteria: TestCriteria,
        latency_summary: LatencySummary
    ) -> tuple:
        """
        检查测试是否通过

        Returns:
            (是否通过, 失败原因)
        """
        if result.success_rate < 100.0:
            failed_count = len([s for s in result.latency_stats if not s.success])
            return (False, f"部分客户端失败: {failed_count}/{len(result.latency_stats)}")

        if result.max_first_packet_latency_ms >= criteria.max_first_packet_latency_ms:
            return (False, f"首包延迟超过阈值: "
                         f"{result.max_first_packet_latency_ms:.2f}ms >= "
                         f"{criteria.max_first_packet_latency_ms}ms")

        if result.peak_cpu_percent >= criteria.max_cpu_percent:
            return (False, f"CPU使用率超过阈值: "
                         f"{result.peak_cpu_percent:.2f}% >= "
                         f"{criteria.max_cpu_percent}%")

        if result.peak_memory_percent >= criteria.max_memory_percent:
            return (False, f"内存使用率超过阈值: "
                         f"{result.peak_memory_percent:.2f}% >= "
                         f"{criteria.max_memory_percent}%")

        return (True, "")

    def _generate_summary(self) -> Dict[str, Any]:
        """生成测试摘要"""
        summary = {
            "test_id": self._test_result.test_id if self._test_result else "",
            "max_concurrent_achieved": self._max_concurrent_achieved,
            "total_tests_run": len(self._concurrent_test_results),
        }

        if self._concurrent_test_results:
            last_result = self._concurrent_test_results[-1]
            summary["last_test_stats"] = {
                "concurrent_count": last_result.concurrent_count,
                "avg_first_packet_latency_ms": last_result.avg_first_packet_latency_ms,
                "max_first_packet_latency_ms": last_result.max_first_packet_latency_ms,
                "peak_cpu_percent": last_result.peak_cpu_percent,
                "peak_memory_percent": last_result.peak_memory_percent,
                "success_rate": last_result.success_rate,
                "passed": last_result.passed,
                "fail_reason": last_result.fail_reason
            }

        if self._hardware_info:
            summary["hardware"] = self._hardware_info.to_dict()

        return summary

    def stop_test(self):
        """停止测试"""
        self._running = False
        if self._client_manager:
            self._client_manager.stop_all()
        if self._resource_monitor:
            self._resource_monitor.stop()

    def pause_test(self):
        """暂停测试"""
        self._paused = True

    def resume_test(self):
        """继续测试"""
        self._paused = False

    def get_progress(self) -> Optional[TestProgress]:
        """获取当前进度"""
        return self._progress

    def get_result(self) -> Optional[TestResult]:
        """获取测试结果"""
        return self._test_result

    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._running
