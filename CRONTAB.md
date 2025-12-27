# 定时任务配置指南

## Crontab 配置

使用 `crontab -e` 编辑定时任务，添加以下配置：

```bash
# PhD 奖学金抓取 - 每12小时运行一次
0 */12 * * * cd /root/scholar/scholarshipdb && /bin/bash run_scraper.sh >> /root/scholar/scraper.log 2>&1
```

**说明：**
- `0 */12 * * *` - 每12小时运行一次（0:00 和 12:00）
- `cd /root/scholar/scholarshipdb` - 切换到项目目录
- `/bin/bash run_scraper.sh` - 执行抓取脚本
- `>> /root/scholar/scraper.log 2>&1` - 将输出和错误记录到日志文件

## 其他时间选项

### 每天运行一次（凌晨2点）
```bash
0 2 * * * cd /root/scholar/scholarshipdb && /bin/bash run_scraper.sh >> /root/scholar/scraper.log 2>&1
```

### 每6小时运行一次
```bash
0 */6 * * * cd /root/scholar/scholarshipdb && /bin/bash run_scraper.sh >> /root/scholar/scraper.log 2>&1
```

### 每天早上8点和晚上8点
```bash
0 8,20 * * * cd /root/scholar/scholarshipdb && /bin/bash run_scraper.sh >> /root/scholar/scraper.log 2>&1
```

## 查看定时任务

```bash
# 查看当前用户的定时任务
crontab -l

# 查看 cron 服务状态
systemctl status cron

# 查看 cron 日志
tail -f /var/log/syslog | grep CRON
```

## 查看脚本执行日志

```bash
# 实时查看日志
tail -f /root/scholar/scraper.log

# 查看最近100行日志
tail -n 100 /root/scholar/scraper.log

# 查看日志中的错误
grep -i error /root/scholar/scraper.log
```

## 手动测试脚本

在设置定时任务之前，先手动测试脚本：

```bash
cd /root/scholar/scholarshipdb
bash run_scraper.sh
```

确保脚本能正常运行，没有错误。

## 环境要求

✅ 脚本已配置使用 `uv run` 来管理 Python 环境
✅ 无需手动激活虚拟环境
✅ 确保服务器已安装 `uv` 工具

## 故障排查

### 定时任务没有运行？

1. **检查 cron 服务是否运行：**
   ```bash
   systemctl status cron
   ```

2. **检查定时任务是否添加：**
   ```bash
   crontab -l
   ```

3. **查看系统日志：**
   ```bash
   tail -f /var/log/syslog | grep CRON
   ```

4. **检查脚本权限：**
   ```bash
   chmod +x /root/scholar/scholarshipdb/run_scraper.sh
   ```

### 脚本运行出错？

1. **手动运行查看错误：**
   ```bash
   cd /root/scholar/scholarshipdb
   bash run_scraper.sh
   ```

2. **查看详细日志：**
   ```bash
   tail -n 200 /root/scholar/scraper.log
   ```

3. **检查 uv 是否安装：**
   ```bash
   which uv
   uv --version
   ```

## 推送到远程仓库时的注意事项

如果 git push 被拒绝，执行：

```bash
cd /root/scholar/scholarshipdb
git pull --no-rebase
git push
```

或者在 `run_scraper.sh` 中将 push 改为：

```bash
git push || (git pull --no-rebase && git push)
```
