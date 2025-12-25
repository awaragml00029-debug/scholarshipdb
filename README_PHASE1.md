# PhD Scholarship Scraper - Phase 1 自动化系统

## 🎯 概述

Phase 1 实现了一个完全自动化的PhD奖学金抓取和展示系统：

- ✅ **多URL配置** - 通过 `urls.yaml` 管理多个抓取源
- ✅ **自动抓取** - GitHub Actions 每6小时自动运行
- ✅ **数据展示** - 静态网页展示，支持搜索、筛选、排序
- ✅ **零成本** - 完全使用GitHub免费服务
- ✅ **零维护** - 自动化运行，无需服务器

## 📁 项目结构

```
scholarshipdb/
├── urls.yaml                    # URL配置文件（在此添加新URL）
├── batch_scrape.py              # 批量抓取脚本
├── scraper_v2.py                # 核心抓取器
├── time_parser.py               # 时间解析工具
├── .github/
│   └── workflows/
│       └── scrape.yml           # GitHub Actions 工作流
├── docs/
│   ├── index.html               # 网页展示界面
│   └── data/                    # 数据文件（自动生成）
│       ├── cancer_research.json
│       ├── uk_scholarships.json
│       └── all_scholarships.json
└── data/                        # 备份数据文件
    └── *.json
```

## 🚀 快速开始

### 1. 添加新的抓取URL

编辑 `urls.yaml` 文件：

```yaml
sources:
  - name: "my_topic"              # 唯一标识符
    label: "我的主题"              # 显示名称
    url: "https://scholarshipdb.net/scholarships/Program-PhD?q=topic"
    max_pages: 10                 # 最多抓取页数
    enabled: true                 # 是否启用
```

**常用URL模板：**

```bash
# 按主题搜索
https://scholarshipdb.net/scholarships/Program-PhD?q=<关键词>

# 按国家
https://scholarshipdb.net/scholarships-in-<Country>

# 示例：
https://scholarshipdb.net/scholarships/Program-PhD?q=cancer
https://scholarshipdb.net/scholarships-in-United-Kingdom
https://scholarshipdb.net/scholarships/Program-PhD?q=artificial+intelligence
```

### 2. 本地测试抓取

```bash
# 安装依赖
uv pip install -r requirements.txt
playwright install chromium

# 运行批量抓取
python batch_scrape.py
```

输出文件：
- `data/<source_name>.json` - 每个源的独立文件
- `data/all_scholarships.json` - 所有源的合并文件

### 3. 查看网页界面

```bash
# 本地预览（需要先运行抓取生成数据）
cd docs
python -m http.server 8000

# 访问 http://localhost:8000
```

## ⚙️ GitHub Actions 自动化

### 工作流配置

文件：`.github/workflows/scrape.yml`

**触发条件：**
- 每6小时自动运行（`0 */6 * * *`）
- 手动触发（在GitHub仓库的Actions标签页）
- 推送到main/master分支

**工作流程：**
1. 安装依赖和Playwright浏览器
2. 运行批量抓取脚本
3. 将数据复制到docs目录
4. 提交并推送数据到仓库
5. 部署到GitHub Pages

### 启用GitHub Actions

1. 进入仓库设置 → Actions → General
2. 确保"Allow all actions and reusable workflows"已启用
3. 进入Settings → Pages
4. Source选择"GitHub Actions"
5. 等待第一次workflow运行完成

### 手动触发抓取

1. 进入仓库的"Actions"标签
2. 选择"Scrape PhD Scholarships"工作流
3. 点击"Run workflow"按钮
4. 选择分支并点击"Run workflow"

## 🌐 GitHub Pages 网站

### 访问地址

部署完成后，网站地址为：
```
https://<你的用户名>.github.io/<仓库名>/
```

### 功能特性

1. **实时搜索** - 搜索框可搜索所有字段
2. **多维度筛选**：
   - 按来源（Source）
   - 按国家（Country）
   - 按发布时间（最近24小时/3天/一周/一月）
3. **数据统计** - 显示总数、来源数、最后更新时间
4. **响应式设计** - 支持手机、平板、桌面
5. **数据导出** - 支持复制、导出CSV

## 📊 数据格式

### all_scholarships.json 结构

