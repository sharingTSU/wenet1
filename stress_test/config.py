"""
压力测试配置模块 - 定义所有配置参数和数据结构
"""

import os
import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class TestCriteria:
    """测试停止条件"""
    max_concurrent: int = 100
    max_first_packet_latency_ms: float = 200.0
    max_cpu_percent: float = 90.0
    max_memory_percent: float = 95.0
    test_duration_per_concurrent: int = 30

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ClientConfig:
    """客户端配置"""
    server_url: str = "ws://127.0.0.1:10086"
    sample_rate: int = 16000
    chunk_duration_ms: float = 500.0
    nbest: int = 1
    continuous_decoding: bool = False
    ping_timeout: int = 300

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EngineParams:
    """引擎参数"""
    model_name: str = "unknown"
    model_size: str = "unknown"
    chunk_size: int = 16
    num_left_chunks: int = -1
    feature_type: str = "kaldi"
    num_bins: int = 80

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HardwareInfo:
    """硬件配置信息"""
    cpu_model: str = "unknown"
    cpu_cores: int = 0
    cpu_threads: int = 0
    total_memory_gb: float = 0.0
    os_name: str = "unknown"
    os_version: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LatencyStats:
    """延迟统计数据"""
    client_id: int = 0
    first_packet_latency_ms: float = 0.0
    connect_time_ms: float = 0.0
    total_duration_ms: float = 0.0
    partial_results_count: int = 0
    final_results_count: int = 0
    success: bool = True
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResourceStats:
    """资源使用统计"""
    timestamp: str = ""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_gb: float = 0.0
    concurrent_clients: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConcurrentTestResult:
    """单轮并发测试结果"""
    concurrent_count: int = 0
    latency_stats: List[LatencyStats] = field(default_factory=list)
    resource_stats: List[ResourceStats] = field(default_factory=list)
    avg_first_packet_latency_ms: float = 0.0
    max_first_packet_latency_ms: float = 0.0
    min_first_packet_latency_ms: float = 0.0
    avg_cpu_percent: float = 0.0
    peak_cpu_percent: float = 0.0
    avg_memory_percent: float = 0.0
    peak_memory_percent: float = 0.0
    success_rate: float = 100.0
    passed: bool = True
    fail_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "concurrent_count": self.concurrent_count,
            "latency_stats": [s.to_dict() for s in self.latency_stats],
            "resource_stats": [s.to_dict() for s in self.resource_stats],
            "avg_first_packet_latency_ms": self.avg_first_packet_latency_ms,
            "max_first_packet_latency_ms": self.max_first_packet_latency_ms,
            "min_first_packet_latency_ms": self.min_first_packet_latency_ms,
            "avg_cpu_percent": self.avg_cpu_percent,
            "peak_cpu_percent": self.peak_cpu_percent,
            "avg_memory_percent": self.avg_memory_percent,
            "peak_memory_percent": self.peak_memory_percent,
            "success_rate": self.success_rate,
            "passed": self.passed,
            "fail_reason": self.fail_reason
        }


@dataclass
class TestResult:
    """完整测试结果"""
    test_id: str = ""
    start_time: str = ""
    end_time: str = ""
    hardware_info: HardwareInfo = field(default_factory=HardwareInfo)
    engine_params: EngineParams = field(default_factory=EngineParams)
    test_criteria: TestCriteria = field(default_factory=TestCriteria)
    client_config: ClientConfig = field(default_factory=ClientConfig)
    max_concurrent_achieved: int = 0
    test_results: List[ConcurrentTestResult] = field(default_factory=list)
    audio_files: List[str] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "hardware_info": self.hardware_info.to_dict(),
            "engine_params": self.engine_params.to_dict(),
            "test_criteria": self.test_criteria.to_dict(),
            "client_config": self.client_config.to_dict(),
            "max_concurrent_achieved": self.max_concurrent_achieved,
            "test_results": [r.to_dict() for r in self.test_results],
            "audio_files": self.audio_files,
            "summary": self.summary
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


@dataclass
class TestProgress:
    """测试进度信息"""
    current_concurrent: int = 0
    total_concurrent: int = 0
    status: str = "idle"
    message: str = ""
    percentage: float = 0.0
    current_test_stats: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_concurrent": self.current_concurrent,
            "total_concurrent": self.total_concurrent,
            "status": self.status,
            "message": self.message,
            "percentage": self.percentage,
            "current_test_stats": self.current_test_stats
        }


