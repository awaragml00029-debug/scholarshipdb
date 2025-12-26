# 自定义URL抓取指南

## 功能特点

✅ **自定义URL抓取** - 可以抓取任何scholarshipdb.net的页面
✅ **JSON导出** - 所有数据导出为JSON格式
✅ **时间解析** - 自动将相对时间（"22 hours ago"）转换为绝对时间
✅ **Telegram格式** - 自动格式化为Telegram消息
✅ **无过滤** - 抓取所有数据，您自己决定如何过滤

## 快速开始

### 1. 抓取cancer相关PhD奖学金

```bash
uv run python scrape_custom.py scrape "https://scholarshipdb.net/scholarships/Program-PhD?q=cancer"
```

输出：`scholarships.json` 包含所有抓取的数据

### 2. 抓取UK奖学金并保存到自定义文件

```bash
uv run python scrape_custom.py scrape "https://scholarshipdb.net/scholarships-in-United-Kingdom" uk_scholarships.json
```

### 3. 抓取AI相关奖学金，限制5页

```bash
uv run python scrape_custom.py scrape "https://scholarshipdb.net/scholarships/Program-PhD?q=AI" ai.json 5
```

### 4. 格式化为Telegram消息

```bash
uv run python scrape_custom.py telegram scholarships.json 17
```

这会生成：
- `telegram_message_1.txt` - 第1-17条
- `telegram_message_2.txt` - 第18-34条
- 等等...

## JSON数据格式

每条奖学金包含：

```json
{
  "title": "Creative Bridges PhD Studentships",
  "url": "https://scholarshipdb.net/scholarships-in-United-Kingdom/...",
  "location": "Leeds, England",
  "country": "United Kingdom",
  "description": "industry partners. Creative Bridges will train PhD students...",
  "posted_time": "2025-12-24T23:00:00+00:00",
  "posted_time_text": "about 22 hours ago",
  "scraped_at": "2025-12-25T21:00:00+00:00"
}
```

## 使用示例

### 示例1：抓取多个不同类别

```bash
# Cancer研究
uv run python scrape_custom.py scrape \
  "https://scholarshipdb.net/scholarships/Program-PhD?q=cancer" \
  cancer_phd.json

# AI/机器学习
uv run python scrape_custom.py scrape \
  "https://scholarshipdb.net/scholarships/Program-PhD?q=machine+learning" \
  ml_phd.json

# 生物学
uv run python scrape_custom.py scrape \
  "https://scholarshipdb.net/scholarships/Program-PhD?q=biology" \
  biology_phd.json

# 特定国家
uv run python scrape_custom.py scrape \
  "https://scholarshipdb.net/scholarships-in-United-Kingdom" \
  uk_phd.json
```

### 示例2：Python脚本中使用

```python
import asyncio
from scraper_v2 import scrape_custom_url, ScholarshipScraperV2

async def main():
    # 抓取数据
    scholarships = await scrape_custom_url(
        "https://scholarshipdb.net/scholarships/Program-PhD?q=cancer",
        output_file="cancer.json",
        max_pages=5
    )

    print(f"抓取到 {len(scholarships)} 条奖学金")

    # 格式化为Telegram消息
    messages = ScholarshipScraperV2.format_for_telegram(scholarships, per_page=17)

    for i, msg in enumerate(messages, 1):
        print(f"\n=== 消息 {i} ===")
        print(msg)

asyncio.run(main())
```

### 示例3：批量抓取并合并

```python
import asyncio
import json
from scraper_v2 import scrape_custom_url

async def scrape_multiple_categories():
    categories = {
        'cancer': 'https://scholarshipdb.net/scholarships/Program-PhD?q=cancer',
        'ai': 'https://scholarshipdb.net/scholarships/Program-PhD?q=artificial+intelligence',
        'physics': 'https://scholarshipdb.net/scholarships/Program-PhD?q=physics',
    }

    all_scholarships = {}

    for name, url in categories.items():
        print(f"抓取 {name}...")
        scholarships = await scrape_custom_url(url, max_pages=3)
        all_scholarships[name] = scholarships
        await asyncio.sleep(5)  # 延迟避免过快请求

    # 保存所有类别
    with open('all_categories.json', 'w', encoding='utf-8') as f:
        json.dump(all_scholarships, f, ensure_ascii=False, indent=2)

    # 统计
    for name, scholarships in all_scholarships.items():
        print(f"{name}: {len(scholarships)} 条")

asyncio.run(scrape_multiple_categories())
```

