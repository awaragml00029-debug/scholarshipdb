# 部署指南 / Deployment Guide

## 环境要求

### 最低要求
- Python 3.8 或更高版本
- 2GB RAM
- 1GB 可用磁盘空间
- 稳定的互联网连接

### 推荐环境
- Ubuntu 20.04+ / Debian 11+ / macOS 10.15+ / Windows 10+
- Python 3.11
- 4GB RAM
- Chrome/Chromium 支持

## 快速开始

### 1. Linux/Mac 环境

```bash
# 克隆仓库
git clone <repository-url>
cd scholarshipdb

# 运行自动安装脚本
bash setup.sh

# 激活虚拟环境
source venv/bin/activate

# 复制并编辑配置文件
cp .env.example .env
nano .env  # 根据需要修改配置

# 测试系统
python main.py test

# 开始抓取
python main.py scrape
```

### 2. Windows 环境

```powershell
# 克隆仓库
git clone <repository-url>
cd scholarshipdb

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium

# 复制配置文件
copy .env.example .env
# 使用文本编辑器编辑 .env

# 测试系统
python main.py test

# 开始抓取
python main.py scrape
```

## 手动安装步骤

### 步骤 1: 安装 Python 依赖

```bash
pip install -r requirements.txt
```

依赖包括:
- playwright - 浏览器自动化
- beautifulsoup4 - HTML 解析
- lxml - XML/HTML 解析器
- loguru - 日志记录
- pydantic - 配置管理
- pydantic-settings - 设置管理
- sqlalchemy - 数据库 ORM

### 步骤 2: 安装 Playwright 浏览器

```bash
# 仅安装 Chromium
playwright install chromium

# 或安装所有浏览器
playwright install

# 在某些 Linux 系统上可能需要系统依赖
playwright install-deps chromium
```

### 步骤 3: 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# 数据库配置
DATABASE_URL=sqlite:///./scholarships.db
# 使用 PostgreSQL (可选)
# DATABASE_URL=postgresql://user:password@localhost/scholarshipdb

# 爬虫配置
SCRAPER_HEADLESS=true          # false 可以看到浏览器窗口
SCRAPER_TIMEOUT=30000          # 页面加载超时（毫秒）
SCRAPER_MAX_RETRIES=3          # 重试次数
SCRAPER_DELAY_MIN=2            # 最小延迟（秒）
SCRAPER_DELAY_MAX=5            # 最大延迟（秒）

# 日志配置
LOG_LEVEL=INFO                 # DEBUG, INFO, WARNING, ERROR
LOG_FILE=scraper.log

# 目标网站
BASE_URL=https://scholarshipdb.net
```

## 使用方法

### 测试模式

首次运行建议使用测试模式：

```bash
python main.py test
```

这将：
- 验证 Cloudflare 绕过是否成功
- 保存页面 HTML 到 `page_sample.html`
- 保存截图到 `page_screenshot.png`
- 尝试解析第一页的奖学金

### 基本抓取

```bash
# 抓取奖学金列表（只抓取基本信息）
python main.py scrape

# 抓取详细信息（包括每个奖学金的详情页）
python main.py scrape --details
```

### 查看统计信息

```bash
python main.py stats
```

### 搜索数据库

```bash
python main.py search "cancer"
python main.py search "computer science"
python main.py search "machine learning"
```

## 针对特定搜索的使用

如果您想抓取特定搜索结果（如您提供的 cancer 相关 PhD），可以修改 `main.py` 或创建自定义脚本：

```python
import asyncio
from scraper import ScholarshipScraper
from storage import ScholarshipStorage
from bs4 import BeautifulSoup

async def scrape_cancer_phd():
    """抓取 cancer 相关的 PhD 奖学金"""
    async with ScholarshipScraper() as scraper:
        # 访问搜索结果页面
        url = "https://scholarshipdb.net/scholarships/Program-PhD?q=cancer"
        await scraper.navigate_with_retry(url)

        scholarships = []
        page = 1

        while page <= 10:  # 限制最多 10 页
            print(f"正在抓取第 {page} 页...")

            # 获取页面内容
            content = await scraper.page.content()
            soup = BeautifulSoup(content, 'lxml')

            # 解析奖学金
            page_scholarships = scraper.parse_scholarship_list(soup)

            if not page_scholarships:
                break

            scholarships.extend(page_scholarships)

            # 尝试下一页
            has_next = await scraper.go_to_next_page()
            if not has_next:
                break

            await scraper.random_delay()
            page += 1

        # 保存到数据库
        stats = ScholarshipStorage.save_scholarships_batch(scholarships)
        print(f"完成！新增: {stats['new']}, 更新: {stats['updated']}")

if __name__ == "__main__":
    asyncio.run(scrape_cancer_phd())
```

保存为 `scrape_cancer.py` 并运行：

```bash
python scrape_cancer.py
```

## 调整 HTML 解析器

网站的 HTML 结构可能与代码中的选择器不匹配。如需调整：

1. 运行测试模式获取 HTML：
   ```bash
   python main.py test
   ```

2. 检查 `page_sample.html` 文件，找到奖学金列表的 HTML 结构

3. 修改 `scraper.py` 中的 `parse_scholarship_list()` 方法

例如，如果奖学金在 `<div class="scholarship-card">` 中：

```python
def parse_scholarship_list(self, soup: BeautifulSoup) -> List[Dict]:
    """Parse scholarship listings from the page."""
    scholarships = []

    # 修改这里的选择器
    articles = soup.select('div.scholarship-card')

    for article in articles:
        try:
            # 修改字段提取逻辑
            title_elem = article.find('h3', class_='title')
            # ... 更多字段
        except Exception as e:
            logger.error(f"Error parsing scholarship: {e}")
            continue

    return scholarships
