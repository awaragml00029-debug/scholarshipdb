# Botasaurus 集成指南 🦖

## 🎯 Botasaurus 能解决问题吗？

### ✅ 能解决的问题

1. **Cloudflare 检测** - 内置 `bypass_cloudflare=True`
2. **浏览器指纹识别** - 更"人性化"的自动化
3. **JavaScript 挑战** - 自动处理

### ⚠️ 仍无法解决的问题

1. **GitHub Actions IP 封禁** - IP 问题需要其他方案
2. **大规模抓取限制** - 频率限制仍然存在

### 🎯 最佳使用场景

**Botasaurus + Self-Hosted Runner = 完美组合**

- Botasaurus 绕过 Cloudflare
- Self-Hosted Runner 使用你的 IP
- 成功率 99%+

---

## 📦 快速测试

### 1. 安装 Botasaurus

```bash
# 使用 pip
pip install botasaurus

# 或使用 uv
uv pip install --system botasaurus
```

### 2. 测试单个 URL

```bash
python scraper_botasaurus.py
```

**预期结果**：
- 成功绕过 Cloudflare
- 抓取 cancer research 的前 2 页
- 生成 `botasaurus_test.json`

### 3. 批量测试

```bash
python batch_scrape_botasaurus.py urls_test.yaml
```

---

## 📁 新增文件说明

### 1. `scraper_botasaurus.py`

Botasaurus 版本的抓取器，主要区别：

```python
# Playwright 版本
async with ScholarshipScraperV2() as scraper:
    scholarships = await scraper.scrape_url(url)

# Botasaurus 版本
@browser(bypass_cloudflare=True)
def scrape_scholarship_page(driver, url, max_pages):
    driver.get(url)
    # ... 抓取逻辑
```

**特性**：
- ✅ Cloudflare 绕过
- ✅ 相同的解析逻辑
- ✅ 支持分页
- ✅ JSON 导出

### 2. `batch_scrape_botasaurus.py`

批量抓取脚本，使用 Botasaurus：

```bash
# 使用方法
python batch_scrape_botasaurus.py         # 使用默认 urls.yaml
python batch_scrape_botasaurus.py custom.yaml  # 使用自定义配置
```

---

## 🔬 本地测试步骤

```bash
# 步骤 1：安装
uv pip install --system botasaurus

# 步骤 2：测试单 URL
python scraper_botasaurus.py

# 步骤 3：检查结果
cat botasaurus_test.json | jq '.[0]'

# 步骤 4：批量测试
python batch_scrape_botasaurus.py urls_test.yaml

# 步骤 5：查看数据
ls -lh data/
```

---

## ⚖️ 对比：Playwright vs Botasaurus

| 特性 | Playwright | Botasaurus |
|------|------------|------------|
| **Cloudflare 绕过** | ❌ 容易被检测 | ✅ 专门设计 |
| **反爬虫对抗** | ⚠️ 需要额外配置 | ✅ 内置 |
| **速度** | ⚡ 快 | ⚡ 中等 |
| **稳定性** | ✅ 高 | ⚠️ 新项目 |
| **文档** | ✅ 完善 | ⚠️ 一般 |
| **学习曲线** | 中等 | 简单 |

---

## 💡 推荐使用策略

### 方案 1：本地测试 Botasaurus 效果

```bash
# 1. 先用 Botasaurus 本地测试
python scraper_botasaurus.py

# 2. 如果成功，说明 Cloudflare 绕过有效
# 3. 再考虑部署方案
```

### 方案 2：Botasaurus + Self-Hosted Runner

```yaml
# .github/workflows/scrape_botasaurus.yml
jobs:
  scrape:
    runs-on: self-hosted  # 使用你的电脑

    steps:
      - name: Install Botasaurus
        run: pip install botasaurus

      - name: Run scraper
        run: python batch_scrape_botasaurus.py
```

### 方案 3：继续使用 Playwright + Runner

如果 Botasaurus 效果不明显，Self-Hosted Runner 可能已经足够。

---

## 🚨 重要提示

### 1. IP 问题仍需解决

**Botasaurus 能绕过 Cloudflare ≠ 能绕过 IP 封禁**

即使成功绕过检测，GitHub Actions IP 仍可能被封。

**解决方案**：
- Self-Hosted Runner（推荐）
- 代理服务
- 本地运行

### 2. 浏览器下载

首次运行会下载 Chrome（~150MB），需要几分钟。

### 3. GitHub Actions 中使用

需要缓存浏览器：

```yaml
- name: Cache Botasaurus
  uses: actions/cache@v4
  with:
    path: ~/.botasaurus
    key: botasaurus-chrome
```

---

## 📊 测试结果预期

### 成功的标志

```
✓ Successfully loaded URL
✓ Found 20 scholarships on page 1
✓ Scraped 40 scholarships
✓ Exported to botasaurus_test.json
```

### 如果仍然失败

可能原因：
1. **IP 被封** - 使用 Self-Hosted Runner
2. **网络问题** - 检查网络连接
3. **网站更新** - 检查 HTML 结构

---

## 🎯 下一步行动

### 立即测试（5 分钟）

```bash
uv pip install --system botasaurus
python scraper_botasaurus.py
```

**如果成功**：
→ 说明 Cloudflare 绕过有效
→ 配合 Self-Hosted Runner 使用

**如果失败**：
→ 可能是 IP 问题
→ 直接使用 Self-Hosted Runner 即可

---

## 📚 参考资源

- [Botasaurus GitHub](https://github.com/omkarcloud/botasaurus)
- [Cloudflare 绕过文档](https://github.com/omkarcloud/botasaurus#bypassing-cloudflare)
- [Self-Hosted Runner 设置](IP_BLOCKING_ISSUE.md)

---

需要帮助测试或有问题随时问！🦖