## Telegram消息格式

```
📚 PhD Scholarships (1-17 of 34)

1. Creative Bridges PhD Studentships
   📍 Leeds, England, United Kingdom
   ⏰ about 22 hours ago
   📝 industry partners. Creative Bridges will train PhD students in the latest knowledge...
   🔗 https://scholarshipdb.net/...

2. [下一条]
...
```

## RSS Feed集成

JSON数据可以轻松转换为RSS格式：

```python
import json
from datetime import datetime

def json_to_rss(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        scholarships = json.load(f)

    rss_items = []
    for sch in scholarships:
        item = f"""
    <item>
        <title>{sch['title']}</title>
        <link>{sch['url']}</link>
        <description>{sch.get('description', '')}</description>
        <pubDate>{sch.get('posted_time', '')}</pubDate>
        <category>{sch.get('country', '')}</category>
    </item>"""
        rss_items.append(item)

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>PhD Scholarships</title>
    <link>https://scholarshipdb.net</link>
    <description>Latest PhD scholarships</description>
    {''.join(rss_items)}
  </channel>
</rss>"""

    with open('scholarships.rss', 'w', encoding='utf-8') as f:
        f.write(rss)

json_to_rss('scholarships.json')
```

## 常用URL模板

```bash
# PhD奖学金（按主题搜索）
https://scholarshipdb.net/scholarships/Program-PhD?q=<关键词>

# 按国家
https://scholarshipdb.net/scholarships-in-<Country>

# 按学位级别
https://scholarshipdb.net/scholarships/Program-<Level>
# Level: PhD, Master, Bachelor, Postdoctoral

# 组合搜索
https://scholarshipdb.net/scholarships/Program-PhD?q=<关键词>&country=<国家>
```

## 时间字段说明

每条奖学金有两个时间字段：

1. **posted_time** - 绝对时间（ISO 8601格式）
   - 格式：`2025-12-24T23:00:00+00:00`
   - 可以直接排序和比较
   - 用于程序处理

2. **posted_time_text** - 原始相对时间
   - 格式：`about 22 hours ago`
   - 更人性化
   - 用于显示给用户

时间解析支持：
- `X minutes ago`
- `X hours ago`
- `X days ago`
- `X weeks ago`
- `X months ago`
- `X years ago`
- `about X hours ago`

## 注意事项

1. **请求频率**：建议在批量抓取时添加延迟（2-5秒）
2. **数据验证**：JSON输出的所有字段都可能为null，使用时需要检查
3. **分页限制**：默认最多抓取10页，可以通过参数调整
4. **Cloudflare**：系统会自动处理Cloudflare验证，通常需要几秒钟

## 故障排除

### 问题：没有找到数据

检查JSON文件是否为空数组`[]`。可能原因：
- URL错误
- 页面结构改变
- Cloudflare阻止

解决：运行调试模式查看详细日志

### 问题：时间解析错误

某些时间格式可能无法识别。原始时间文本会保留在`posted_time_text`字段中。

### 问题：Telegram消息太长

调整`per_page`参数减少每页数量：

```bash
uv run python scrape_custom.py telegram scholarships.json 10
```

## 完整命令参考

```bash
# 基本抓取
uv run python scrape_custom.py scrape <URL>

# 自定义输出文件
uv run python scrape_custom.py scrape <URL> <output.json>

# 限制页数
uv run python scrape_custom.py scrape <URL> <output.json> <max_pages>

# 生成Telegram消息
uv run python scrape_custom.py telegram <input.json>

# 自定义每页数量
uv run python scrape_custom.py telegram <input.json> <per_page>
```

## 需要帮助？

查看详细日志：

```bash
# 设置日志级别为DEBUG
LOG_LEVEL=DEBUG uv run python scrape_custom.py scrape <URL>
```