class StressTestConfig:
    """压力测试配置管理器"""

    def __init__(self):
        self.test_criteria = TestCriteria()
        self.client_config = ClientConfig()
        self.engine_params = EngineParams()
        self.audio_dir: str = ""
        self.audio_files: List[str] = []
        self.output_dir: str = "./stress_test_results"
        self.web_port: int = 5000
        self.web_host: str = "0.0.0.0"

    def load_audio_files(self, audio_dir: str) -> List[str]:
        """加载音频目录中的所有音频文件"""
        self.audio_dir = os.path.abspath(audio_dir) if audio_dir else ""
        self.audio_files = []
        self._all_files_in_dir = []
        self._audio_extensions = ('.wav', '.pcm', '.mp3', '.flac', '.ogg', '.m4a', '.aac', '.wma')

        if not audio_dir:
            return self.audio_files

        abs_audio_dir = os.path.abspath(audio_dir)

        if not os.path.exists(abs_audio_dir):
            return self.audio_files

        if not os.path.isdir(abs_audio_dir):
            return self.audio_files

        try:
            all_entries = os.listdir(abs_audio_dir)
            for entry in all_entries:
                full_path = os.path.join(abs_audio_dir, entry)
                if os.path.isfile(full_path):
                    self._all_files_in_dir.append(entry)
                    if entry.lower().endswith(self._audio_extensions):
                        self.audio_files.append(full_path)
        except Exception as e:
            print(f"Error scanning directory {abs_audio_dir}: {e}")
            pass

        return self.audio_files

    def get_all_files_in_dir(self) -> List[str]:
        """获取目录中的所有文件"""
        return getattr(self, '_all_files_in_dir', [])

    def get_audio_extensions(self) -> tuple:
        """获取支持的音频扩展名"""
        return getattr(self, '_audio_extensions', ('.wav', '.pcm'))

    def get_audio_file(self, index: int) -> Optional[str]:
        """根据索引获取音频文件（循环使用）"""
        if not self.audio_files:
            return None
        return self.audio_files[index % len(self.audio_files)]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_criteria": self.test_criteria.to_dict(),
            "client_config": self.client_config.to_dict(),
            "engine_params": self.engine_params.to_dict(),
            "audio_dir": self.audio_dir,
            "audio_files": self.audio_files,
            "output_dir": self.output_dir,
            "web_port": self.web_port,
            "web_host": self.web_host
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StressTestConfig':
        config = cls()

        if 'test_criteria' in data:
            tc = data['test_criteria']
            config.test_criteria = TestCriteria(
                max_concurrent=tc.get('max_concurrent', 100),
                max_first_packet_latency_ms=tc.get('max_first_packet_latency_ms', 200.0),
                max_cpu_percent=tc.get('max_cpu_percent', 90.0),
                max_memory_percent=tc.get('max_memory_percent', 95.0),
                test_duration_per_concurrent=tc.get('test_duration_per_concurrent', 30)
            )

        if 'client_config' in data:
            cc = data['client_config']
            config.client_config = ClientConfig(
                server_url=cc.get('server_url', "ws://127.0.0.1:10086"),
                sample_rate=cc.get('sample_rate', 16000),
                chunk_duration_ms=cc.get('chunk_duration_ms', 500.0),
                nbest=cc.get('nbest', 1),
                continuous_decoding=cc.get('continuous_decoding', False),
                ping_timeout=cc.get('ping_timeout', 300)
            )

        if 'engine_params' in data:
            ep = data['engine_params']
            config.engine_params = EngineParams(
                model_name=ep.get('model_name', "unknown"),
                model_size=ep.get('model_size', "unknown"),
                chunk_size=ep.get('chunk_size', 16),
                num_left_chunks=ep.get('num_left_chunks', -1),
                feature_type=ep.get('feature_type', "kaldi"),
                num_bins=ep.get('num_bins', 80)
            )

        if 'audio_dir' in data:
            audio_dir = data['audio_dir']
            if 'audio_files' in data and data['audio_files']:
                config.audio_dir = audio_dir
                config.audio_files = data['audio_files']
            elif audio_dir:
                config.load_audio_files(audio_dir)
        if 'output_dir' in data:
            config.output_dir = data['output_dir']
        if 'web_port' in data:
            config.web_port = data['web_port']
        if 'web_host' in data:
            config.web_host = data['web_host']

        return config

    def save_json(self, filepath: str):
        """保存配置到JSON文件"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_json(cls, filepath: str) -> 'StressTestConfig':
        """从JSON文件加载配置"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


def generate_test_id() -> str:
    """生成唯一的测试ID"""
    return f"stress_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
