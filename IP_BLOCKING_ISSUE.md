# GitHub Actions IP 封禁问题 🚫

## 🐛 问题描述

在 GitHub Actions 中运行时，浏览器被Cloudflare/网站关闭：

```
Page.goto: Target page, context or browser has been closed
BrowserContext.close: Target page, context or browser has been closed
```

## 🔍 根本原因

**scholarshipdb.net 封禁了 GitHub Actions 的 IP 地址范围**

原因：
1. **Cloudflare 检测** - 识别出来自 GitHub Actions 的大量自动化请求
2. **IP 信誉低** - GitHub Actions 使用的 IP 被很多自动化工具共享
3. **反爬虫措施** - 网站主动阻止云服务提供商的 IP

## ✅ 已实施的优化

### 1. 独立浏览器实例
```python
# 每个源使用独立的浏览器实例
for source in sources:
    async with ScholarshipScraperV2() as scraper:
        # 即使一个源被封，其他源仍可继续
        scholarships = await scraper.scrape_url(url)
```

### 2. 错误处理改进
```python
async def close(self):
    # 处理已关闭的浏览器，避免崩溃
    try:
        await self.page.close()
    except Exception:
        pass  # 忽略"已关闭"错误
```

### 3. 详细日志
```python
logger.exception(e)  # 打印完整traceback帮助调试
```

## 🔧 可行的解决方案

### 方案 1：使用代理服务 ⭐ **推荐**

#### 选项 A：免费代理池

**优点**：免费
**缺点**：不稳定，速度慢

```python
# 在 scraper_v2.py 中添加代理支持
self.browser = await self.playwright.chromium.launch(
    proxy={
        "server": "http://proxy-server:port",
        "username": "user",  # 如果需要
        "password": "pass",  # 如果需要
    }
)
```

**实施步骤**：
1. 注册免费代理服务（如 ProxyScrape, Free Proxy List）
2. 添加到 GitHub Secrets
3. 在代码中配置代理

#### 选项 B：付费代理服务

**推荐服务**：
- **Bright Data** (原 Luminati) - $500/月起
- **Oxylabs** - $300/月起
- **SmartProxy** - $75/月起
- **ScraperAPI** - $49/月起 ⭐ 性价比高

**ScraperAPI 示例**：
```python
import os

SCRAPER_API_KEY = os.getenv('SCRAPER_API_KEY')
proxy_url = f"http://scraperapi:{SCRAPER_API_KEY}@proxy-server.scraperapi.com:8001"

self.browser = await self.playwright.chromium.launch(
    proxy={"server": proxy_url}
)
```

### 方案 2：Self-Hosted Runner 🏠

使用自己的服务器运行 GitHub Actions

**优点**：
- 完全控制 IP
- 不受 GitHub IP 限制
- 可以使用家庭/办公室网络

**缺点**：
- 需要维护服务器
- 可能需要成本

**步骤**：
1. 购买VPS或使用家用电脑
2. 安装 GitHub Actions Runner
3. 配置为 self-hosted runner
4. 修改 workflow 使用 `runs-on: self-hosted`

```yaml
# .github/workflows/scrape.yml
jobs:
  scrape:
    runs-on: self-hosted  # 使用自建 runner
```

### 方案 3：降低抓取频率 📉

减少触发 Cloudflare 的概率

**当前**：每 6 小时运行
**建议**：每 12 或 24 小时运行

```yaml
schedule:
  - cron: '0 */12 * * *'  # 每 12 小时
  # 或
  - cron: '0 0 * * *'     # 每天一次
```

**配合**：
- 减少同时抓取的源数量
- 增加源之间的延迟（10-15秒）

```yaml
# urls.yaml
config:
  delay_between_sources: 15  # 从 5 秒增加到 15 秒
```

### 方案 4：混合策略 🔄

**GitHub Actions + 本地运行**

**设置**：
- GitHub Actions：定时任务（失败也没关系）
- 本地电脑：手动运行或使用 cron（成功率高）

**本地运行**：
```bash
# 每天晚上 10 点运行（Mac/Linux crontab）
0 22 * * * cd /path/to/scholarshipdb && python batch_scrape.py

# 或使用 systemd timer（Linux）
# 或使用 Task Scheduler（Windows）
```

**数据同步**：
```bash
# 本地运行后自动提交
python batch_scrape.py
git add data/*.json docs/data/*.json
git commit -m "Update scholarship data - $(date)"
git push
```

### 方案 5：Selenium Stealth + 浏览器指纹 🥷

增强反检测能力

**安装**：
```bash
pip install playwright-stealth
```

**代码**：
```python
from playwright_stealth import stealth_async

async def start(self):
    self.page = await self.context.new_page()
    await stealth_async(self.page)  # 应用 stealth 模式
```

**配合**：
- 随机化 User-Agent
- 模拟人类行为（随机延迟、鼠标移动）
- 更换浏览器指纹

## 💡 推荐组合方案

### 短期（立即可行）

