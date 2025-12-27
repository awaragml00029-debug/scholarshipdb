# Docker 部署指南

使用 Docker 运行 PhD 奖学金爬虫，简化部署和环境配置。

## 快速开始

### 1. 使用 Docker Compose（推荐）

```bash
# 启动容器（后台运行，每12小时自动抓取）
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止容器
docker-compose down
```

### 2. 手动运行一次

```bash
# 运行单次抓取并退出
docker-compose run --rm scraper-once
```

### 3. 使用 Docker 命令

```bash
# 构建镜像
docker build -t scholarship-scraper .

# 运行容器
docker run -d \
  --name scholarship-scraper \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/docs:/app/docs \
  -v $(pwd)/urls.yaml:/app/urls.yaml:ro \
  -v $(pwd)/credentials.json:/app/credentials.json:ro \
  scholarship-scraper
```

## 配置说明

### 环境变量

在 `docker-compose.yml` 中配置：

```yaml
environment:
  # 抓取间隔（秒），默认 43200 = 12小时
  - SCRAPE_INTERVAL=43200

  # 无头模式（推荐保持 true）
  - SCRAPER_HEADLESS=true

  # 时区
  - TZ=Asia/Shanghai  # 或其他时区
```

### 代理配置

**方法1：编辑 urls.yaml**

```yaml
config:
  use_proxy: true
  proxy_pool:
    - "socks5://your-proxy:1080"
```

**方法2：使用宿主机代理**

```yaml
# docker-compose.yml
services:
  scraper:
    network_mode: host  # 使用宿主机网络
```

### 数据持久化

默认挂载的卷：
- `./data` → 抓取结果
- `./docs` → GitHub Pages 静态文件
- `./urls.yaml` → 配置文件（只读）

## 常用命令

### 查看日志

```bash
# 实时查看日志
docker-compose logs -f scraper

# 查看最近100行
docker-compose logs --tail=100 scraper
```

### 进入容器

```bash
# 进入运行中的容器
docker-compose exec scraper bash

# 或使用 docker 命令
docker exec -it scholarship-scraper bash
```

### 手动触发抓取

```bash
# 在容器内执行
docker-compose exec scraper python batch_scrape.py
```

### 更新配置

```bash
# 1. 修改 urls.yaml
# 2. 重启容器
docker-compose restart scraper
```

### 重新构建

```bash
# 修改代码后重新构建
docker-compose build

# 强制重新构建（不使用缓存）
docker-compose build --no-cache

# 重新构建并启动
docker-compose up -d --build
```

## 定时任务

### 选项1：Docker 内置循环（默认）

容器内自动循环运行，间隔由 `SCRAPE_INTERVAL` 控制。

### 选项2：外部 Cron 调用

```bash
# 禁用容器内循环，使用外部 cron
# docker-compose.yml
command: python batch_scrape.py  # 单次运行

# 宿主机 crontab
0 */12 * * * docker-compose run --rm scraper-once
```

### 选项3：Kubernetes CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: scholarship-scraper
spec:
  schedule: "0 */12 * * *"  # 每12小时
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: scraper
            image: scholarship-scraper:latest
            command: ["python", "batch_scrape.py"]
          restartPolicy: OnFailure
```

## Git 集成（可选）

如果需要自动提交和推送：

```bash
# 挂载 .git 目录
volumes:
  - ./.git:/app/.git

# 配置 git credentials
docker-compose exec scraper git config --global user.email "bot@example.com"
docker-compose exec scraper git config --global user.name "Bot"

# 配置 GitHub token（如果需要 push）
docker-compose exec scraper git config --global credential.helper store
# 然后手动 git push 一次输入 token
```

## 资源限制

在 `docker-compose.yml` 中配置：

```yaml
deploy:
  resources:
    limits:
      cpus: '2'        # 最大 2 核
      memory: 2G       # 最大 2GB 内存
    reservations:
      cpus: '0.5'      # 保留 0.5 核
      memory: 512M     # 保留 512MB
```

## 监控和告警

### 健康检查

```bash
# 查看健康状态
docker inspect --format='{{.State.Health.Status}}' scholarship-scraper
```

### 日志监控

```bash
# 使用 logrotate 管理日志
# docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

## 故障排查

### 容器无法启动

```bash
# 查看详细错误
docker-compose logs scraper

# 检查容器状态
docker-compose ps
```

### Playwright 浏览器问题

```bash
# 重新安装浏览器
docker-compose exec scraper playwright install chromium
docker-compose exec scraper playwright install-deps chromium
```

### 内存不足

```bash
# 增加内存限制
# docker-compose.yml
deploy:
  resources:
    limits:
      memory: 4G  # 增加到 4GB
```

### 代理连接失败

```bash
# 测试代理连接
docker-compose exec scraper curl -x socks5://proxy:1080 https://scholarshipdb.net

# 查看代理日志
docker-compose logs -f scraper | grep -i proxy
```

## 生产部署建议

1. **使用环境变量**：敏感信息不要硬编码
2. **启用日志轮转**：防止日志文件过大
3. **设置资源限制**：避免占用过多资源
4. **配置重启策略**：`restart: unless-stopped`
5. **定期备份数据**：备份 `data/` 目录
6. **监控容器状态**：使用 Prometheus + Grafana

## 卸载

```bash
# 停止并删除容器
docker-compose down

# 删除镜像
docker rmi scholarship-scraper

# 清理所有未使用的资源
docker system prune -a
```
