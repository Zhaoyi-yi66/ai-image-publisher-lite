# AI Image Publisher Lite

<p align="center">
  <img src="assets/app-icon.png" width="128" alt="AI Image Publisher Lite 图标">
</p>

<p align="center">
  一款轻量、离线、无需浏览器的 Windows 图片批处理工具。<br>
  面向 AI 生成图片和日常图片的多平台发布前处理。
</p>

## 直接下载

[下载 AIImagePublisherLite.exe（Windows 10/11 64 位）](https://github.com/Zhaoyi-yi66/ai-image-publisher-lite/releases/latest/download/AIImagePublisherLite.exe)

无需安装 Python。下载后双击 EXE 即可运行；如果 Windows 首次启动时显示安全提示，请核对文件来自本仓库 Release 页面后再决定是否运行。

## 项目简介

AI Image Publisher Lite 用于在图片发布到 Instagram、TikTok、YouTube、小红书或网站前，统一完成尺寸适配、格式转换、压缩和常见隐私元数据清理。

所有处理都在本地电脑完成，图片不会上传到任何服务器。程序采用 Python、Tkinter 和 Pillow 开发，可构建为单文件 Windows EXE，双击即可使用。

> 本工具用于格式、隐私和兼容性处理，不保证移除平台可检测的 AI/C2PA 信号，也不用于规避平台的 AI 内容标注要求。

## 软件能解决什么问题

AI 生成图片和相机图片通常存在尺寸过大、比例不适合平台、文件体积偏大、色彩空间不统一，以及携带 EXIF、GPS、相机型号等元数据的问题。如果需要同时发布到多个平台，逐张调整尺寸和格式会非常耗时。

AI Image Publisher Lite 把这些步骤集中到一个本地桌面界面中：拖入图片、选择目标平台和输出格式，程序即可批量生成适合发布的新图片，并保留原始文件不变。

适合以下使用场景：

- 将 AI 生成图片发布到小红书、Instagram、TikTok 或网站。
- 批量制作 YouTube 封面和不同尺寸的社交媒体配图。
- 上传前清理图片中的常见定位、相机和设备信息。
- 在不安装大型图片编辑软件的情况下完成快速压缩和格式转换。
- 同一批图片一次导出多种平台比例，减少重复操作。

## 处理流程

```text
拖入图片 → 自动旋转 → 转换 sRGB → 清理常见元数据
        → 保持原尺寸或适配平台尺寸 → 压缩/转换格式 → 导出新图片
```

## 主要特点

- **完全离线**：图片只在本机处理，不上传网络。
- **拖放导入**：可直接拖入单张、多张图片或整个图片文件夹。
- **原图优先**：默认保持原图尺寸和原文件格式。
- **任意尺寸**：可输入 16–20000 像素范围内的自定义宽度和高度。
- **多平台预设**：可同时选择多个尺寸，一次生成多套图片。
- **灵活裁剪**：可留白保留完整画面，或选择居中、上、下、左、右焦点裁切铺满。
- **格式转换**：支持 PNG、JPG/JPEG、WebP 互相转换。
- **压缩控制**：可调整 JPEG/WebP 质量及 PNG 压缩级别。
- **隐私处理**：重新构建纯像素图层，移除常见 EXIF、GPS、XMP、文本、相机和设备信息。
- **色彩兼容**：自动旋转图片并转换为 sRGB，减少不同平台显示差异。
- **静默完成**：处理结束只在界面显示状态，不播放系统提示音。
- **轻量界面**：窗口缩小时设置区域可滚动，避免内容遮挡。

## 支持格式

| 类型 | 导入 | 导出 |
| --- | :---: | :---: |
| PNG | ✅ | ✅ |
| JPG / JPEG | ✅ | ✅ |
| WebP | ✅ | ✅ |

默认选择“保持原格式”，每张图片会沿用自己的原后缀。只有主动选择 JPEG、WebP 或 PNG 时，程序才会转换输出格式和文件后缀。

## 平台尺寸预设

| 预设 | 输出尺寸 |
| --- | --- |
| 原图尺寸（默认） | 保持原宽高 |
| 自定义尺寸 | 宽高均可输入 16–20000 px |
| Instagram 竖版 | 1080 × 1350 |
| TikTok 竖版 | 1080 × 1920 |
| YouTube 封面 | 1280 × 720 |
| 小红书竖版 | 1080 × 1440 |
| Web | 长边最大 1600 px |

多个预设可以同时勾选。例如同时选择“小红书竖版”和“Instagram 竖版”，每张原图会分别生成两张适配图片。

## 留白与裁切

### 留白模式

- 保持完整画面，不截掉任何内容。
- 按比例缩放后居中放置到目标画布。
- 可自定义留白背景颜色。

### 裁切模式

- 按比例放大并铺满目标尺寸。
- 超出目标比例的边缘会居中裁切。
- 可指定居中、上方、下方、左侧或右侧为裁剪焦点。
- 适合需要满版封面或竖屏背景的场景。

## 导出规则

### 单张图片

- 自动保存到当前用户的桌面。
- 不再弹出目录选择窗口。
- 文件名增加 `_processed` 或平台尺寸标识，避免覆盖原图。
- 如果桌面已有同名文件，会自动增加数字后缀。

```text
photo.png → photo_processed.png
photo.png → photo_xiaohongshu_1080x1440.png
```

### 批量图片

- 由用户选择保存位置。
- 程序自动创建带时间的结果文件夹。
- 所有处理结果直接保存为普通图片，不生成 ZIP。

```text
AI图片处理结果_20260918_103000/
├── photo_1_processed.png
├── photo_2_processed.jpg
└── photo_3_instagram_1080x1350.webp
```

## 使用方法

1. 双击打开 `AIImagePublisherLite.exe`。
2. 把图片或图片文件夹直接拖入窗口，也可以点击“添加图片”。
3. 保持默认原图尺寸，或勾选平台尺寸、自定义宽高。
4. 选择留白或裁切模式；裁切时可指定焦点方向。
5. 保持原格式，或指定 JPEG、WebP、PNG 输出格式。
6. 点击“开始处理并导出”。
7. 在界面中查看完成状态，并可点击“打开结果位置”。

## 图片处理说明

程序会执行以下处理：

1. 根据 EXIF 方向信息自动旋转。
2. 尝试将嵌入 ICC 配置的图片转换为 sRGB。
3. 按选择的预设进行保持比例缩放、留白或裁切。
4. 使用 Pillow 重新编码图片。
5. 输出前重新构建纯像素图层，不带回原 EXIF、GPS、XMP、文本、相机型号等常见元数据。

重新编码和移除常见元数据不等于“消除 AI 痕迹”。平台仍可能通过内容凭证、上传信息、图像分析或其他机制识别 AI 内容。

## 从源代码运行

### 环境要求

- Windows 10 或 Windows 11
- Python 3.10 或更高版本
- Python 安装包含 Tcl/Tk 支持

### 安装与启动

```powershell
git clone https://github.com/Zhaoyi-yi66/ai-image-publisher-lite.git
cd ai-image-publisher-lite
python -m pip install -r requirements.txt
python app.py
```

## 构建 Windows EXE

双击 `build.bat`，或在命令行运行：

```powershell
.\build.bat
```

构建脚本会创建独立构建环境、安装依赖、嵌入程序图标，并在 `dist\AIImagePublisherLite.exe` 生成单文件程序。

## 运行测试

```powershell
python -m unittest discover -s tests -v
```

当前测试覆盖平台尺寸、原图默认行为、格式转换、透明图片、Web 长边限制、文件重名、文件夹拖入和界面默认选项。

## 项目结构

```text
ai-image-publisher-lite/
├── app.py                  # Tkinter 桌面界面与批处理流程
├── image_processor.py      # 图片旋转、色彩、缩放、编码逻辑
├── assets/                 # 程序图标
├── tests/                  # 单元测试
├── build.bat               # Windows 单文件构建脚本
├── requirements.txt        # 运行依赖
├── requirements-build.txt  # 构建依赖
└── LICENSE                 # MIT License
```

## 隐私与安全

- 不连接服务器，不上传图片。
- 不读取图片之外的个人文件。
- 不覆盖原始图片，始终生成新文件。
- 建议发布前仍根据目标平台要求检查内容和 AI 标注。

## 参与贡献

欢迎提交 Issue 和 Pull Request。提交代码前请运行完整测试，并尽量保持改动聚焦、界面简洁和依赖轻量。

## 开源许可证

本项目采用 [MIT License](LICENSE)。