```json
{
  "generated_at": "2025-12-25T21:00:00+00:00",
  "total_scholarships": 150,
  "sources": {
    "cancer_research": 50,
    "uk_scholarships": 100
  },
  "scholarships": [
    {
      "title": "PhD in Cancer Biology",
      "university": "University of Oxford",
      "location": "Oxford, England",
      "country": "United Kingdom",
      "description": "Full scholarship for PhD research...",
      "url": "https://scholarshipdb.net/...",
      "posted_time": "2025-12-24T23:00:00+00:00",
      "posted_time_text": "about 22 hours ago",
      "scraped_at": "2025-12-25T21:00:00+00:00",
      "source_name": "cancer_research",
      "source_label": "Cancer Research",
      "source_url": "https://scholarshipdb.net/scholarships/Program-PhD?q=cancer"
    }
  ]
}
```

## 🔧 配置选项

### urls.yaml 配置说明

```yaml
sources:
  - name: "unique_id"           # 必填：唯一标识符（字母、数字、下划线）
    label: "Display Name"       # 必填：显示名称
    url: "https://..."          # 必填：抓取URL
    max_pages: 10               # 可选：最大页数（默认10）
    enabled: true               # 可选：是否启用（默认true）

config:
  delay_between_sources: 5      # 源之间的延迟（秒）
  output_dir: "data"            # 输出目录
  combined_output: "data/all_scholarships.json"  # 合并文件路径
```

## 📝 工作流程示例

### 场景1：添加新的研究主题

1. 编辑 `urls.yaml`，添加新源：
   ```yaml
   - name: "quantum_computing"
     label: "Quantum Computing"
     url: "https://scholarshipdb.net/scholarships/Program-PhD?q=quantum+computing"
     max_pages: 5
     enabled: true
   ```

2. 提交更改：
   ```bash
   git add urls.yaml
   git commit -m "Add quantum computing scholarships"
   git push
   ```

3. GitHub Actions 自动运行抓取并更新网站

### 场景2：临时禁用某个源

1. 编辑 `urls.yaml`，将 `enabled` 设为 `false`：
   ```yaml
   - name: "physics"
     label: "Physics"
     url: "..."
     enabled: false  # 临时禁用
   ```

2. 提交并推送

### 场景3：调整抓取频率

1. 编辑 `.github/workflows/scrape.yml`
2. 修改 cron 表达式：
   ```yaml
   schedule:
     - cron: '0 */12 * * *'  # 改为每12小时
   ```

## 🐛 故障排除

### 1. GitHub Actions 失败

**查看日志：**
- 进入 Actions 标签
- 点击失败的workflow run
- 查看具体步骤的错误信息

**常见问题：**
- Playwright安装失败 → 检查workflow中的安装步骤
- 抓取超时 → 减少 `max_pages` 或增加源之间的延迟
- 权限错误 → 检查仓库的Actions权限设置

### 2. 网页无法显示数据

**检查：**
1. `docs/data/all_scholarships.json` 是否存在
2. 浏览器控制台是否有错误
3. GitHub Pages 是否正确部署

**解决：**
```bash
# 本地测试数据生成
python batch_scrape.py

# 手动复制数据到docs
mkdir -p docs/data
cp data/*.json docs/data/
```

### 3. 抓取到的数据为空

**检查：**
1. URL是否正确
2. 网站结构是否改变
3. Cloudflare是否阻止

**调试：**
```bash
# 运行单个URL测试
python scrape_custom.py scrape "https://scholarshipdb.net/..." test.json 2

# 查看详细日志
LOG_LEVEL=DEBUG python batch_scrape.py
```

## 🎯 下一步计划（Phase 2）

- [ ] Web管理界面（无需编辑YAML）
- [ ] Telegram机器人通知
- [ ] AI翻译集成（OpenAI API）
- [ ] 邮件订阅功能
- [ ] RSS Feed生成
- [ ] 数据去重和更新检测

## 📚 相关文档

- [自定义抓取指南](CUSTOM_SCRAPER_GUIDE.md)
- [原始项目说明](README.md)

## 💡 提示

1. **定期检查**：每周检查一次GitHub Actions运行状态
2. **数据备份**：数据已自动提交到Git仓库
3. **URL测试**：添加新URL前先用 `scrape_custom.py` 测试
4. **性能优化**：避免同时启用过多源（建议<10个）
5. **尊重网站**：保持合理的抓取频率，避免过度请求

## 📧 问题反馈

如有问题或建议，请在仓库中创建Issue。
