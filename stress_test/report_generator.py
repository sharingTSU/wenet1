"""
报告生成模块 - 生成HTML/JSON测试报告
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime

from stress_test.config import TestResult, ConcurrentTestResult


class ReportGenerator:
    """报告生成器"""

    def __init__(self, output_dir: str = "./stress_test_results"):
        """
        初始化报告生成器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_json_report(self, result: TestResult, filename: Optional[str] = None) -> str:
        """
        生成JSON报告

        Args:
            result: 测试结果
            filename: 文件名（可选）

        Returns:
            生成的文件路径
        """
        if filename is None:
            filename = f"{result.test_id}.json"

        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)

        return filepath

    def generate_html_report(self, result: TestResult, filename: Optional[str] = None) -> str:
        """
        生成HTML报告

        Args:
            result: 测试结果
            filename: 文件名（可选）

        Returns:
            生成的文件路径
        """
        if filename is None:
            filename = f"{result.test_id}.html"

        filepath = os.path.join(self.output_dir, filename)

        html_content = self._build_html_report(result)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return filepath

    def _build_html_report(self, result: TestResult) -> str:
        """构建HTML报告内容"""
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>压力测试报告 - {result.test_id}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(90deg, #4a5568 0%, #2d3748 100%);
            color: white;
            padding: 30px 40px;
        }}
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        .header .meta {{
            color: #a0aec0;
            font-size: 14px;
        }}
        .section {{
            padding: 30px 40px;
            border-bottom: 1px solid #e2e8f0;
        }}
        .section:last-child {{ border-bottom: none; }}
        .section-title {{
            font-size: 20px;
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .section-title .icon {{
            width: 8px;
            height: 24px;
            background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
            border-radius: 4px;
        }}
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 24px;
            border-radius: 12px;
            text-align: center;
        }}
        .card.green {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }}
        .card.orange {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }}
        .card.blue {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }}
        .card .value {{
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 5px;
        }}
        .card .label {{
            font-size: 14px;
            opacity: 0.9;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        .info-box {{
            background: #f7fafc;
            padding: 20px;
            border-radius: 12px;
        }}
        .info-box h3 {{
            font-size: 16px;
            color: #4a5568;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e2e8f0;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #e2e8f0;
        }}
        .info-row:last-child {{ border-bottom: none; }}
        .info-row .key {{ color: #718096; font-size: 14px; }}
        .info-row .value {{ color: #2d3748; font-weight: 500; font-size: 14px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }}
        th {{
            background: #f7fafc;
            font-weight: 600;
            color: #4a5568;
            font-size: 13px;
            text-transform: uppercase;
        }}
        td {{ color: #2d3748; font-size: 14px; }}
        tr:hover {{ background: #f7fafc; }}
        .status-pass {{ color: #38a169; font-weight: 600; }}
        .status-fail {{ color: #e53e3e; font-weight: 600; }}
        .highlight {{
            background: linear-gradient(90deg, #fff3cd 0%, #ffeaa7 100%);
            padding: 20px;
            border-radius: 12px;
            border-left: 4px solid #f0ad4e;
        }}
        .highlight h3 {{ color: #856404; margin-bottom: 10px; }}
        .highlight p {{ color: #856404; font-size: 14px; }}
        .footer {{
            background: #f7fafc;
            padding: 20px 40px;
            text-align: center;
            color: #718096;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 语音识别服务压力测试报告</h1>
            <div class="meta">
                测试ID: {result.test_id} | 开始时间: {result.start_time} | 结束时间: {result.end_time}
            </div>
        </div>

        <div class="section">
            <div class="section-title">
                <div class="icon"></div>
                测试摘要
            </div>
            <div class="summary-cards">
                <div class="card green">
                    <div class="value">{result.max_concurrent_achieved}</div>
                    <div class="label">最大并发路数</div>
                </div>
                <div class="card blue">
                    <div class="value">{len(result.test_results)}</div>
                    <div class="label">已完成测试轮数</div>
                </div>
                {self._get_cards_html(result)}
            </div>
        </div>

        <div class="section">
            <div class="section-title">
                <div class="icon"></div>
                硬件配置
            </div>
            <div class="info-grid">
                <div class="info-box">
                    <h3>CPU 信息</h3>
                    <div class="info-row">
                        <span class="key">型号</span>
                        <span class="value">{result.hardware_info.cpu_model}</span>
                    </div>
                    <div class="info-row">
                        <span class="key">物理核心数</span>
                        <span class="value">{result.hardware_info.cpu_cores}</span>
                    </div>
                    <div class="info-row">
                        <span class="key">逻辑核心数</span>
                        <span class="value">{result.hardware_info.cpu_threads}</span>
                    </div>
                </div>
                <div class="info-box">
                    <h3>内存与系统</h3>
                    <div class="info-row">
                        <span class="key">总内存</span>
                        <span class="value">{result.hardware_info.total_memory_gb:.2f} GB</span>
                    </div>
                    <div class="info-row">
                        <span class="key">操作系统</span>
                        <span class="value">{result.hardware_info.os_name} {result.hardware_info.os_version}</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">
                <div class="icon"></div>
                引擎参数
            </div>
            <div class="info-grid">
                <div class="info-box">
                    <h3>模型配置</h3>
                    <div class="info-row">
                        <span class="key">模型名称</span>
                        <span class="value">{result.engine_params.model_name}</span>
                    </div>
                    <div class="info-row">
                        <span class="key">模型大小</span>
                        <span class="value">{result.engine_params.model_size}</span>
                    </div>
                    <div class="info-row">
                        <span class="key">Chunk Size</span>
                        <span class="value">{result.engine_params.chunk_size}</span>
                    </div>
                    <div class="info-row">
                        <span class="key">Left Chunks</span>
                        <span class="value">{result.engine_params.num_left_chunks}</span>
                    </div>
                </div>
                <div class="info-box">
                    <h3>特征配置</h3>
                    <div class="info-row">
                        <span class="key">特征类型</span>
                        <span class="value">{result.engine_params.feature_type}</span>
                    </div>
                    <div class="info-row">
                        <span class="key">Mel Bin 数</span>
                        <span class="value">{result.engine_params.num_bins}</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">
                <div class="icon"></div>
                测试条件
            </div>
            <div class="info-grid">
                <div class="info-box">
                    <h3>停止阈值</h3>
                    <div class="info-row">
                        <span class="key">最大并发路数</span>
                        <span class="value">{result.test_criteria.max_concurrent}</span>
                    </div>
                    <div class="info-row">
                        <span class="key">最大首包延迟</span>
                        <span class="value">{result.test_criteria.max_first_packet_latency_ms} ms</span>
                    </div>
                    <div class="info-row">
                        <span class="key">最大CPU使用率</span>
                        <span class="value">{result.test_criteria.max_cpu_percent}%</span>
                    </div>
                    <div class="info-row">
                        <span class="key">最大内存使用率</span>
                        <span class="value">{result.test_criteria.max_memory_percent}%</span>
                    </div>
                </div>
                <div class="info-box">
                    <h3>客户端配置</h3>
                    <div class="info-row">
                        <span class="key">服务器地址</span>
                        <span class="value">{result.client_config.server_url}</span>
                    </div>
                    <div class="info-row">
                        <span class="key">采样率</span>
                        <span class="value">{result.client_config.sample_rate} Hz</span>
                    </div>
                    <div class="info-row">
                        <span class="key">Chunk 时长</span>
                        <span class="value">{result.client_config.chunk_duration_ms} ms</span>
                    </div>
                    <div class="info-row">
                        <span class="key">音频文件数</span>
                        <span class="value">{len(result.audio_files)}</span>
                    </div>
                </div>
            </div>
        </div>

        {self._get_fail_reason_html(result)}

        <div class="section">
            <div class="section-title">
                <div class="icon"></div>
                各轮测试详细数据
            </div>
            <table>
                <thead>
                    <tr>
                        <th>并发数</th>
                        <th>平均首包延迟 (ms)</th>
                        <th>最大首包延迟 (ms)</th>
                        <th>最小首包延迟 (ms)</th>
                        <th>平均CPU (%)</th>
                        <th>峰值CPU (%)</th>
                        <th>平均内存 (%)</th>
                        <th>峰值内存 (%)</th>
                        <th>成功率</th>
                        <th>状态</th>
                    </tr>
                </thead>
                <tbody>
                    {self._get_test_results_table(result)}
                </tbody>
            </table>
        </div>

        {self._get_latency_detail_table(result)}

        <div class="footer">
            报告生成时间: {datetime.now().isoformat()} | WeNet 压力测试系统 v1.0
        </div>
    </div>
</body>
</html>
"""
        return html

    def _get_cards_html(self, result: TestResult) -> str:
        """获取卡片HTML"""
        if not result.test_results:
            return ""

        last_result = result.test_results[-1]
        cards = f"""
                <div class="card orange">
                    <div class="value">{last_result.avg_first_packet_latency_ms:.2f}</div>
                    <div class="label">平均首包延迟 (ms)</div>
                </div>
                <div class="card">
                    <div class="value">{last_result.peak_cpu_percent:.1f}%</div>
                    <div class="label">峰值CPU使用率</div>
                </div>
        """
        return cards

    def _get_fail_reason_html(self, result: TestResult) -> str:
        """获取失败原因HTML"""
        if not result.test_results:
            return ""

        last_result = result.test_results[-1]
        if last_result.passed:
            return ""

        return f"""
        <div class="section">
            <div class="highlight">
                <h3>⚠️ 测试停止原因</h3>
                <p>{last_result.fail_reason}</p>
            </div>
        </div>
        """

    def _get_test_results_table(self, result: TestResult) -> str:
        """获取测试结果表格HTML"""
        rows = []
        for r in result.test_results:
            status_class = "status-pass" if r.passed else "status-fail"
            status_text = "通过" if r.passed else "失败"
            row = f"""
                    <tr>
                        <td><strong>{r.concurrent_count}</strong></td>
                        <td>{r.avg_first_packet_latency_ms:.2f}</td>
                        <td>{r.max_first_packet_latency_ms:.2f}</td>
                        <td>{r.min_first_packet_latency_ms:.2f}</td>
                        <td>{r.avg_cpu_percent:.1f}</td>
                        <td>{r.peak_cpu_percent:.1f}</td>
                        <td>{r.avg_memory_percent:.1f}</td>
                        <td>{r.peak_memory_percent:.1f}</td>
                        <td>{r.success_rate:.1f}%</td>
                        <td class="{status_class}">{status_text}</td>
                    </tr>
            """
            rows.append(row)

        return "\n".join(rows)

    def _get_latency_detail_table(self, result: TestResult) -> str:
        """获取延迟详情表格"""
        if not result.test_results:
            return ""

        last_result = result.test_results[-1]
        if not last_result.latency_stats:
            return ""

        rows = []
        for s in last_result.latency_stats:
            status_class = "status-pass" if s.success else "status-fail"
            status_text = "成功" if s.success else "失败"
            error = s.error_message if s.error_message else "-"
            row = f"""
                    <tr>
                        <td>{s.client_id}</td>
                        <td>{s.first_packet_latency_ms:.2f}</td>
                        <td>{s.connect_time_ms:.2f}</td>
                        <td>{s.total_duration_ms:.2f}</td>
                        <td>{s.partial_results_count}</td>
                        <td>{s.final_results_count}</td>
                        <td class="{status_class}">{status_text}</td>
                        <td>{error}</td>
                    </tr>
            """
            rows.append(row)

        return f"""
        <div class="section">
            <div class="section-title">
                <div class="icon"></div>
                最后一轮测试 - 各路客户端详细延迟
            </div>
            <table>
                <thead>
                    <tr>
                        <th>客户端ID</th>
                        <th>首包延迟 (ms)</th>
                        <th>连接时间 (ms)</th>
                        <th>总时长 (ms)</th>
                        <th>部分结果数</th>
                        <th>最终结果数</th>
                        <th>状态</th>
                        <th>错误信息</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """

    def generate_all_reports(self, result: TestResult) -> Dict[str, str]:
        """
        生成所有格式的报告

        Args:
            result: 测试结果

        Returns:
            报告文件路径字典
        """
        json_path = self.generate_json_report(result)
        html_path = self.generate_html_report(result)

        return {
            "json": json_path,
            "html": html_path
        }
