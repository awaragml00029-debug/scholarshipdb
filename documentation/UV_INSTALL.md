# UV 安装指南

## 使用 UV 快速安装和运行

### 完整安装命令

```bash
# 1. 创建虚拟环境（如果还没有）
uv venv

# 2. 安装所有依赖
uv pip install playwright beautifulsoup4 lxml loguru pydantic pydantic-settings sqlalchemy python-dotenv

# 3. 安装 Playwright 浏览器
uv run playwright install chromium

# 4. 安装 Playwright 系统依赖（Linux）
uv run playwright install-deps chromium
```

### 一键安装命令

```bash
uv pip install playwright beautifulsoup4 lxml loguru pydantic pydantic-settings sqlalchemy python-dotenv && uv run playwright install chromium
```

## 运行命令

安装完成后，使用 `uv run` 运行程序：

```bash
# 测试模式
uv run python main.py test

# 开始抓取
uv run python main.py scrape

# 抓取详细信息
uv run python main.py scrape --details

# 查看统计
uv run python main.py stats

# 搜索
uv run python main.py search cancer
```

## 或者激活虚拟环境后直接运行

```bash
# 激活虚拟环境
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows

# 然后可以直接运行
python main.py test
python main.py scrape
```

## 快速启动脚本（使用 UV）

```bash
#!/bin/bash
# uv_quick_start.sh

echo "使用 UV 安装依赖..."
uv pip install playwright beautifulsoup4 lxml loguru pydantic pydantic-settings sqlalchemy python-dotenv

echo "安装 Playwright 浏览器..."
uv run playwright install chromium

echo "✓ 安装完成！"
echo ""
echo "运行测试："
echo "  uv run python main.py test"
```

## 验证安装

```bash
uv run python -c "import loguru; import playwright; import sqlalchemy; print('✓ 所有依赖已安装')"
```

## pyproject.toml 配置（可选）

如果您想使用 `pyproject.toml` 管理依赖，可以创建：

```toml
[project]
name = "scholarshipdb"
version = "1.0.0"
description = "PhD Scholarship Scraper"
requires-python = ">=3.8"
dependencies = [
    "playwright>=1.48.0",
    "beautifulsoup4>=4.12.3",
    "lxml>=5.1.0",
    "loguru>=0.7.2",
    "pydantic>=2.5.3",
    "pydantic-settings>=2.1.0",
    "sqlalchemy>=2.0.25",
    "python-dotenv>=1.0.0",
]

[project.scripts]
scholarship-scraper = "main:main"
```

然后使用：

```bash
uv pip install -e .
uv run playwright install chromium
```

## 常见问题

### 问题：找不到 playwright
```bash
# 确保使用 uv run
uv run playwright install chromium
```

### 问题：权限错误
```bash
# UV 会自动处理虚拟环境，不需要 sudo
```

### 问题：浏览器下载失败
```bash
# 手动指定浏览器
uv run python -m playwright install chromium --with-deps
```