```

## 定时任务

### Linux/Mac (cron)

编辑 crontab：

```bash
crontab -e
```

添加定时任务（每天凌晨 2 点运行）：

```bash
0 2 * * * cd /path/to/scholarshipdb && /path/to/venv/bin/python main.py scrape >> /var/log/scholarship-scraper.log 2>&1
```

### Windows (Task Scheduler)

1. 打开任务计划程序
2. 创建基本任务
3. 设置触发器（每天）
4. 设置操作：
   - 程序: `C:\path\to\venv\Scripts\python.exe`
   - 参数: `main.py scrape`
   - 起始于: `C:\path\to\scholarshipdb`

## 数据库管理

### SQLite（默认）

数据存储在 `scholarships.db` 文件中。

查看数据：

```bash
sqlite3 scholarships.db
```

```sql
-- 查看所有表
.tables

-- 查看奖学金数量
SELECT COUNT(*) FROM scholarships;

-- 查看最新的 10 条奖学金
SELECT title, university, country FROM scholarships ORDER BY scraped_at DESC LIMIT 10;

-- 导出为 CSV
.mode csv
.output scholarships.csv
SELECT * FROM scholarships;
.quit
```

### PostgreSQL（生产环境推荐）

安装 PostgreSQL：

```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql
```

创建数据库：

```sql
CREATE DATABASE scholarshipdb;
CREATE USER scraper WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE scholarshipdb TO scraper;
```

修改 `.env`：

```bash
DATABASE_URL=postgresql://scraper:your_password@localhost/scholarshipdb
```

## 故障排除

### 问题 1: Cloudflare 403 错误

**症状**: 测试时显示 403 Forbidden

**解决方案**:
1. 设置 `SCRAPER_HEADLESS=false` 观察浏览器行为
2. 增加延迟时间 `SCRAPER_DELAY_MIN=5` 和 `SCRAPER_DELAY_MAX=10`
3. 检查 IP 是否被封禁（尝试更换网络）
4. 更新 Playwright 到最新版本

### 问题 2: 找不到奖学金数据

**症状**: 解析器返回 0 条奖学金

**解决方案**:
1. 运行 `python main.py test` 并检查 `page_sample.html`
2. 网站 HTML 结构可能已改变
3. 更新 `scraper.py` 中的 CSS 选择器
4. 参考上面的"调整 HTML 解析器"部分

### 问题 3: 浏览器启动失败

**症状**: `Executable doesn't exist` 错误

**解决方案**:
```bash
# 重新安装浏览器
playwright install chromium

# 或安装系统依赖
playwright install-deps
```

### 问题 4: 内存不足

**症状**: 程序崩溃或变慢

**解决方案**:
1. 减少并发页面数
2. 不使用 `--details` 模式
3. 分批抓取，而不是一次性抓取所有

### 问题 5: 数据库锁定 (SQLite)

**症状**: `database is locked` 错误

**解决方案**:
1. 不要同时运行多个抓取进程
2. 考虑使用 PostgreSQL
3. 增加 SQLite 超时：
   ```python
   engine = create_engine(
       settings.database_url,
       connect_args={"timeout": 30}
   )
   ```

## 性能优化

### 1. 使用无头模式

```bash
SCRAPER_HEADLESS=true
```

### 2. 调整延迟

在不被封禁的前提下减少延迟：

```bash
SCRAPER_DELAY_MIN=1
SCRAPER_DELAY_MAX=3
```

### 3. 使用代理（可选）

修改 `scraper.py` 中的浏览器启动代码：

```python
self.browser = await self.playwright.chromium.launch(
    headless=settings.scraper_headless,
    proxy={
        "server": "http://proxy-server:port",
        "username": "username",
        "password": "password"
    }
)
```

### 4. 并行抓取（高级）

创建多个 Scraper 实例并行运行（需要小心避免被封禁）。

## 监控和日志

日志文件位置: `scraper.log`

实时查看日志:

```bash
tail -f scraper.log
```

日志配置在 `.env` 中：

```bash
LOG_LEVEL=INFO     # DEBUG 可以看到更详细的信息
LOG_FILE=scraper.log
```

## 生产环境部署

### Docker 部署（推荐）

创建 `Dockerfile`:

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py", "scrape"]
```

构建和运行：

```bash
docker build -t scholarship-scraper .
docker run -v $(pwd)/scholarships.db:/app/scholarships.db scholarship-scraper
```

### Systemd 服务（Linux）

创建 `/etc/systemd/system/scholarship-scraper.service`:

```ini
[Unit]
Description=PhD Scholarship Scraper
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/scholarshipdb
ExecStart=/path/to/venv/bin/python main.py scrape
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

启用和启动服务：

```bash
sudo systemctl enable scholarship-scraper
sudo systemctl start scholarship-scraper
sudo systemctl status scholarship-scraper
```

## 安全建议

1. **不要提交 `.env` 文件到 Git**
2. **使用强密码**（如果使用 PostgreSQL）
3. **定期备份数据库**
4. **遵守网站的 robots.txt 和使用条款**
5. **不要设置过于频繁的抓取**
6. **使用 HTTPS 连接数据库**

## 支持

如有问题:
1. 检查日志文件 `scraper.log`
2. 运行测试模式 `python main.py test`
3. 查看 GitHub Issues
4. 阅读 README.md

## 许可证

MIT License - 详见 LICENSE 文件
