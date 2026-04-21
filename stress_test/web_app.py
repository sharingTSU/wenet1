"""
Web应用 - 提供网页界面进行压力测试配置和控制
"""

import asyncio
import json
import os
import threading
from typing import Optional, Dict, Any
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, stream_with_context

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stress_test.config import (
    StressTestConfig, TestCriteria, TestResult,
    ClientConfig, EngineParams, generate_test_id
)
from stress_test.stress_engine import StressTestEngine, TestProgress
from stress_test.report_generator import ReportGenerator
from stress_test.resource_monitor import get_hardware_info


app = Flask(__name__)
app.config['SECRET_KEY'] = 'wenet-stress-test-secret-key-2024'


class StressTestManager:
    """压力测试管理器 - 单例模式管理测试状态"""

    _instance: Optional['StressTestManager'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.config = StressTestConfig()
            self.engine: Optional[StressTestEngine] = None
            self.report_generator = ReportGenerator(self.config.output_dir)
            self.latest_result: Optional[TestResult] = None
            self._test_thread: Optional[threading.Thread] = None
            self._loop: Optional[asyncio.AbstractEventLoop] = None

    def load_config(self, data: Dict[str, Any]):
        """从字典加载配置"""
        self.config = StressTestConfig.from_dict(data)
        self.report_generator = ReportGenerator(self.config.output_dir)

    def get_config_dict(self) -> Dict[str, Any]:
        """获取配置字典"""
        return self.config.to_dict()

    def start_test(self) -> tuple:
        """启动测试"""
        if self.engine and self.engine.is_running():
            return (False, "Test is already running")

        if not self.config.audio_files:
            return (False, "No audio files configured. Please set audio directory first.")

        self.engine = StressTestEngine(self.config)
        self.engine.set_progress_callback(self._on_progress)
        self.engine.set_result_callback(self._on_result)

        def run_async_test():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(self.engine.start_test())
            finally:
                self._loop.close()
                self._loop = None

        self._test_thread = threading.Thread(target=run_async_test, daemon=True)
        self._test_thread.start()

        return (True, "Test started successfully")

    def stop_test(self) -> tuple:
        """停止测试"""
        if self.engine and self.engine.is_running():
            self.engine.stop_test()
            return (True, "Test stopped")
        return (False, "No test running")

    def get_progress(self) -> Optional[TestProgress]:
        """获取当前进度"""
        if self.engine:
            return self.engine.get_progress()
        return None

    def get_result(self) -> Optional[TestResult]:
        """获取测试结果"""
        if self.latest_result:
            return self.latest_result
        if self.engine:
            return self.engine.get_result()
        return None

    def _on_progress(self, progress: TestProgress):
        """进度回调"""
        pass

    def _on_result(self, result: TestResult):
        """结果回调"""
        self.latest_result = result
        self.report_generator.generate_all_reports(result)

    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self.engine is not None and self.engine.is_running()

    def get_hardware_info(self) -> Dict[str, Any]:
        """获取硬件信息"""
        info = get_hardware_info()
        return info.to_dict()

    def scan_audio_files(self, directory: str) -> list:
        """扫描音频目录"""
        files = self.config.load_audio_files(directory)
        return [os.path.basename(f) for f in files]


manager = StressTestManager()


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    """获取配置"""
    config = manager.get_config_dict()
    hardware = manager.get_hardware_info()
    return jsonify({
        'config': config,
        'hardware': hardware
    })


@app.route('/api/config', methods=['POST'])
def update_config():
    """更新配置"""
    try:
        data = request.get_json()
        manager.load_config(data)
        return jsonify({'success': True, 'message': 'Configuration updated'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/api/audio/scan', methods=['POST'])
def scan_audio():
    """扫描音频文件"""
    try:
        data = request.get_json()
        directory = data.get('directory', '')

        if not directory or not os.path.exists(directory):
            return jsonify({
                'success': False,
                'message': 'Invalid directory'
            }), 400

        files = manager.scan_audio_files(directory)
        return jsonify({
            'success': True,
            'files': files,
            'count': len(files),
            'directory': directory
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/test/start', methods=['POST'])
def start_test():
    """启动测试"""
    success, message = manager.start_test()
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': message}), 400


@app.route('/api/test/stop', methods=['POST'])
def stop_test():
    """停止测试"""
    success, message = manager.stop_test()
    return jsonify({'success': success, 'message': message})


@app.route('/api/test/status', methods=['GET'])
def get_status():
    """获取测试状态"""
    progress = manager.get_progress()
    is_running = manager.is_running()

    status_data = {
        'is_running': is_running,
        'progress': None
    }

    if progress:
        status_data['progress'] = progress.to_dict()

    return jsonify(status_data)


@app.route('/api/test/result', methods=['GET'])
def get_result():
    """获取测试结果"""
    result = manager.get_result()

    if result is None:
        return jsonify({'success': False, 'message': 'No test result available'})

    return jsonify({
        'success': True,
        'result': result.to_dict()
    })


@app.route('/api/test/stream')
def stream_status():
    """流式获取测试状态"""
    def generate():
        last_progress = None
        while True:
            progress = manager.get_progress()
            is_running = manager.is_running()

            if progress != last_progress:
                data = {
                    'is_running': is_running,
                    'progress': progress.to_dict() if progress else None,
                    'timestamp': datetime.now().isoformat()
                }
                yield f"data: {json.dumps(data)}\n\n"
                last_progress = progress

            if not is_running and last_progress and last_progress.status in ['completed', 'failed']:
                break

            import time
            time.sleep(0.5)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/api/hardware', methods=['GET'])
def get_hardware():
    """获取硬件信息"""
    info = manager.get_hardware_info()
    return jsonify({'success': True, 'hardware': info})


@app.route('/api/reports', methods=['GET'])
def list_reports():
    """列出所有报告"""
    output_dir = manager.config.output_dir
    if not os.path.exists(output_dir):
        return jsonify({'success': True, 'reports': []})

    reports = []
    for filename in os.listdir(output_dir):
        if filename.endswith('.json') or filename.endswith('.html'):
            filepath = os.path.join(output_dir, filename)
            stat = os.stat(filepath)
            reports.append({
                'filename': filename,
                'type': 'json' if filename.endswith('.json') else 'html',
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })

    reports.sort(key=lambda x: x['modified'], reverse=True)
    return jsonify({'success': True, 'reports': reports})


def create_default_config():
    """创建默认配置"""
    config = StressTestConfig()

    audio_dir = os.path.join(os.path.dirname(__file__), '..', 'test', 'resources')
    if os.path.exists(audio_dir):
        config.load_audio_files(audio_dir)

    return config


def run_server(host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
    """运行服务器"""
    manager.config = create_default_config()
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    run_server(port=5000, debug=True)
