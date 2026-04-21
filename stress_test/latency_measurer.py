"""
延迟测量模块 - 测量和分析首包延迟及各阶段时间
"""

import statistics
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from stress_test.config import LatencyStats


@dataclass
class LatencySummary:
    """延迟统计摘要"""
    count: int = 0
    success_count: int = 0
    success_rate: float = 0.0

    avg_first_packet_latency_ms: float = 0.0
    median_first_packet_latency_ms: float = 0.0
    max_first_packet_latency_ms: float = 0.0
    min_first_packet_latency_ms: float = 0.0
    p95_first_packet_latency_ms: float = 0.0
    p99_first_packet_latency_ms: float = 0.0

    avg_connect_time_ms: float = 0.0
    avg_total_duration_ms: float = 0.0

    all_latencies: List[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "count": self.count,
            "success_count": self.success_count,
            "success_rate": self.success_rate,
            "avg_first_packet_latency_ms": self.avg_first_packet_latency_ms,
            "median_first_packet_latency_ms": self.median_first_packet_latency_ms,
            "max_first_packet_latency_ms": self.max_first_packet_latency_ms,
            "min_first_packet_latency_ms": self.min_first_packet_latency_ms,
            "p95_first_packet_latency_ms": self.p95_first_packet_latency_ms,
            "p99_first_packet_latency_ms": self.p99_first_packet_latency_ms,
            "avg_connect_time_ms": self.avg_connect_time_ms,
            "avg_total_duration_ms": self.avg_total_duration_ms
        }


class LatencyMeasurer:
    """延迟测量器 - 收集和分析延迟数据"""

    def __init__(self):
        """初始化延迟测量器"""
        self._stats: List[LatencyStats] = []

    def add_stats(self, stats: LatencyStats):
        """添加延迟统计数据"""
        self._stats.append(stats)

    def add_multiple(self, stats_list: List[LatencyStats]):
        """添加多个延迟统计数据"""
        self._stats.extend(stats_list)

    def get_all_stats(self) -> List[LatencyStats]:
        """获取所有统计数据"""
        return list(self._stats)

    def get_success_stats(self) -> List[LatencyStats]:
        """获取成功的统计数据"""
        return [s for s in self._stats if s.success]

    def get_failed_stats(self) -> List[LatencyStats]:
        """获取失败的统计数据"""
        return [s for s in self._stats if not s.success]

    def analyze(self) -> LatencySummary:
        """分析延迟数据"""
        summary = LatencySummary()
        summary.count = len(self._stats)

        success_stats = self.get_success_stats()
        summary.success_count = len(success_stats)

        if summary.count > 0:
            summary.success_rate = (summary.success_count / summary.count) * 100.0
        else:
            summary.success_rate = 0.0

        if not success_stats:
            return summary

        first_packet_latencies = [s.first_packet_latency_ms for s in success_stats]
        connect_times = [s.connect_time_ms for s in success_stats]
        total_durations = [s.total_duration_ms for s in success_stats]

        summary.all_latencies = first_packet_latencies
        summary.avg_first_packet_latency_ms = statistics.mean(first_packet_latencies)
        summary.median_first_packet_latency_ms = statistics.median(first_packet_latencies)
        summary.max_first_packet_latency_ms = max(first_packet_latencies)
        summary.min_first_packet_latency_ms = min(first_packet_latencies)
        summary.p95_first_packet_latency_ms = self._calculate_percentile(first_packet_latencies, 95)
        summary.p99_first_packet_latency_ms = self._calculate_percentile(first_packet_latencies, 99)

        summary.avg_connect_time_ms = statistics.mean(connect_times)
        summary.avg_total_duration_ms = statistics.mean(total_durations)

        return summary

    def _calculate_percentile(self, data: List[float], percentile: int) -> float:
        """
        计算百分位数

        Args:
            data: 数据列表
            percentile: 百分位 (0-100)

        Returns:
            百分位数的值
        """
        if not data:
            return 0.0

        sorted_data = sorted(data)
        n = len(sorted_data)

        if n == 0:
            return 0.0
        if n == 1:
            return sorted_data[0]

        index = (percentile / 100.0) * (n - 1)
        floor = int(index)
        ceil = floor + 1
        fraction = index - floor

        if floor >= n - 1:
            return sorted_data[-1]

        result = sorted_data[floor] + fraction * (sorted_data[ceil] - sorted_data[floor])
        return result

    def get_latency_distribution(self, bucket_size_ms: float = 50.0) -> Dict[str, int]:
        """
        获取延迟分布

        Args:
            bucket_size_ms: 每个桶的大小（毫秒）

        Returns:
            延迟分布字典，键为桶范围，值为计数
        """
        success_stats = self.get_success_stats()
        if not success_stats:
            return {}

        latencies = [s.first_packet_latency_ms for s in success_stats]

        distribution: Dict[str, int] = {}
        for latency in latencies:
            bucket_start = int(latency // bucket_size_ms) * bucket_size_ms
            bucket_end = bucket_start + bucket_size_ms
            bucket_key = f"{bucket_start}-{bucket_end}ms"
            distribution[bucket_key] = distribution.get(bucket_key, 0) + 1

        return dict(sorted(distribution.items(),
                         key=lambda x: float(x[0].split('-')[0])))

    def check_threshold(self, max_latency_ms: float) -> tuple:
        """
        检查是否超过阈值

        Args:
            max_latency_ms: 最大允许延迟（毫秒）

        Returns:
            (是否通过, 超过阈值的数量, 最大延迟)
        """
        success_stats = self.get_success_stats()

        if not success_stats:
            return (len(self._stats) == 0 or all(not s.success for s in self._stats), 0, 0.0)

        latencies = [s.first_packet_latency_ms for s in success_stats]
        max_latency = max(latencies)
        over_threshold = sum(1 for l in latencies if l >= max_latency_ms)

        passed = over_threshold == 0
        return (passed, over_threshold, max_latency)

    def reset(self):
        """重置所有统计数据"""
        self._stats.clear()


def aggregate_latency_stats(stats_list: List[LatencyStats]) -> LatencySummary:
    """
    聚合延迟统计数据

    Args:
        stats_list: 延迟统计列表

    Returns:
        聚合后的延迟摘要
    """
    measurer = LatencyMeasurer()
    measurer.add_multiple(stats_list)
    return measurer.analyze()
