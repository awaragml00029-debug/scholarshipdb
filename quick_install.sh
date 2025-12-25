#!/bin/bash
# 快速安装脚本 - 适用于已有Python环境

echo "正在安装依赖包..."
pip install --user loguru beautifulsoup4 lxml pydantic pydantic-settings sqlalchemy playwright python-dotenv

echo ""
echo "正在安装Playwright浏览器..."
python -m playwright install chromium

echo ""
echo "✓ 安装完成！"
echo ""
echo "运行以下命令测试系统："
echo "  python main.py test"
