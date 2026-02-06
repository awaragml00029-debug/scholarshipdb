# PhD Scholarship Scraper

一个用于抓取 scholarshipdb.net 网站上PhD奖学金信息的自动化系统。该系统使用Playwright绕过Cloudflare保护，并将数据存储在数据库中供后续分析和查询。

## 功能特性

- ✅ 使用Playwright自动化浏览器绕过Cloudflare保护
- ✅ 完整的PhD奖学金信息抓取
- ✅ SQLite/PostgreSQL数据库存储
- ✅ 增量更新支持（避免重复抓取）
- ✅ 详细的日志记录
- ✅ 智能重试机制
- ✅ 随机延迟防止封禁
- ✅ 数据搜索和统计功能

## 系统架构

```
scholarshipdb/
├── config.py           # 配置管理
├── models.py           # 数据模型
├── database.py         # 数据库连接
├── scraper.py          # 爬虫核心逻辑
├── storage.py          # 数据存储
├── main.py             # 主程序入口
├── requirements.txt    # 依赖包
├── .env.example        # 环境变量示例
└── README.md           # 本文件
```

## 安装步骤

### 1. 克隆仓库

```bash
cd scholarshipdb
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 安装Playwright浏览器

```bash
playwright install chromium
```

### 5. 配置环境变量

```bash
cp .env.example .env
# 根据需要编辑 .env 文件
```

## 使用方法

### 测试抓取器

首先运行测试模式，确保系统能够成功绕过Cloudflare并访问网站：

```bash
python main.py test
```

这将：
- 尝试访问PhD奖学金页面
- 验证Cloudflare绕过是否成功
- 保存页面HTML到 `page_sample.html` 供检查
- 尝试解析第一页的奖学金信息

### 基本抓取

抓取所有PhD奖学金列表（只抓取列表信息）：

```bash
python main.py scrape
```

### 详细抓取

抓取列表并获取每个奖学金的详细信息（速度较慢但信息更全）：

```bash
python main.py scrape --details
```

### 同步到 Google Sheets

在抓取后将数据追加到指定 Google Sheets（按 `url` 去重）：

1. 创建 Google Service Account 并下载凭据 JSON
2. 将表格共享给该 Service Account 邮箱（编辑权限）
3. 设置环境变量并运行同步脚本：

```bash
export GOOGLE_SHEETS_SPREADSHEET_ID=你的SheetID
export GOOGLE_SHEETS_SHEET_NAME=shcolardb
export GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json
python sync_to_sheets.py
```

### 查看统计

查看数据库中的统计信息：

```bash
python main.py stats
```

### 搜索奖学金

在数据库中搜索奖学金：

```bash
python main.py search "computer science"
python main.py search "machine learning"
```

## 配置说明

主要配置项在 `.env` 文件中：

```bash
# 数据库配置
DATABASE_URL=sqlite:///./scholarships.db

# 爬虫配置
SCRAPER_HEADLESS=true          # 无头模式（后台运行）
SCRAPER_TIMEOUT=30000          # 页面加载超时（毫秒）
SCRAPER_MAX_RETRIES=3          # 最大重试次数
SCRAPER_DELAY_MIN=2            # 最小延迟（秒）
SCRAPER_DELAY_MAX=5            # 最大延迟（秒）

# 日志配置
LOG_LEVEL=INFO                 # 日志级别
LOG_FILE=scraper.log           # 日志文件

# 目标网站
BASE_URL=https://scholarshipdb.net
```

## 数据库结构

### Scholarship 表

存储奖学金信息：

- `id`: 主键
- `title`: 奖学金标题
- `url`: 详情页URL
- `university`: 大学名称
- `country`: 国家
- `field_of_study`: 研究领域
- `degree_level`: 学位级别
- `description`: 描述
- `deadline`: 申请截止日期
- `funding_type`: 资助类型
- `source_id`: 源网站ID（用于去重）
- `scraped_at`: 抓取时间
- 等等...

### ScrapingLog 表

记录抓取会话：

- `id`: 主键
- `started_at`: 开始时间
- `completed_at`: 完成时间
- `status`: 状态（success/failed/partial）
- `total_scholarships`: 总数
- `new_scholarships`: 新增数量
- `updated_scholarships`: 更新数量

## Cloudflare 绕过策略

系统采用多种技术绕过Cloudflare保护：

1. **真实浏览器模拟**：使用Playwright而非简单的HTTP请求
2. **反检测设置**：
   - 禁用自动化控制特征
   - 使用真实的User-Agent
   - 设置完整的浏览器上下文
3. **JavaScript执行**：屏蔽webdriver检测
4. **等待策略**：等待Cloudflare验证完成
5. **随机延迟**：模拟人类浏览行为

## 使用示例

### Python脚本调用

```python
import asyncio
from scraper import ScholarshipScraper
from storage import ScholarshipStorage

async def custom_scrape():
    async with ScholarshipScraper() as scraper:
        # 获取奖学金列表
        scholarships = await scraper.get_phd_scholarships_list()

        # 保存到数据库
        stats = ScholarshipStorage.save_scholarships_batch(scholarships)
        print(f"Saved: {stats}")

asyncio.run(custom_scrape())
```

### 数据查询

```python
from storage import ScholarshipStorage

# 搜索奖学金
results = ScholarshipStorage.search_scholarships(
    query="AI",
    country="USA",
    limit=10
)

for scholarship in results:
    print(scholarship.title)
```

## 注意事项

1. **合法使用**：请遵守网站的robots.txt和使用条款
2. **访问频率**：不要设置过于频繁的抓取，建议使用默认的2-5秒延迟
3. **数据更新**：定期运行以获取最新奖学金信息
4. **Cloudflare更新**：如果Cloudflare策略更新导致无法访问，可能需要调整绕过策略
5. **网站结构变化**：如果网站HTML结构改变，需要更新解析器中的CSS选择器

## 故障排除

### 问题：403 Forbidden错误

**解决方案**：
- 尝试设置 `SCRAPER_HEADLESS=false` 观察浏览器行为
- 增加 `SCRAPER_DELAY_MIN` 和 `SCRAPER_DELAY_MAX`
- 检查IP是否被封禁

### 问题：找不到奖学金数据

**解决方案**：
- 运行 `python main.py test` 并检查 `page_sample.html`
- 网站HTML结构可能已改变，需要更新 `scraper.py` 中的CSS选择器

### 问题：浏览器启动失败

**解决方案**：
- 确保已运行 `playwright install chromium`
- 检查系统依赖是否完整

## 技术栈

- **Python 3.8+**
- **Playwright**: 浏览器自动化
- **BeautifulSoup4**: HTML解析
- **SQLAlchemy**: ORM
- **Loguru**: 日志记录
- **Pydantic**: 配置管理

## 未来改进

- [ ] 添加多线程/多进程支持
- [ ] 支持代理池
- [ ] 添加Web界面查看数据
- [ ] 导出功能（CSV, JSON, Excel）
- [ ] 邮件通知新奖学金
- [ ] 定时任务支持（cron）
- [ ] 更多过滤和搜索选项
- [ ] API接口

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 联系方式

如有问题，请创建Issue。
