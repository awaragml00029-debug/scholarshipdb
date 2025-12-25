#!/bin/bash
# UV 快速启动脚本

echo "========================================"
echo "UV 快速安装 - PhD Scholarship Scraper"
echo "========================================"
echo ""

# 检查 UV 是否安装
if ! command -v uv &> /dev/null; then
    echo "错误: UV 未安装"
    echo "请访问 https://github.com/astral-sh/uv 安装 UV"
    exit 1
fi

echo "✓ UV 已安装"
echo ""

# 创建虚拟环境（如果不存在）
if [ ! -d ".venv" ]; then
    echo "创建虚拟环境..."
    uv venv
    echo "✓ 虚拟环境已创建"
else
    echo "✓ 虚拟环境已存在"
fi
echo ""

# 安装 Python 依赖
echo "安装 Python 依赖..."
uv pip install playwright beautifulsoup4 lxml loguru pydantic pydantic-settings sqlalchemy python-dotenv
echo "✓ Python 依赖已安装"
echo ""

# 安装 Playwright 浏览器
echo "安装 Playwright 浏览器..."
uv run playwright install chromium
echo "✓ Playwright 浏览器已安装"
echo ""

# 创建 .env 文件（如果不存在）
if [ ! -f ".env" ]; then
    echo "创建 .env 配置文件..."
    cp .env.example .env
    echo "✓ .env 文件已创建"
else
    echo "✓ .env 文件已存在"
fi
echo ""

# 验证安装
echo "验证安装..."
if uv run python -c "import loguru; import playwright; import sqlalchemy" 2>/dev/null; then
    echo "✓ 所有依赖验证成功"
else
    echo "✗ 依赖验证失败"
    exit 1
fi
echo ""

echo "========================================"
echo "安装完成！"
echo "========================================"
echo ""
echo "运行以下命令测试系统："
echo "  uv run python main.py test"
echo ""
echo "开始抓取："
echo "  uv run python main.py scrape"
echo ""
echo "查看统计："
echo "  uv run python main.py stats"
echo ""
echo "搜索奖学金："
echo "  uv run python main.py search cancer"
echo ""
