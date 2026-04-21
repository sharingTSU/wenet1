"""
WebSocket流式客户端 - 模拟实时语音流解码请求
"""

import asyncio
import json
import os
import time
import struct
import wave
from dataclasses import dataclass, field
from typing import Optional, List, Callable, Any
from datetime import datetime

try:
    import websockets
    from websockets.asyncio.client import connect as ws_connect
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False

from config import LatencyStats, ClientConfig


WS_START = json.dumps({
    'signal': 'start',
    'nbest': 1,
    'continuous_decoding': False,
})

WS_END = json.dumps({'signal': 'end'})


@dataclass
class AudioChunk:
    """音频数据块"""
    data: bytes
    samples: int
    duration_ms: float


class AudioStreamer:
    """音频流处理器 - 支持WAV文件的流式读取"""

    def __init__(self, filepath: str, sample_rate: int = 16000):
        """
        初始化音频流处理器

        Args:
            filepath: 音频文件路径
            sample_rate: 采样率
        """
        self.filepath = filepath
        self.sample_rate = sample_rate
        self._audio_data: Optional[bytes] = None
        self._num_samples: int = 0
        self._load_audio()

    def _load_audio(self):
        """加载音频文件"""
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Audio file not found: {self.filepath}")

        if self.filepath.lower().endswith('.wav'):
            self._load_wav()
        elif self.filepath.lower().endswith('.pcm'):
            self._load_pcm()
        elif SOUNDFILE_AVAILABLE:
            self._load_soundfile()
        else:
            raise ValueError(f"Unsupported audio format: {self.filepath}")

    def _load_wav(self):
        """加载WAV文件"""
        with wave.open(self.filepath, 'rb') as wav:
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            num_channels = wav.getnchannels()

            if sample_rate != self.sample_rate:
                raise ValueError(f"Sample rate mismatch: expected {self.sample_rate}, got {sample_rate}")
            if sample_width != 2:
                raise ValueError(f"Only 16-bit audio supported, got {sample_width * 8}-bit")
            if num_channels != 1:
                raise ValueError(f"Only mono audio supported, got {num_channels} channels")

            self._audio_data = wav.readframes(wav.getnframes())
            self._num_samples = wav.getnframes()

    def _load_pcm(self):
        """加载PCM原始数据"""
        with open(self.filepath, 'rb') as f:
            self._audio_data = f.read()
        self._num_samples = len(self._audio_data) // 2

    def _load_soundfile(self):
        """使用soundfile加载音频"""
        data, sr = sf.read(self.filepath, dtype='int16')

        if sr != self.sample_rate:
            raise ValueError(f"Sample rate mismatch: expected {self.sample_rate}, got {sr}")

        if len(data.shape) > 1:
            data = data[:, 0]

        self._audio_data = data.tobytes()
        self._num_samples = len(data)

    def get_chunks(self, chunk_duration_ms: float = 500.0) -> List[AudioChunk]:
        """
        将音频分割成指定时长的块

        Args:
            chunk_duration_ms: 每个块的时长（毫秒）

        Returns:
            音频块列表
        """
        if self._audio_data is None:
            return []

        samples_per_chunk = int(chunk_duration_ms * self.sample_rate / 1000.0)
        bytes_per_sample = 2
        bytes_per_chunk = samples_per_chunk * bytes_per_sample

        chunks: List[AudioChunk] = []
        total_bytes = len(self._audio_data)

        for offset in range(0, total_bytes, bytes_per_chunk):
            end = min(offset + bytes_per_chunk, total_bytes)
            chunk_data = self._audio_data[offset:end]
            num_samples = len(chunk_data) // bytes_per_sample
            duration_ms = (num_samples / self.sample_rate) * 1000.0

            chunks.append(AudioChunk(
                data=chunk_data,
                samples=num_samples,
                duration_ms=duration_ms
            ))

        return chunks

    @property
    def duration_ms(self) -> float:
        """音频总时长（毫秒）"""
        return (self._num_samples / self.sample_rate) * 1000.0

    @property
    def num_samples(self) -> int:
        """采样点数量"""
        return self._num_samples

    @property
    def audio_bytes(self) -> Optional[bytes]:
        """原始音频数据"""
        return self._audio_data


