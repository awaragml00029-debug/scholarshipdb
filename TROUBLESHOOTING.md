# 快速修复指南

## 问题：ModuleNotFoundError: No module named 'loguru'

这个错误说明Python依赖包没有安装。

## 解决方案

### 方法1：使用快速安装脚本（推荐）

```bash
bash quick_install.sh
```

### 方法2：手动安装

```bash
# 安装Python依赖
pip install loguru beautifulsoup4 lxml pydantic pydantic-settings sqlalchemy playwright python-dotenv

# 安装Playwright浏览器
python -m playwright install chromium
```

### 方法3：使用requirements.txt

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## 验证安装

安装完成后，运行以下命令验证：

```bash
python -c "import loguru; print('✓ loguru installed')"
python -c "import playwright; print('✓ playwright installed')"
```

## 测试系统

```bash
# 测试模式
python main.py test

# 开始抓取
python main.py scrape
```

## 如果还有问题

### 1. 检查Python版本
```bash
python --version  # 需要 Python 3.8+
```

### 2. 使用Python3
某些系统上可能需要使用 `python3` 和 `pip3`：

```bash
pip3 install -r requirements.txt
python3 -m playwright install chromium
python3 main.py test
```

### 3. 使用虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
python -m playwright install chromium

# 运行
python main.py test
```

### 4. 权限问题

如果遇到权限问题，使用 `--user` 标志：

```bash
pip install --user -r requirements.txt
```

## 完整安装流程示例

```bash
# 进入项目目录
cd /scholar/scholarshipdb

# 安装所有依赖
pip install loguru beautifulsoup4 lxml pydantic pydantic-settings sqlalchemy playwright python-dotenv

# 安装Playwright浏览器
python -m playwright install chromium

# 验证安装
python -c "import loguru; import playwright; import sqlalchemy; print('所有依赖已安装')"

# 运行测试
python main.py test
```
