# 服务器环境修复指南

## 问题：BrowserType.launch 失败

如果您看到错误：`BrowserType.launch: Target page, context or browser has been closed`

这是在服务器/Docker环境中运行Playwright的常见问题。

## 解决方案

### 方案1：使用更新后的代码（推荐）

代码已更新，添加了服务器环境支持。重新运行：

```bash
uv run python main.py scrape
```

### 方案2：安装系统依赖

确保安装所有必要的系统依赖：

```bash
# 安装 Playwright 系统依赖
uv run playwright install-deps chromium

# 或手动安装（Debian/Ubuntu）
sudo apt-get update
sudo apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2
```

### 方案3：使用 Xvfb（虚拟显示）

如果仍然失败，使用虚拟显示：

```bash
# 安装 xvfb
sudo apt-get install -y xvfb

# 使用 xvfb 运行
xvfb-run -a uv run python main.py scrape
```

创建包装脚本 `run_with_xvfb.sh`:

```bash
#!/bin/bash
xvfb-run -a uv run python main.py "$@"
```

使用：

```bash
chmod +x run_with_xvfb.sh
./run_with_xvfb.sh scrape
```

### 方案4：使用 Firefox 替代 Chromium

修改 `.env` 文件添加：

```bash
USE_FIREFOX=true
```

然后修改 `scraper.py` 的启动代码：

```python
# 使用 Firefox
self.browser = await self.playwright.firefox.launch(...)
```

### 方案5：Docker 环境

如果在 Docker 中运行，使用官方 Playwright 镜像：

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

CMD ["python", "main.py", "scrape"]
```

构建和运行：

```bash
docker build -t scholarship-scraper .
docker run --rm scholarship-scraper
```

### 方案6：增加超时和重试

修改 `.env`:

```bash
SCRAPER_TIMEOUT=60000      # 增加到 60 秒
SCRAPER_MAX_RETRIES=5      # 增加重试次数
```

### 方案7：调试模式

查看详细错误信息：

```bash
# 设置环境变量
export DEBUG=pw:api
export PLAYWRIGHT_BROWSERS_PATH=/tmp/playwright

# 运行
uv run python main.py scrape
```

## 验证修复

运行测试脚本验证浏览器是否正常：

```bash
uv run python -c "
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-setuid-sandbox', '--single-process']
    )
    page = browser.new_page()
    page.goto('https://www.google.com')
    print('✓ Playwright 工作正常')
    browser.close()
"
```

## 如果所有方案都失败

### 备选方案：使用 cloudscraper

创建 `scraper_alternative.py`:

```python
import cloudscraper
from bs4 import BeautifulSoup

scraper = cloudscraper.create_scraper()
url = "https://scholarshipdb.net/scholarships/Program-PhD?q=cancer"

try:
    response = scraper.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'lxml')
        print("✓ 成功获取页面")
        # 解析数据...
    else:
        print(f"✗ 失败: {response.status_code}")
except Exception as e:
    print(f"✗ 错误: {e}")
```

安装：

```bash
uv pip install cloudscraper
uv run python scraper_alternative.py
```

## 推荐的启动参数

当前代码已包含以下服务器优化参数：

```python
args=[
    '--disable-blink-features=AutomationControlled',
    '--disable-dev-shm-usage',
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-gpu',
    '--disable-software-rasterizer',
    '--disable-extensions',
    '--no-first-run',
    '--no-zygote',
    '--single-process',  # 关键：单进程模式
    '--disable-web-security',
    '--disable-features=IsolateOrigins,site-per-process',
]
```

## 常见错误及解决

### 错误: "Target closed"
- 使用 `--single-process` 参数（已添加）
- 增加超时时间

### 错误: "Protocol error"
- 安装系统依赖
- 使用 xvfb

### 错误: "Browser closed"
- 检查内存是否足够（至少 2GB）
- 使用 `--disable-dev-shm-usage`（已添加）

## 获取帮助

1. 查看完整日志：`LOG_LEVEL=DEBUG uv run python main.py scrape`
2. 检查系统资源：`free -h` 和 `df -h`
3. 测试浏览器：运行上面的验证脚本
