# Git 使用指南

## 📦 当前仓库状态

已成功创建 Git 仓库并完成初始提交：
- ✅ 29 个文件已提交
- ✅ README.md 已更新为最新文档
- ✅ .gitignore 已配置（排除敏感文件）

## 🚀 推送到远程仓库

### 方法一：推送到 GitHub

1. **创建 GitHub 仓库**
   - 访问 https://github.com/new
   - 仓库名称：`ethusdt-quantitative-system`
   - 描述：`ETHUSDT 机构级量化巡航系统`
   - 选择 Public 或 Private
   - **不要**勾选 "Initialize with README"

2. **添加远程仓库**
```bash
git remote add origin https://github.com/你的用户名/ethusdt-quantitative-system.git
```

3. **推送代码**
```bash
git push -u origin master
```

### 方法二：推送到 Gitee（国内推荐）

1. **创建 Gitee 仓库**
   - 访问 https://gitee.com/projects/new
   - 仓库名称：`ethusdt-quantitative-system`
   - **不要**勾选 "初始化仓库"

2. **添加远程仓库**
```bash
git remote add origin https://gitee.com/你的用户名/ethusdt-quantitative-system.git
```

3. **推送代码**
```bash
git push -u origin master
```

### 方法三：使用 SSH（推荐）

1. **生成 SSH 密钥**
```bash
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

2. **查看公钥**
```bash
cat ~/.ssh/id_rsa.pub
```

3. **添加到 GitHub/Gitee**
   - GitHub: Settings -> SSH and GPG keys -> New SSH key
   - Gitee: 设置 -> SSH 公钥 -> 添加公钥

4. **使用 SSH 地址**
```bash
git remote add origin git@github.com:你的用户名/ethusdt-quantitative-system.git
git push -u origin master
```

## 🔐 安全提示

### ⚠️ 重要：API Key 安全

`.streamlit/secrets.toml` 文件已被 `.gitignore` 排除，**不会**被提交到仓库。

如果已经推送了包含 API Key 的文件，请立即：
1. 删除远程仓库
2. 修改 API Key
3. 重新创建仓库

### 使用环境变量（推荐）

创建 `.env` 文件（已忽略）：
```
COINEX_ACCESS_ID=your_access_id
COINEX_SECRET_KEY=your_secret_key
```

在应用中读取：
```python
import os
access_id = os.getenv('COINEX_ACCESS_ID')
secret_key = os.getenv('COINEX_SECRET_KEY')
```

## 📝 常用 Git 命令

### 查看状态
```bash
git status              # 查看当前状态
git log --oneline       # 查看提交历史
git remote -v           # 查看远程仓库
```

### 日常操作
```bash
git add .               # 添加所有更改
git commit -m "更新说明" # 提交更改
git push                # 推送到远程
git pull                # 拉取远程更新
```

### 分支操作
```bash
git branch              # 查看分支
git branch dev          # 创建 dev 分支
git checkout dev        # 切换到 dev 分支
git merge dev           # 合并 dev 分支到当前分支
```

### 撤销操作
```bash
git checkout -- <file>  # 撤销文件修改
git reset HEAD <file>   # 取消暂存
git reset --hard HEAD^  # 撤销最近一次提交
```

## 🔄 版本管理建议

### 提交信息规范
```
feat: 新功能
fix: 修复 bug
docs: 文档更新
style: 代码格式调整
refactor: 代码重构
test: 测试相关
chore: 构建/工具相关
```

### 分支策略
```
master   - 稳定版本
dev      - 开发分支
feature  - 新功能分支
hotfix   - 紧急修复分支
```

## 📊 项目统计

当前提交包含：
- Python 文件：15 个
- 文档文件：4 个
- 配置文件：3 个
- 脚本文件：7 个

总计：29 个文件，5349 行代码

---

**仓库已就绪！选择一个平台推送即可。** 🎉
