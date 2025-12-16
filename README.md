# 发票OCR识别工具

基于Dash框架开发的发票OCR识别工具，使用阿里云OCR服务自动识别发票图片中的关键信息。

## 🌟 功能特性
批量处理：支持批量上传多张发票图片（JPG/PNG格式）

自动识别：使用阿里云OCR服务识别发票关键信息

信息提取：自动提取销售方、购买方、金额、日期、开户行等关键信息

数据导出：支持Excel导出和表格复制功能

简洁界面：现代化UI设计，操作简单直观

状态管理：通过系统托盘提供方便的启动/停止控制

## 📋 系统要求
Python 3.8+

阿里云账号（用于OCR服务）

Windows/Linux/macOS


## 设置环境变量：

### windows
cmd

setx ALIBABA_CLOUD_ACCESS_KEY_ID "your-access-key-id"

setx ALIBABA_CLOUD_ACCESS_KEY_SECRET "your-access-key-secret"

重启计算机使环境变量生效

### Linux/macOS系统：

bash

编辑 ~/.bashrc 或 ~/.zshrc

export ALIBABA_CLOUD_ACCESS_KEY_ID="your-access-key-id"

export ALIBABA_CLOUD_ACCESS_KEY_SECRET="your-access-key-secret"


# 使配置生效
source ~/.bashrc
获取阿里云AK/SK：
登录阿里云控制台

访问RAM访问控制 > 用户管理

创建或选择现有用户

在"安全信息"标签页创建AccessKey

## 🚀 启动方式
方法一：通过托盘程序启动（推荐）
bash
python Tray_app.py
这种方式会在系统托盘中添加图标，便于管理和停止应用。

方法二：直接启动
bash
python GUI-4.py

启动后访问：http://localhost:8050

📁 项目结构
text

Range5-Dash-Invoice-OCR/

├── GUI-4.py              # 主应用程序

├── Tray_app.py           # 托盘启动器（推荐）

├── Ranch5.py             # OCR处理模块


├── README.md            # 说明文档



## 🖥️ 使用说明
### 1. 上传发票
点击上传区域或拖放图片文件

支持批量上传多张图片

支持格式：JPG、PNG

### 2. 自动识别
上传后自动开始OCR识别

显示每张发票的识别状态

失败时会显示错误信息

### 3. 查看结果
每张发票的预览卡片

关键信息高亮显示

汇总表格显示所有发票信息

### 4. 导出数据
复制表格：复制到剪贴板，可直接粘贴到Excel

下载Excel：下载完整的Excel文件

清空数据：清除所有已识别数据

## 🔒 环境变量配置参考
详细配置方法请参考阿里云官方文档：

在Linux、macOS和Windows系统配置环境变量

## ⚠️ 注意事项
OCR服务依赖：需要有效的阿里云OCR服务权限

图片质量：建议使用清晰、无反光的发票图片

网络连接：需要互联网连接以调用OCR API

隐私安全：发票图片会发送到阿里云OCR服务处理，请确保符合数据安全要求

## 🐛 故障排除
问题：OCR识别失败
检查阿里云AK/SK配置是否正确

确认网络连接正常

检查发票图片是否清晰

问题：托盘图标不显示
Windows：确保已安装必要的系统组件

Linux：检查系统托盘支持

macOS：可能需要额外的权限设置

问题：端口占用
如果8050端口被占用，可以修改启动端口：

在代码中修改

app.run(debug=True, port=8060)  # 修改端口号

## 📄本项目仅供学习和技术交流使用。

提示：为获得最佳体验，建议始终通过Tray_app.py启动应用，以便在系统托盘中管理应用生命周期。
