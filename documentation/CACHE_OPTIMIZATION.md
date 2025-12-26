# GitHub Actions 缓存优化 🚀

## 📊 优化效果

### 优化前
- ⏱️ 总运行时间：**8-12分钟**
- 下载 Playwright 浏览器：~3分钟
- 安装 Python 依赖：~2分钟
- 实际抓取时间：~3-7分钟

### 优化后
- ⏱️ 总运行时间：**3-7分钟** (节省 50-60%)
- 下载 Playwright 浏览器：**跳过** (使用缓存)
- 安装 Python 依赖：**<30秒** (使用缓存)
- 实际抓取时间：~3-7分钟

## 🔧 实施的缓存策略

### 1. **Python 依赖缓存**
```yaml
- name: Setup Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.11'
    cache: 'pip'
    cache-dependency-path: 'requirements.txt'
```

**效果**：
- 缓存 pip 下载的包
- 基于 `requirements.txt` 的哈希值
- 首次运行：安装所有依赖（~2分钟）
- 后续运行：使用缓存（~10秒）

### 2. **UV 缓存**
```yaml
- name: Cache UV
  uses: actions/cache@v4
  with:
    path: ~/.cache/uv
    key: ${{ runner.os }}-uv-${{ hashFiles('requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-uv-
```

**效果**：
- 缓存 UV 的包管理缓存
- 加速依赖安装
- 节省带宽

### 3. **Playwright 浏览器缓存** ⭐ 最重要
```yaml
- name: Cache Playwright browsers
  uses: actions/cache@v4
  id: playwright-cache
  with:
    path: ~/.cache/ms-playwright
    key: ${{ runner.os }}-playwright-${{ hashFiles('requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-playwright-
```

**效果**：
- 缓存 Chromium 浏览器（~170MB）
- 首次运行：下载浏览器（~3分钟）
- 后续运行：跳过下载（~5秒）
- **节省 80-90% 的安装时间**

### 4. **智能安装策略**
```yaml
# 只在缓存未命中时下载浏览器
- name: Install Playwright browsers
  if: steps.playwright-cache.outputs.cache-hit != 'true'
  run: |
    playwright install --with-deps chromium

# 缓存命中时只安装系统依赖
- name: Install Playwright system dependencies (if cached)
  if: steps.playwright-cache.outputs.cache-hit == 'true'
  run: |
    playwright install-deps chromium
```

**效果**：
- 缓存命中：跳过浏览器下载，只安装系统依赖
- 缓存未命中：完整安装浏览器和依赖

## 📈 缓存生命周期

### 缓存键策略

1. **主键（Primary Key）**：
   ```
   ${{ runner.os }}-playwright-${{ hashFiles('requirements.txt') }}
   ```
   - 基于操作系统和 requirements.txt 内容
   - 更新依赖时自动失效，重新下载

2. **恢复键（Restore Keys）**：
   ```
   ${{ runner.os }}-playwright-
   ```
   - 如果主键不匹配，尝试使用相似的缓存
   - 提高缓存命中率

### 缓存失效条件

缓存会在以下情况失效：
- ✅ `requirements.txt` 文件内容改变
- ✅ 7天未使用（GitHub Actions 自动清理）
- ✅ 缓存总大小超过 10GB（GitHub 限制）

### 缓存保留

- GitHub Actions 保留缓存**最多 7 天**
- 每 6 小时运行一次，缓存始终保持新鲜
- 不用担心过期

## 🎯 性能对比

### 首次运行（冷启动）
```
1. Checkout                           20s
2. Setup Python + cache restore       30s
3. Install UV                         15s
4. Install dependencies              120s  ← 下载所有包
5. Install Playwright browsers       180s  ← 下载 Chromium
6. Run scraper                       240s
7. Commit and deploy                  30s
-------------------------------------------
总计：                               ~10分钟
```

### 后续运行（缓存命中）
```
1. Checkout                           20s
2. Setup Python + cache restore       30s  ← 命中缓存
3. Restore UV cache                    5s  ← 命中缓存
4. Install dependencies               20s  ← 使用缓存
5. Restore Playwright cache            5s  ← 命中缓存
6. Install Playwright deps             5s  ← 只装系统依赖
7. Run scraper                       240s
8. Commit and deploy                  30s
-------------------------------------------
总计：                                ~5分钟

节省时间：50% ⬇️
```

## 💡 最佳实践

### 1. 保持 requirements.txt 稳定
- 不要频繁更改依赖版本
- 变更依赖会导致缓存失效

### 2. 使用固定版本号
```txt
# ✅ 好的做法
playwright==1.48.0
pyyaml==6.0.1

# ❌ 避免使用
playwright>=1.40.0
pyyaml~=6.0
```

### 3. 监控缓存效果
在 GitHub Actions 运行日志中查看：
```
Run actions/cache@v4
  Cache hit: true  ← 表示缓存命中
```

### 4. 定期清理
GitHub Actions 会自动管理，无需手动清理

## 🔍 故障排除

### 问题1：缓存未命中
**症状**：每次都下载浏览器

**解决**：
1. 检查 `requirements.txt` 是否频繁变化
2. 查看 Actions 日志中的缓存键
3. 确认缓存路径正确

### 问题2：缓存过大
**症状**：缓存存储超出限制

**解决**：
- GitHub 免费版限制 10GB 缓存
- 当前配置约占用 500MB
- 无需担心超出

### 问题3：依赖安装失败
**症状**：即使有缓存也失败

**解决**：
```bash
# 强制重新安装
git commit --allow-empty -m "Clear cache"
git push
```

## 📊 资源使用统计

### 缓存大小估算
```
Python pip 缓存:          ~100MB
UV 缓存:                  ~50MB
Playwright Chromium:      ~170MB
系统依赖:                 ~100MB
-----------------------------------
总计:                     ~420MB
```

### GitHub Actions 配额
- **免费版**：2,000 分钟/月
- **优化前**：每次 10 分钟 → 200 次运行/月
- **优化后**：每次 5 分钟 → **400 次运行/月** ⬆️

每天运行 4 次（每 6 小时），每月约 120 次运行，完全够用！

## 🎉 总结

通过实施三层缓存策略：
1. ✅ **减少 50% 运行时间**
2. ✅ **节省 50% GitHub Actions 配额**
3. ✅ **提高系统响应速度**
4. ✅ **降低网络带宽消耗**
5. ✅ **零额外成本**

缓存策略让自动化系统更高效、更稳定！
