"""
WeNet 语音识别压力测试系统
============================

使用方法:
    1. 安装依赖: pip install -r requirements.txt
    2. 启动Web界面: python run_stress_test.py
    3. 打开浏览器访问 http://localhost:5000

功能特性:
    - 模拟N路客户端同时发起流式解码请求
    - 循环播放音频文件模拟实时语音流
    - 测量单路首包延迟
    - 监控CPU/内存资源占用
    - 自动确定最大并发路数
    - 生成详细的HTML/JSON报告
    - Web界面配置和控制测试
"""

import os
import sys
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

os.chdir(SCRIPT_DIR)


def check_dependencies():
    """检查依赖是否安装"""
    missing_deps = []
    
    try:
        import flask
    except ImportError:
        missing_deps.append('flask')
    
    try:
        import websockets
    except ImportError:
        missing_deps.append('websockets')
    
    try:
        import psutil
    except ImportError:
        missing_deps.append('psutil')
    
    try:
        import soundfile
    except ImportError:
        missing_deps.append('soundfile')
    
    if missing_deps:
        print("❌ 缺少以下依赖包:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print("\n请运行以下命令安装依赖:")
        print(f"   pip install {' '.join(missing_deps)}")
        sys.exit(1)
    
    print("✅ 所有依赖检查通过")


def run_web_server(host='0.0.0.0', port=5000, debug=False):
    """启动Web服务器"""
    from web_app import run_server
    
    print(f"\n🚀 启动Web服务器...")
    print(f"   地址: http://{host}:{port}")
    print(f"   按 Ctrl+C 停止服务器\n")
    
    run_server(host=host, port=port, debug=debug)


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description='WeNet 语音识别压力测试系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Web服务器绑定地址 (默认: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Web服务器端口 (默认: 5000)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='启用调试模式'
    )
    
    parser.add_argument(
        '--check-deps',
        action='store_true',
        help='仅检查依赖是否安装'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  WeNet 语音识别压力测试系统")
    print("=" * 60)
    
    check_dependencies()
    
    if args.check_deps:
        print("\n✅ 依赖检查完成")
        sys.exit(0)
    
    run_web_server(
        host=args.host,
        port=args.port,
        debug=args.debug
    )


if __name__ == '__main__':
    main()