class WebSocketStreamingClient:
    """WebSocket流式语音识别客户端"""

    def __init__(
        self,
        client_id: int,
        config: ClientConfig,
        audio_file: str,
        loop_count: int = 1,
        on_result: Optional[Callable[[int, dict], None]] = None,
        on_error: Optional[Callable[[int, str], None]] = None
    ):
        """
        初始化客户端

        Args:
            client_id: 客户端ID
            config: 客户端配置
            audio_file: 音频文件路径
            loop_count: 循环播放次数（0表示无限循环）
            on_result: 结果回调函数
            on_error: 错误回调函数
        """
        self.client_id = client_id
        self.config = config
        self.audio_file = audio_file
        self.loop_count = loop_count
        self.on_result = on_result
        self.on_error = on_error

        self.stats = LatencyStats(client_id=client_id)
        self._running = False
        self._connected = False
        self._ws: Optional[Any] = None
        self._first_packet_received = False
        self._start_send_time: float = 0.0
        self._connect_time: float = 0.0

        if not WEBSOCKETS_AVAILABLE:
            raise RuntimeError("websockets library is required. "
                            "Please install it with: pip install websockets")

    async def run(self) -> LatencyStats:
        """运行客户端"""
        self._running = True
        self.stats.success = True

        try:
            audio_streamer = AudioStreamer(self.audio_file, self.config.sample_rate)
            chunks = audio_streamer.get_chunks(self.config.chunk_duration_ms)

            if not chunks:
                self.stats.success = False
                self.stats.error_message = "No audio chunks to send"
                return self.stats

            connect_start = time.perf_counter()

            self._ws = await ws_connect(
                self.config.server_url,
                ping_timeout=self.config.ping_timeout,
                close_timeout=10
            )
            self._connect_time = (time.perf_counter() - connect_start) * 1000
            self.stats.connect_time_ms = self._connect_time
            self._connected = True

            await self._send_start()

            loop_idx = 0
            while self._running and (self.loop_count == 0 or loop_idx < self.loop_count):
                for chunk in chunks:
                    if not self._running:
                        break

                    await self._send_audio_chunk(chunk)

                    sleep_duration = chunk.duration_ms / 1000.0
                    await asyncio.sleep(sleep_duration)

                loop_idx += 1

            await self._send_end()

            total_end = time.perf_counter()
            self.stats.total_duration_ms = (total_end - connect_start) * 1000

        except Exception as e:
            self.stats.success = False
            self.stats.error_message = str(e)
            if self.on_error:
                self.on_error(self.client_id, str(e))

        finally:
            if self._ws:
                try:
                    await self._ws.close()
                except Exception:
                    pass
            self._connected = False
            self._running = False

        return self.stats

    async def _send_start(self):
        """发送开始信号"""
        start_msg = json.dumps({
            'signal': 'start',
            'nbest': self.config.nbest,
            'continuous_decoding': self.config.continuous_decoding,
        })

        await self._ws.send(start_msg)

        response = await self._ws.recv()
        response_data = json.loads(response)

        self._start_send_time = time.perf_counter()

    async def _send_audio_chunk(self, chunk: AudioChunk):
        """发送音频数据块"""
        if self._ws and self._connected:
            await self._ws.send(chunk.data)

            try:
                while True:
                    response = await asyncio.wait_for(
                        self._ws.recv(),
                        timeout=0.01
                    )
                    await self._handle_response(response)
            except asyncio.TimeoutError:
                pass

    async def _send_end(self):
        """发送结束信号"""
        if self._ws and self._connected:
            await self._ws.send(json.dumps({'signal': 'end'}))

            try:
                while True:
                    response = await asyncio.wait_for(
                        self._ws.recv(),
                        timeout=5.0
                    )
                    await self._handle_response(response)
            except asyncio.TimeoutError:
                pass

    async def _handle_response(self, response: str):
        """处理服务器响应"""
        try:
            data = json.loads(response)

            if data.get('status') != 'ok':
                error_msg = data.get('message', 'Unknown error')
                self.stats.success = False
                self.stats.error_message = error_msg
                if self.on_error:
                    self.on_error(self.client_id, error_msg)
                return

            msg_type = data.get('type', '')

            if not self._first_packet_received and msg_type in ['partial_result', 'final_result']:
                self._first_packet_received = True
                first_packet_time = time.perf_counter()
                self.stats.first_packet_latency_ms = (first_packet_time - self._start_send_time) * 1000

            if msg_type == 'partial_result':
                self.stats.partial_results_count += 1
                if self.on_result:
                    self.on_result(self.client_id, {
                        'type': 'partial',
                        'data': data.get('nbest', '')
                    })

            elif msg_type == 'final_result':
                self.stats.final_results_count += 1
                if self.on_result:
                    self.on_result(self.client_id, {
                        'type': 'final',
                        'data': data.get('nbest', '')
                    })

            elif msg_type == 'speech_end':
                pass

        except json.JSONDecodeError:
            pass

    def stop(self):
        """停止客户端"""
        self._running = False


class ClientManager:
    """客户端管理器 - 管理多个并发客户端"""

    def __init__(self, config: ClientConfig):
        """
        初始化客户端管理器

        Args:
            config: 客户端配置
        """
        self.config = config
        self._clients: List[WebSocketStreamingClient] = []
        self._results: List[LatencyStats] = []
        self._lock = asyncio.Lock()

    async def run_clients(
        self,
        audio_files: List[str],
        client_ids: List[int],
        loop_count: int = 1,
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> List[LatencyStats]:
        """
        运行多个并发客户端

        Args:
            audio_files: 音频文件列表
            client_ids: 客户端ID列表
            loop_count: 循环次数
            on_progress: 进度回调

        Returns:
            各客户端的延迟统计
        """
        self._clients = []
        self._results = []

        tasks = []
        for idx, client_id in enumerate(client_ids):
            audio_file = audio_files[idx % len(audio_files)]

            client = WebSocketStreamingClient(
                client_id=client_id,
                config=self.config,
                audio_file=audio_file,
                loop_count=loop_count
            )

            self._clients.append(client)
            task = client.run()
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        final_results: List[LatencyStats] = []
        for result in results:
            if isinstance(result, LatencyStats):
                final_results.append(result)
            else:
                stats = LatencyStats()
                stats.success = False
                stats.error_message = str(result)
                final_results.append(stats)

        self._results = final_results
        return final_results

    def stop_all(self):
        """停止所有客户端"""
        for client in self._clients:
            client.stop()

    def get_results(self) -> List[LatencyStats]:
        """获取所有结果"""
        return self._results
