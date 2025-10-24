# Chrome Profile 爬虫使用指引

## 🎯 目标
在其他机器上快速部署和使用Chrome Profile爬虫，实现"一次登录，永久使用"的效果。

---

## 📋 环境准备

### 1. 系统要求
- Windows 10/11
- Python 3.7+
- Chrome浏览器

### 2. 安装依赖
```bash
pip install selenium
```

---

## 🔧 Chrome Profile 创建和配置

### 方法一：在Chrome中创建Profile（推荐）

#### 步骤1：打开Chrome浏览器
双击桌面Chrome图标

#### 步骤2：创建新Profile
1. 点击Chrome右上角的**头像图标**（或空白头像）
2. 点击**"添加"**按钮
3. 选择**"创建新的配置文件"**
4. 输入名称：`CrawlerProfile`（**必须用这个名字**）
5. 点击**"完成"**

#### 步骤3：验证Profile创建
- Chrome会自动打开新窗口
- 右上角应该显示 `CrawlerProfile` 头像
- 地址栏输入 `chrome://version` 查看个人资料路径

### 方法二：使用命令行创建

```powershell
# 创建Profile目录
mkdir "C:\Users\%USERNAME%\AppData\Local\Google\Chrome\User Data\CrawlerProfile"

# 使用新Profile启动Chrome
"C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="C:\Users\%USERNAME%\AppData\Local\Google\Chrome\User Data" --profile-directory="CrawlerProfile"
```

---

## 🚀 项目部署

### 方法一：Git Clone（推荐）

```bash
git clone <你的仓库地址>
cd profile_crawler
```

### 方法二：手动复制

将以下文件复制到目标机器：
```
项目目录/
├── crawler.py           # 主爬虫脚本
├── config.json          # 配置文件（已配置好目标网站）
└── open_chrome.bat      # Chrome启动脚本
```

### 配置文件说明

`config.json` 已配置好目标网站，无需修改：
```json
{
  "target_url": "https://cmcr.yiigle.com/index",
  "headless": false,
  "wait_time": 3,
  "page_load_timeout": 60,
  "implicit_wait": 2,
  "output_directory": "./output",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
```

### 重要说明

- ✅ **chrome_profile目录会自动创建**，无需手动创建
- ✅ **首次运行会自动检测**Chrome中的CrawlerProfile
- ✅ **如果存在会复制**，不存在会提示手动登录
- ❌ **不要推送chrome_profile到Git**（包含敏感信息）

---

## 🔐 登录设置（关键步骤）

### 第一次使用：自动检测 + 手动登录

#### 步骤1：运行爬虫脚本（自动检测）
```bash
python crawler.py
```

脚本会自动：
- ✅ 检测Chrome中是否存在CrawlerProfile
- ✅ 如果存在，自动复制到项目目录
- ✅ 如果不存在，提示手动登录

#### 步骤2：手动登录（如果需要）
如果提示需要手动登录：
1. **双击运行** `open_chrome.bat`
2. Chrome会使用项目目录下的独立Profile打开
3. 访问目标网站：https://cmcr.yiigle.com/index
4. 点击右上角的"登录"
5. 完成登录流程（输入账号密码、验证码等）
6. 确认登录成功
7. **关闭Chrome**

#### 步骤3：重新运行爬虫
```bash
python crawler.py
```

现在会自动使用保存的登录状态！

### 验证Profile路径

在Chrome地址栏输入 `chrome://version`，个人资料路径应该是：
```
D:\你的项目路径\chrome_profile\CrawlerProfile
```

**不是**Chrome默认路径：
```
C:\Users\用户名\AppData\Local\Google\Chrome\User Data\CrawlerProfile
```

---

## 🎯 运行爬虫

### 基本运行
```bash
python crawler.py
```

### 运行流程
1. ✅ 自动检测Profile目录
2. ✅ 启动Chrome浏览器（使用项目Profile）
3. ✅ 访问目标网站
4. ✅ 自动点击登录按钮
5. ✅ 使用保存的登录状态完成登录
6. ✅ 保存页面截图和HTML到 `output/` 目录

---

## 🔧 故障排除

### 问题1：Chrome启动失败
**错误信息**：`DevToolsActivePort file doesn't exist`

**解决步骤**：
1. 关闭所有Chrome窗口
2. 运行命令强制关闭Chrome进程：
   ```powershell
   taskkill /F /IM chrome.exe /T
   ```
3. 等待5秒后重新运行 `python crawler.py`

### 问题2：找不到登录按钮
**错误信息**：`未找到登录按钮`

**解决步骤**：
1. 手动运行 `open_chrome.bat`
2. 在打开的Chrome中确认登录状态
3. 如果未登录，重新完成登录流程
4. 关闭Chrome后重新运行爬虫

### 问题3：Profile路径错误
**检查方法**：
1. 运行 `open_chrome.bat`
2. 在Chrome地址栏输入 `chrome://version`
3. 确认个人资料路径包含 `chrome_profile\CrawlerProfile`

### 问题4：登录状态丢失
**解决步骤**：
1. 重新运行 `open_chrome.bat`
2. 在打开的Chrome中重新登录目标网站
3. 关闭Chrome
4. 运行 `python crawler.py`

---

## 📁 文件结构说明

### 项目文件
```
项目目录/
├── crawler.py              # 主爬虫脚本
├── config.json             # 配置文件
├── open_chrome.bat         # Chrome启动脚本
├── chrome_profile/         # Profile目录（自动创建）
│   └── CrawlerProfile/     # 专用Profile
└── output/                 # 输出目录（自动创建）
    ├── page_*.png          # 页面截图
    └── page_*.html         # 页面HTML
```

### Profile目录内容（清理后）
```
CrawlerProfile/
├── Preferences             # 用户设置
├── Login Data              # 登录数据
├── Cookies                 # Cookie信息
├── Web Data                # 网页数据
├── History                 # 浏览历史
├── Local Storage/          # 本地存储
├── Session Storage/        # 会话存储
└── Network/                # 网络数据
```

---

## ⚡ 快速操作指南

### Git部署（2步）
1. **Git Clone** → `git clone <仓库地址>`
2. **运行爬虫** → `python crawler.py`（自动检测Profile）

### 首次使用（3步）
1. **运行脚本** → `python crawler.py`
2. **手动登录** → 双击 `open_chrome.bat` 完成登录（如果需要）
3. **重新运行** → `python crawler.py`

### 日常使用（1步）
```bash
python crawler.py
```

### 重新登录（2步）
1. 双击 `open_chrome.bat`
2. 重新登录后关闭Chrome

---

## 🎯 关键要点

### ✅ 必须记住
- **Profile名称**：必须是 `CrawlerProfile`
- **首次使用**：必须手动登录一次
- **Profile路径**：使用项目目录下的独立Profile
- **Chrome进程**：运行前确保没有Chrome进程冲突

### ❌ 常见错误
- 使用Chrome默认Profile（会冲突）
- 忘记手动登录（脚本无法自动登录）
- Profile名称错误（找不到Profile）
- 同时运行多个爬虫实例（会冲突）

---

## 📞 快速参考

| 操作 | 命令/文件 |
|------|-----------|
| 手动登录 | 双击 `open_chrome.bat` |
| 运行爬虫 | `python crawler.py` |
| 强制关闭Chrome | `taskkill /F /IM chrome.exe /T` |
| 检查Profile路径 | Chrome输入 `chrome://version` |
| 查看输出文件 | `output/` 目录 |

---

**版本**: v1.0  
**适用**: Windows + Chrome + Python  
**更新**: 2025-10-24