1. ✅ **使用 Self-Hosted Runner**
   - 在家用电脑或VPS上运行
   - 成本低，见效快
   - 5分钟内设置完成

2. ✅ **降低抓取频率**
   - 改为每 24 小时运行一次
   - 减少被检测风险

### 中期（最佳方案）

1. **ScraperAPI 代理**
   - 月费 $49，性价比高
   - 自动处理 Cloudflare
   - 无需维护

2. **继续使用 GitHub Actions**
   - 零维护成本
   - 自动化部署

### 长期（企业级）

1. **轮换代理池**
   - Bright Data 或 Oxylabs
   - 高成功率，高成本

2. **分布式抓取**
   - 多个 runner 在不同地区
   - AWS Lambda + Playwright

## 📝 实施步骤（Self-Hosted Runner）

### 步骤 1：准备服务器

选择之一：
- 家用电脑（Mac/Linux/Windows）
- VPS（Vultr, DigitalOcean, AWS EC2）
- 树莓派

### 步骤 2：安装 Runner

1. 进入 GitHub 仓库 Settings → Actions → Runners
2. 点击 "New self-hosted runner"
3. 选择操作系统
4. 按照指令安装：

```bash
# 下载
mkdir actions-runner && cd actions-runner
curl -o actions-runner-linux-x64-2.317.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.317.0/actions-runner-linux-x64-2.317.0.tar.gz

# 解压
tar xzf ./actions-runner-linux-x64-2.317.0.tar.gz

# 配置
./config.sh --url https://github.com/YOUR-USERNAME/scholarshipdb --token YOUR-TOKEN

# 运行
./run.sh

# 或作为服务运行（推荐）
sudo ./svc.sh install
sudo ./svc.sh start
```

### 步骤 3：修改 Workflow

```yaml
# .github/workflows/scrape.yml
jobs:
  scrape:
    runs-on: self-hosted  # 改为 self-hosted
```

### 步骤 4：安装依赖

在 runner 机器上：
```bash
# 安装 Python 和依赖
pip install -r requirements.txt
playwright install chromium
```

### 步骤 5：测试

手动触发 workflow，查看是否成功

## 📊 成本对比

| 方案 | 月成本 | 设置时间 | 成功率 | 维护成本 |
|------|--------|----------|--------|----------|
| **GitHub Actions（当前）** | $0 | 0分钟 | 0% ❌ | 无 |
| **Self-Hosted Runner** | $0-5 | 10分钟 | 95%+ ✅ | 低 |
| **ScraperAPI** | $49 | 5分钟 | 99%+ ✅ | 无 |
| **Bright Data** | $500+ | 30分钟 | 99.9%+ ✅ | 无 |
| **本地 Cron** | $0 | 5分钟 | 90%+ ✅ | 中 |

## 🎯 我的建议

### 最推荐：Self-Hosted Runner（家用电脑）

**理由**：
1. **免费** - 利用现有设备
2. **简单** - 10分钟设置
3. **可靠** - 95%+ 成功率
4. **灵活** - 完全控制

**适用场景**：
- 有一台 24/7 运行的电脑
- 愿意花 10 分钟设置
- 不想付费

### 次选：ScraperAPI

**理由**：
1. **省心** - 自动处理所有反爬虫
2. **稳定** - 99%+ 成功率
3. **专业** - 企业级服务

**适用场景**：
- 没有 24/7 运行的设备
- 愿意每月付费 $49
- 需要企业级可靠性

## ❓ 常见问题

### Q: 为什么本地运行没问题，GitHub Actions 就不行？

A: GitHub Actions 使用的是 Azure 数据中心 IP，这些 IP 被大量自动化工具使用，很容易被识别和封禁。而你的家庭/办公室 IP 看起来像正常用户。

### Q: 有没有完全免费的解决方案？

A: **Self-hosted runner** 使用现有设备是完全免费的。

### Q: 能否绕过 Cloudflare？

A: 可以，但需要：
1. 使用住宅代理（成本高）
2. 或使用 ScraperAPI 等服务（自动绕过）
3. 或使用 stealth 模式（效果有限）

### Q: 降低频率有用吗？

A: 有一定帮助，但 IP 封禁是主要问题。即使每天运行一次，GitHub IP 仍可能被封。

## 📚 参考资源

- [GitHub Self-Hosted Runners 文档](https://docs.github.com/en/actions/hosting-your-own-runners)
- [ScraperAPI 文档](https://www.scraperapi.com/documentation/)
- [Playwright 代理配置](https://playwright.dev/docs/network#http-proxy)
- [Playwright Stealth](https://github.com/AtuboDad/playwright_stealth)

## 🎉 总结

**当前问题**：GitHub Actions IP 被封 ❌

**最佳方案**：
1. 🏆 **短期**：Self-Hosted Runner（免费，10分钟）
2. 🥈 **中期**：ScraperAPI（$49/月，专业）
3. 🥉 **备选**：本地 Cron + 手动提交（免费，手动）

需要我帮你设置哪个方案？
