> 本文档是英文 README 的翻译。如需最新信息，请参阅 [English README](README.md)。

# ArtSmoker
> *对你的艺术作品进行冒烟测试！*

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green?logo=fastapi&logoColor=white)
![Amazon Bedrock](https://img.shields.io/badge/Amazon-Bedrock-orange?logo=amazonaws&logoColor=white)
![License](https://img.shields.io/badge/License-MIT--0-yellow)

## 📌 0. 概述

为 Amazon Bedrock 的图像和视频生成模型提供的简洁、艺术家友好的界面。ArtSmoker 帮助创意团队高效使用 Bedrock——无需学习 API、CLI 或提示词工程。

### 📝 问题

创意团队和游戏工作室希望利用 AI 进行资产生成，但面临诸多障碍：

- **缺乏简单的界面** —— 艺术家不应该需要登录 Bedrock 控制台或编写 API 调用来生成图像
- **提示词工程很难** —— 编写包含恰当负面提示词、风格指令和模型特定格式的有效提示词需要大多数艺术家不具备的专业知识
- **团队不会自己构建/训练模型** —— 他们需要通过可用的工具访问 Bedrock 上已有的众多模型
- **图像编辑难以使用** —— 局部重绘、扩展绘制、搜索替换和风格迁移都需要 API 知识
- **2D 到 3D 是独立的流程** —— 将 2D 概念转换为游戏引擎可用的带纹理 3D 模型，通常需要手动建模、UV 展开和纹理绘制 —— 或者昂贵的第三方工具

### 📝 解决方案

ArtSmoker 是一个自托管的 Web 应用程序，以简洁的创意界面封装 Amazon Bedrock。专为游戏资产制作而构建，同时适用于广告、电子商务、出版和数字媒体等其他 AI 生成视觉内容有价值的创意行业。

- **艺术家只需用自然语言描述需求** —— ArtSmoker 在幕后处理提示词分解、增强、模型特定优化和风格应用。引导式 Prompt Designer 让用户通过锁定/变化控制微调各个视觉元素（主体、场景、光照、颜色），生成真正不同的创意选项
- **风格感知生成** —— 上传您游戏的现有美术作品，ArtSmoker 的视觉模型会学习您的视觉标识。每个生成的资产都会匹配您游戏的外观和风格
- **所有 Bedrock 模型，所有区域** —— 完全可配置。选择您的文生图模型、视频模型和区域。系统通过 Bedrock API 动态发现可用模型
- **自托管开源模型 —— 一键部署** —— 浏览精选的预测试模型目录（HunyuanImage 3.0、FLUX.2 等），选择 GPU 实例，一键部署到 Amazon SageMaker。一切均已处理：推理打包、量化、CUDA 配置、自动缩放和任务跟踪。目录中的每个模型在发布前均已端到端验证
- **一键图像转 3D** —— 从任意 2D 游戏资产或角色图像直接生成带纹理的 3D 模型（GLB）。多视图合成和纹理烘焙生成可直接导入 Unity、Unreal 或 Blender 的游戏引擎可用网格 —— 无需手动建模
- **您的 AWS 账户，您的 IP** —— 一切运行在您自己的私有 AWS 账户中。所有作品、提示词、风格和生成的资产都保留在您的隔离环境内 —— 没有数据流向第三方服务。您对自己的创意 IP 拥有完全的所有权和控制权

**Amazon Bedrock 模型**：Claude Sonnet/Opus（提示词工程和聊天）、Nova Canvas、Titan Image、Stable Diffusion 3.5 Large、Stable Image Ultra、Stability AI 服务（图像编辑）、Nova Reel、Luma AI Ray（视频生成），以及 Chat Studio 可用的来自 16 个供应商的 80 多个 LLM。**自托管模型**：HunyuanImage 3.0（BF16/NF4）、FLUX.2、FLUX.1、TripoSG 等，通过 Amazon SageMaker —— 附带可扩展目录以添加新模型。

**[立即开始 —— 跳转至前置条件和安装 ▸](#get-started)**

### Language / 言語 / 语言 / 언어 / हिन्दी / Язык / Langue / Idioma

ArtSmoker 支持 8 种语言。通过顶部导航栏的语言按钮（EN | 日 | 中 | 한 | हिं | РУ | FR | ES）切换 UI 语言。您的选择会自动保存。

| 语言 | README |
|------|--------|
| English | [README.md](README.md) |
| 日本語 (Japanese) | [README.ja.md](README.ja.md) |
| 中文 | 本文档 |
| 한국어 (Korean) | [README.ko.md](README.ko.md) |
| हिन्दी (Hindi) | [README.hi.md](README.hi.md) |
| Русский (Russian) | [README.ru.md](README.ru.md) |
| Français (French) | [README.fr.md](README.fr.md) |
| Español (Spanish) | [README.es.md](README.es.md) |

**多语言提示词支持：**
- 非英语提示词（日语、中文、韩语、印地语、俄语、法语、西班牙语等）会被自动检测，并在生成前翻译为英语
- 提示词区域会显示双语预览：可在原始文本和英语翻译之间切换，查看模型将接收的确切内容
- 原始提示词、检测到的语言和英语翻译都会保存在资产元数据中
- 文件名由翻译后的英语提示词生成（例如："病院の建物" → `hospital-building_opt1_var1.png`）
- Chat Studio 将提示词直接传递给 LLM（不翻译）——因为 Claude 等模型原生支持多语言
- Type Studio 中的文本保持您的语言不变（会按原样渲染到图像上）
- 所有审核预检和内容筛查都基于翻译后的英语提示词执行，以确保一致性

## 📌 1. 功能概览

ArtSmoker 以两种模式运行 —— **独立模式**（无需设置艺术风格或主题，直接描述并生成）和**风格引导模式**（上传您的现有美术作品，所有生成都匹配您的视觉标识）。两种模式使用相同的工作室和生成管线。

### 📝 独立模式（快速开始）

无需风格或主题设置 —— 打开 2D Image Studio、Video Studio 或 Type Studio 即可立即开始创作。

1. **描述您的需求** —— 输入如 "hospital building" 或 "fire mage character" 的提示词，或使用语音输入。AI 将您的想法分解为视觉组件，使用模型特定的优化进行增强，并通过智能锁定/变化控制尊重您的创意意图。支持任何语言输入 —— 非英语提示词会自动翻译。
2. **选择模型和设置** —— 从所有可用的文生图模型（Amazon Bedrock + SageMaker 自托管）中多选，设定尺寸、质量等级和区域。勾选多个模型进行并排比较，或选择一个进行专注生成。成本估算随选择实时更新。
3. **获取真正不同的选项** —— 系统生成最多 5 个明显不同的创意概念（变化服装、情绪、光照、构图 —— 而非仅仅改变相机角度），每个概念最多 5 个种子变体（共 25 张图像）。用户指定的细节被锁定；AI 推断的细节被大胆变化。
4. **编辑和精调** —— 直接在 Asset Viewer 中使用局部重绘、扩展绘制、擦除、搜索替换或重新着色。每次编辑创建新版本 —— 原始图像始终保留。
5. **下载游戏可用文件** —— 透明背景的 PNG + SVG，带有描述性命名（例如 `hospital-building_opt2_var3.png`）。视频导出为 MP4。

### 📝 风格引导模式（匹配您的艺术风格和主题）

适用于希望所有生成资产匹配现有艺术风格的团队 —— 上传参考图像，让 AI 先学习您的视觉标识。

1. **上传您的游戏美术** —— 从本地目录（递归扫描，通过符号链接避免重复）或 S3 存储桶（带分页的递归列表）导入参考图像。**智能去重**自动运行 —— 去除旋转变体（barrel_N/E/S/W.png 仅保留 barrel_S.png）和动画帧（Idle0-Idle8 仅保留 Idle）。例如，包含 747 个文件的等距资产包去重后约为 99 个独特对象。支持格式：.png、.jpg、.jpeg、.gif、.bmp、.webp、.tiff、.tif、.tga、.ico、.svg，以及从 3D 模型（.glb、.gltf）自动提取纹理。
2. **AI 学习您的风格** —— 两阶段一致性感知分析：首先进行快速检查，判断您的集合是统一的、结构一致的还是多样化的。然后对完整参考集进行深度分析，生成元数据丰富的风格档案 —— 色彩调板、线条粗细、光照模式、构图规则和制作惯例。如果您提供生成提示，AI 会将其作为"艺术家指导"接收，使分析不仅理解外观，还理解意图。
3. **应用风格生成** —— 在 Image Studio 中选择风格后，每个提示词都会自动用您风格的视觉指令增强。如 "hospital building" 这样的提示词会变成详细的生成指令，包含您游戏的色彩调板、透视惯例和渲染风格。
4. **独立模式的所有功能同样适用** —— 多选项、模型比较、编辑、版本管理和游戏可用下载都以相同方式运行，现在由您的艺术风格引导。

> [!NOTE]
> 所有生成内容均由 AI 模型产出，取决于您提供的提示词和参考。在生产环境中使用生成资产之前，请查看关于内容质量、知识产权和适用服务条款的[免责声明](#disclaimer)。

### 📝 1.1 功能一览

- 🎨 **Style Library** —— 上传美术作品，AI 学习您的视觉标识
- 🖼️ **2D Image Studio** —— 以选项 x 变体生成图像，引导式 3 步提示词工作流
- 🎨 **Prompt Designer** —— AI 将提示词分解为可编辑的视觉组件（主体、场景、光照、颜色），每个字段可锁定/变化切换，风格集成，智能资产类型分类。Photorealistic、Character、Environment 等
- 🎬 **Video Studio** —— 模型特定的提示词引导（Nova Reel 摄像机控制、Luma Ray 自然语言），多镜头、图生视频
- ✍️ **Type Studio** —— 带字体选择器的 AI 设计文字叠加
- 💬 **Chat Studio** —— 支持流式输出、Markdown、代码高亮、视觉、会话、上下文压缩的多模型 LLM 聊天
- 📁 **统一画廊** —— 浏览图像和视频、媒体过滤、搜索、下载、删除
- ✏️ **图像编辑** —— 局部重绘、扩展绘制、擦除、搜索替换、重新着色（在 AssetViewer 中）
- 🔄 **实时进度** —— 带重试/限流可见性的 SSE 流式传输
- 🛡️ **智能审核** —— 金丝雀测试、自动模型切换、AI 辅助改写
- ⚙️ **Model Registry** —— 按工作室（Image、Video、Chat、Type、Shared）组织的管理 UI、Bedrock 发现、自定义模型支持
- 📝 **Prompt Templates** —— 19 个可编辑的 LLM 指令提示词、AI 辅助优化、变量验证和自动修复
- 📦 **资产版本管理** —— 带版本历史（v1、v2、...）和版本导航的就地编辑
- 💰 **成本追踪** —— 每请求、每会话、每资产的预估 AWS 支出 —— 发送至 PulseBoard 遥测
- 🌐 **8 语言 i18n** —— 完整 UI 翻译（EN、JA、ZH、KO、HI、RU、FR、ES），自动检测非英语提示词，双语预览
- 🔍 **自定义模型支持** —— 自动发现微调、导入和已部署的自定义 Bedrock 模型
- 🔧 **自托管模型 —— 一键部署** —— 浏览精选的预测试开源模型目录（HunyuanImage 3.0、FLUX.2、FLUX.1、TripoSG 等），选择 GPU 实例，点击 Deploy。ArtSmoker 处理一切：打包推理处理器、配置量化、选择正确的 CUDA 工具包、设置自动缩放、注册 CloudWatch 告警、以及连接异步任务跟踪。目录中每个模型从冷启动到生成到画廊交付均经过端到端验证。支持 BF16 + FlashInfer 获得最佳质量，NF4 实现成本效率，多 GPU 自动检测，自动缩容至零（空闲时 $0），同一模型无需重新配置即可在不同实例类型上运行
- 🧊 **图像到 3D 生成** —— 将任何 Game Asset 或 Character 图像一键转换为带纹理的 3D 网格（GLB）。多视角合成 + 纹理烘焙生成游戏引擎可用的资产。交互式 3D 查看器支持轨道旋转/缩放/平移
- 🔄 **Auto-Update** —— 启动时版本门控 git pull、更新后自动重启、24 小时定期检查（`ARTSMOKER_AUTO_UPDATE=false` 禁用）

### 📝 1.2 屏幕截图

**2D Image Studio** —— 左侧为设置区域，包含多选模型下拉菜单、资产类型、尺寸和后处理选项。右侧为 3 步提示词工作流，带有 Prompt Designer 和 Generate Enhanced Prompt 按钮。底部为 IP 声明和成本估算。

![2D Image Studio — 设置、提示词工作流和生成控制](docs/images/image-studio-top.png)

**2D Image Studio — 生成结果** —— 上方显示增强提示词，下方为多模型比较结果。每个模型独立生成，并进行模型专属的提示词优化。结果显示模型名称、尺寸和生成成本。

![2D Image Studio — 增强提示词和生成结果](docs/images/image-studio-results.png)

**2D Image Studio — 模型比较** —— 所有选定模型的并排比较网格（展示 7 个模型）。所选选项的变体显示在下方。左侧为后处理切换开关（移除背景、转换为 SVG、放大）。

![2D Image Studio — 多模型比较网格与变体](docs/images/image-studio-comparison.png)

**Prompt Designer** —— AI 将提示词分解为可编辑的视觉组件（主体、场景、构图、光照、风格与颜色）。每个字段可通过锁定/变化控制单独编辑，生成真正不同的创意选项。

![Prompt Designer — 带可编辑字段的结构化视觉分解](docs/images/prompt-designer-top.png)

**Prompt Designer — 色彩调板** —— 带十六进制色样的命名色彩调板、风格关键词和质量级别控制。AI 学习您的视觉标识，并在所有生成中一致应用。

![Prompt Designer — 色彩调板、风格关键词和质量控制](docs/images/prompt-designer-bottom.png)

**Style Library** —— 上传您游戏的现有美术作品，AI 分析视觉风格并生成元数据丰富的提示词指南。参考图像与完整的 AI 分析和 JSON 风格档案一同显示。

![Style Library — 带参考图像的 AI 风格分析](docs/images/style-library-top.png)

![Style Library — 参考图像、导入选项和分析数据](docs/images/style-library-bottom.png)

**画廊** —— 生成的图像和视频的统一视图，带有媒体类型过滤、风格过滤、搜索和排序。点击任意资产打开完整查看器。

![画廊 — 带过滤器的生成资产网格](docs/images/gallery.png)

**Asset Viewer** —— 带选项卡界面（PNG、编辑、SVG、元数据、3D 模型）的全尺寸预览。直接下载 PNG 和 SVG。棋盘格图案展示透明背景合成效果。

![Asset Viewer — 带下载选项的全尺寸预览](docs/images/asset-viewer.png)

**Asset Viewer — 图像编辑** —— 编辑选项卡的局部重绘功能：在需要更改的区域绘制蒙版，描述想要的效果，选择编辑模型并应用。保留版本历史 —— 原始图像永远不会被覆盖。

![Asset Viewer — 蒙版和提示词局部重绘](docs/images/asset-viewer-edit.png)

**3D 模型生成** —— 将任何 Game Asset 或 Character 图像转换为带纹理的 3D 网格（GLB）。在 Asset Viewer 的 3D 模型选项卡中直接配置行进立方体分辨率、前景比例和生成参数。

![3D 模型生成 — Asset Viewer 中的设置和生成](docs/images/3d-model-generation.png)

**Video Studio** —— 左侧为设置（模型、生成模式、时长、区域、成本估算），右侧为提示词。支持 Nova Reel（单镜头、最长 2 分钟的多镜头自动/手动）和 Luma AI Ray（宽高比、循环）。

![Video Studio — 设置和提示词](docs/images/video-studio.png)

![Video Studio — 带 AI 增强提示词的生成中](docs/images/video-studio-generating.png)

![Video Studio — 带缩略图和最近视频的已完成视频](docs/images/video-studio-completed.png)

**视频播放器** —— 点击视频可内联播放，显示完整元数据（原始提示词、AI 增强提示词、模型、时长、区域）。

![视频播放器 — 带元数据的生成视频播放](docs/images/video-player.png)

### 📝 1.3 两级生成

对于每个提示词，AI 会创建**选项** —— 根本不同的设计诠释（例如对于 "warrior"：维京狂战士、日本武士、部落战士、赛博战士、希腊重甲步兵）。对于每个选项，图像模型生成**变体** —— 不同的随机种子带来微妙的视觉差异。这为艺术家提供了广泛的创意调色板可供选择。

### 📝 1.4 多模型选择


模型下拉菜单支持**基于复选框的多选** —— 在单次生成中选择任意模型组合：

- **单一模型** —— 勾选一个模型进行专注生成（最快、最便宜）
- **多个模型** —— 勾选2-3个特定模型进行定向比较（例如：仅SD 3.5 + FLUX.2）
- **All Available Models** —— 底部的切换按钮选择/取消选择所有已启用模型，进行完整并排比较

每个模型独立运行：如果较严格的模型阻止了提示词，您仍然可以获得接受该提示词的模型的结果。成本估算随模型的勾选/取消勾选实时更新。

可选的**"Model-optimized prompts"**切换会针对每个模型的优势调整提示词 —— 提示词按模型重写（例如：SD 3.5的质量增强词、FLUX.2的自然语言、Nova Canvas的简洁描述）。

### 📝 1.5 Video Studio

从文本提示词生成 AI 视频和动画。支持 **Amazon Nova Reel**（v1.0、v1.1）和 **Luma AI Ray**（v2.0）。

| 功能 | Nova Reel | Luma Ray v2 |
|------|-----------|-------------|
| **最大时长** | 120 秒（2 分钟） | 9 秒 |
| **分辨率** | 1280x720 | 720p / 540p |
| **宽高比** | 仅 16:9 | 7 个选项（1:1、16:9、9:16 等） |
| **图生视频** | 是（起始帧） | 是（起始 + 结束帧） |
| **循环视频** | 否 | 是 |
| **多镜头控制** | 是（自动 + 手动） | 否 |
| **价格** | ~$0.08/秒 | ~$1.50/秒 |

**工作原理：**
1. 选择视频模型，配置时长、宽高比、区域
2. 输入提示词 —— AI 用电影词汇、镜头运动和时间一致性提示增强
3. 点击 Generate —— 任务通过 `StartAsyncInvoke` 异步运行，输出到您配置的 S3 存储桶
4. 每 5 秒轮询状态 —— 完成时提取缩略图（通过 ffmpeg），MP4 下载到本地（或从 S3 流式传输）
5. 视频同时出现在 Video Studio 的 "Recent Videos" 部分和统一画廊中

**需要 S3 存储桶**：视频生成输出到 S3。可在 UI 的 Video Settings 中配置（浏览现有存储桶或创建新的），或通过 CLI 创建：

```bash
# 为视频存储创建 S3 存储桶（替换 REGION 和 YOUR_ORG）
aws s3api create-bucket --bucket artsmoker-video-YOUR_ORG --region us-east-1

# 对于 us-east-1 以外的区域，添加 LocationConstraint：
aws s3api create-bucket --bucket artsmoker-video-YOUR_ORG --region us-west-2 \
  --create-bucket-configuration LocationConstraint=us-west-2
```

存储模式：本地下载（默认）或从 S3 按需流式传输。

**视频提示词增强**：LLM 添加镜头运动（平移、缩放、推拉、跟踪）、光照细节和时间提示。由于视频模型不支持负面提示词，回避概念会自然地融入正面提示词中。

### 📝 1.6 Chat Studio

全功能 LLM 聊天界面 —— 自托管的对话 AI，在您自己的 AWS 账户上运行，无第三方数据访问。

**来自 16 个供应商的 80 多个模型** —— Claude（Sonnet、Opus、Haiku）、Amazon Nova、Meta Llama、Mistral、Cohere、Qwen、DeepSeek、Google Gemma、NVIDIA Nemotron 等。以及您账户中的任何自定义/导入模型。全部通过 Sync from AWS 自动发现。

**核心功能：**
- **流式响应** —— 通过 Bedrock ConverseStream 实时逐 token 渲染
- **Markdown 渲染** —— 标题、粗体/斜体、列表、表格、引用、分割线
- **代码块** —— 带语言标签和复制按钮的语法高亮（highlight.js）
- **逐消息指标** —— 输入/输出 token 数、延迟、预估成本、使用的模型
- **上下文窗口条** —— 显示已用/最大 token 数的可视化填充指示器（绿色/黄色/红色）
- **区域切换** —— 每个模型显示所有可用区域，选择最近或最便宜的

**会话管理：**
- 支持自动保存的多个并发会话
- 侧边栏中的内联重命名、复制、删除、搜索/过滤
- 将对话导出为 Markdown
- 会话总计：token 数、预估成本、消息数

**高级功能：**
- **系统提示词模板** —— General Assistant、Coding Expert、Creative Writer、Game Designer、Data Analyst、Technical Writer
- **视觉/多模态** —— 拖放、文件选择器或 Ctrl+V 粘贴图像，适用于支持视觉的模型
- **上下文压缩** —— AI 总结旧消息以释放上下文窗口空间
- **重新生成** —— 使用相同提示词重新运行 AI 响应
- **编辑并重发** —— 修改任意用户消息并从该点重新执行
- **分支** —— 从任意消息将对话分支到新会话

**定价透明度：** 模型选择器显示每 1K token 的成本，定价信息栏显示 10K 和 100K token 对话的预估成本。

### 📝 1.7 资产类型感知

选定的**资产类型**从根本上改变 AI 对提示词的诠释 —— 不仅是图像模型，而是管线的每个阶段。当您输入 "hospital" 并选择不同的资产类型时，您会得到完全不同的输出：

| 类型 | 构图 | 取景 | 技术方法 |
|------|------|------|----------|
| **Game Asset** | 透明背景上的单个分离对象。无场景、无文字、无 UI。 | 正面或等距视角，对象占据画面的 70-80%。 | 用于背景去除的干净锐利边缘，一致的左上方光照，无地面阴影。设计用于在各种比例下与其他游戏资产组合。 |
| **Character** | 干净背景上分离的全身或 3/4 身人物。仅一个角色。 | 角色占垂直空间的 60-75%，从头到脚，略偏离中心。 | 强可读的轮廓（仅凭轮廓即可识别），传达个性的表现力姿势，清晰的面部特征和服装细节。 |
| **Icon** | 单个醒目的可识别符号，居中放置并留有充足的内边距。追求最大简洁性。 | 正面或略微 3/4 倾斜，边缘留有余量。 | 必须在 64x64 像素下清晰可读。高对比度，最多 3-5 种颜色，粗体形状，无细线或精细细节。 |
| **Marketing Banner** | 具有戏剧性构图的全场景插图。一侧预留干净的文本安全区 —— 不渲染文字或排版。 | 宽银幕电影感，镜头拉远展示场景。 | 丰富饱和的色彩，戏剧性光照（轮廓光、体积光线），景深。AI 被明确指示不渲染文字，文本安全区保持干净，供设计工具（Figma、Canva 等）后期制作叠加。 |
| **Environment** | 具有前景/中景/背景深度层和引导线的完整风景。 | 宽全景镜头，地平线位于上方或下方三分之一处。 | 大气透视（远处物体更亮/更模糊），通过细节进行环境叙事，营造氛围的光照。 |

这在每个阶段都很重要：

- **"Preview Enhanced Prompt" 按钮** —— 点击 Compose 时，AI 使用资产类型将您的简短描述重构为详细的生成提示词，将您的文字与风格指南和资产类型指令结合。您的明确意图始终优先于风格默认值。您可以在生成前查看组合版本。
- **概念生成** —— 生成多个选项时，AI 创建 N 个不同的设计诠释，全部遵循资产类型的结构规则。Character 选项始终具有可读的轮廓；Marketing Banner 选项始终具有无渲染文字的文本安全区。
- **结果** —— 来自相同提示词但不同资产类型的两张图像看起来完全不同。Game Asset 的 "warrior" 是居中的单个角色精灵。Marketing Banner 的 "warrior" 是带有标题叠加干净区域的史诗战斗场景。

### 📝 1.8 3D 模型生成（图像到 3D）

从任意 2D 图像生成生产就绪的 3D 网格 —— 直接在 Asset Viewer 中操作。选择一张 **Game Asset** 或 **Character** 图像，打开 **3D Model** 标签页，点击 Generate。

![3D 模型生成 — 在交互式 3D 查看器中从多个角度查看生成的士兵网格](docs/images/3d-model-result.png)

**工作原理：**

1. **几何提取** —— 整流流变换器（TripoSG，15 亿参数，MIT 许可）使用符号距离场（SDF）表示将单张 2D 图像转换为高保真 3D 网格。网格密度随质量预设而缩放（在最高八叉树分辨率下最多约 100 万面），为面部和装备呈现锐利细节。
2. **纹理处理** —— 网格由**您在部署时选择的纹理后端**进行绘制。默认后端为 **TRELLIS.2**（Microsoft，MIT）—— 一种基于 SLAT/体素条件的纹理器，可在 4096² 图集上生成完整的 PBR 材质（基础色 + 金属度-粗糙度 + alpha），在保持商业可授权的同时，达到同类最佳专有纹理器的质量水准。
3. **PBR 输出** —— 带纹理的网格导出为内嵌 PBR 贴图的 GLB，可在任意现代引擎中进行基于物理的渲染。

**选择您的纹理后端 —— 许可信息一目了然。** 图像到 3D 支持三种纹理器，按部署逐一选择。每一种都在部署对话框中展示其**完整的许可与依赖明细** —— 它拉取的每个模型、该模型的许可，以及它是否可商用或受限 —— 您必须在部署前阅读并接受：

| 后端 | 许可 | 商业用途 | 最适用于 |
|------|------|----------|----------|
| **TRELLIS.2** *(默认)* | MIT | ✅ 可以 —— 需在您的产品中标注 "Built with DINOv3" 署名 | 生产环境、商业资产、最高质量 |
| **Hunyuan3D-Paint** | Tencent Community | ❌ 非商业 | 研究 / 非商业用途，面部表现卓越 |
| **MVPainter** | Apache-2.0 | ✅ 可以 | 轻量级商业多视角烘焙 |

背景移除（纹理处理前的抠图步骤）默认使用 **BiRefNet（MIT）**—— 完全商业洁净 —— 并提供一个非商业替代方案（RMBG），作为已披露的可选项。ArtSmoker 绝不会悄无声息地拉取受限依赖：任何受限或非商业的内容都会被命名、标记，并置于显式接受的门槛之后。

**输出：** 标准 GLB 格式，内嵌 PBR 纹理 —— 可直接导入 Unity、Unreal Engine、Blender 及其他游戏引擎。交互式 3D 查看器支持轨道旋转、缩放和平移，可即时检查；**3D Model** 标签页还会列出生成所用的确切模型与工具（几何模型、纹理后端、依赖、实例、参数），以实现完整的溯源。

**基础设施：** 通过相同的一键 Custom Models 流程部署，部署时的后端选择器会显示每个选项的许可、依赖表、实例基线以及预估成本/时间。运行于 `ml.g6e` GPU 实例；空闲时缩容至零 —— 作业间成本为 $0。首次冷启动会构建一次 CUDA 扩展（随后缓存至 S3 以加快重启）。

| 指标 | 数值 |
|------|------|
| 生成时间 | 每个资产 60-90 秒 |
| 网格质量 | 20 万-45 万面，完整顶点法线 |
| 纹理分辨率 | 最高 4K UV 图集 |
| 支持的资产类型 | Game Asset、Character |

<a id="get-started"></a>

## 📌 2. 前置条件

- **Python 3.11+**（3.12、3.13、3.14 均可）
- 已配置并具有有效凭证的 **AWS CLI**
- 用于 Bedrock 访问的 **IAM 权限**（见下文）

### 📝 2.1 AWS 凭证

ArtSmoker 使用 [boto3 的标准凭证解析](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials)，因此以下任何方法均可：

| 方法 | 最适用于 | 方式 |
|------|----------|------|
| **环境变量** | CI/CD、容器 | `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` |
| **共享凭证文件** | 本地开发 | `~/.aws/credentials`（通过 `aws configure`） |
| **命名配置文件** | 多账户 | 设置 `ARTSMOKER_AWS_PROFILE=myprofile` 或 `AWS_PROFILE` |
| **AWS SSO** | 企业 SSO | `aws configure sso` |
| **IAM 实例配置文件** | EC2、ECS、App Runner | 将 IAM 角色附加到实例 —— 机器上无需凭证 |
| **ECS 任务角色** | ECS/Fargate 容器 | 分配具有所需权限的任务执行角色 |

验证凭证是否有效的快速检查：

```bash
aws sts get-caller-identity
```

> [!NOTE]
> 在 EC2 和其他 AWS 计算服务上，您无需配置显式凭证。附加具有所需权限的 [IAM 实例配置文件](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2_instance-profiles.html)，boto3 会通过实例元数据服务自动获取。

有关详细的 IAM 权限、安装步骤、配置选项和定价信息，请参阅[英文版 README](README.md) 的 2.1.1-2.4 节、3-4 节和 11-12 节。

## 📌 5. 架构

```
┌─────────────────────────────────────────────┐
│  浏览器 (SPA)                                │
│  Vanilla JS + Tailwind CSS                  │
└──────────────────────┬──────────────────────┘
                       │ HTTP / SSE
                       ▼
┌─────────────────────────────────────────────┐
│  FastAPI 后端 (Python)                       │
│                                             │
│  /api/styles      风格 CRUD + 导入           │
│  /api/generate    两级生成                   │
│  /api/type-studio 文字叠加 + 字体            │
│  /api/video       视频生成 + 任务            │
│  /api/chat        LLM 聊天 + 会话           │
│  /api/gallery     资产浏览 + 导出            │
│  /api/browse      文件/S3 浏览器             │
│  /api/admin       模型注册表 + 模板          │
│  /api/refine-prompt 提示词 + 翻译           │
│  /api/transcribe  语音转文字                 │
└────────────┬────────────────────┬───────────┘
             │                    │
             ▼                    ▼
┌──────────────────────┐  ┌──────────────────────────┐
│  us-west-2           │  │  us-east-1               │
│                      │  │                          │
│  Claude Sonnet 4.6   │  │  Nova Canvas             │
│  Claude Opus 4.6     │  │  Titan Image v2          │
│  SD 3.5 Large        │  │  Nova Sonic              │
│  Stable Image Ultra  │  │                          │
│  Stability AI (post) │  │                          │
└──────────────────────┘  └──────────────────────────┘ ... (其他区域)
             │
             ▼
┌──────────────────────┐
│  本地存储              │
│  data/styles/         │
│  data/generated/      │
│  data/video/          │
│  data/chat/           │
└──────────────────────┘
```

## 📌 7. 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI (Python 3.11+)、boto3、Pydantic |
| 前端 | Vanilla JS、Tailwind CSS (CDN) |
| AI (LLM) | Claude Sonnet 4.6（快速任务）、Claude Opus 4.6（复杂任务） |
| AI (图像) | Nova Canvas、Titan Image v2、Stable Diffusion 3.5 Large、Stable Image Ultra |
| AI (后处理) | Stability AI（背景去除、Creative Upscale） |
| AI (聊天) | 通过 Bedrock ConverseStream 的 16 个供应商 80 多个 LLM |
| AI (视频) | Nova Reel v1.0/v1.1（最长 2 分钟）、Luma AI Ray v2（最长 9 秒） |
| AI (语音) | Nova Sonic（通过双向流式传输的语音转文字） |
| i18n | 自定义 t() 函数、817 个键 × 8 种语言、反向查找 DOM 翻译 |
| SVG 转换 | vtracer（主要）、potrace（备选）、Pillow（最后手段） |
| 文字渲染 | Pillow（阴影、描边、发光效果） |
| 存储 | 本地文件系统（兼容 S3 的接口） |
| 开发 | 静态文件无缓存中间件、通过 `POST /api/log` 的客户端错误日志 |

前端无需构建步骤。

## 📌 8. 安全模型

ArtSmoker 设计为**本地/受信网络开发工具** —— 在开发者自己的机器或私有 EC2 实例上运行。

- **无认证** —— 所有 API 端点均开放。适用于本地开发和私有团队部署。
- **文件系统浏览器** —— `GET /api/browse/local` 端点允许浏览服务器进程可访问的任意目录。这是为导入参考美术资源而特意设计的。
- **S3 访问** —— S3 浏览和导入使用服务器的 AWS 凭证。

> [!WARNING]
> 不要在未添加认证和路径限制的情况下将 ArtSmoker 暴露到不受信任的网络。有关生产环境加固指南，请参阅 [SPEC.md 中的部署路线图](SPEC.md#14-deployment--scaling-roadmap)。

## 📌 12. Amazon Bedrock 定价和成本明细

> [!NOTE]
> 下表为**规划用的参考定价**。应用本身在 Image Studio 侧边栏中显示**实时的每模型定价** —— 在注册表刷新时从 AWS Pricing API 获取并存储在 `model_registry.json` 中。

所有价格来自 [Amazon Bedrock 定价页面](https://aws.amazon.com/bedrock/pricing/)（美国区域）。详情请参阅 [SPEC.md](SPEC.md#13-aws-bedrock-pricing--cost-breakdown)。

| 服务 | 模型 | 成本 | 单位 |
|------|------|------|------|
| **Claude Sonnet 4.6** | `us.anthropic.claude-sonnet-4-6` | $3.00 输入 / $15.00 输出 | 每百万 token |
| **Claude Opus 4.6** | `us.anthropic.claude-opus-4-6-v1` | $5.00 输入 / $25.00 输出 | 每百万 token |
| **Nova Canvas** | `amazon.nova-canvas-v1:0` | $0.06 | 每张图像 |
| **Titan Image v2** | `amazon.titan-image-generator-v2:0` | $0.01 | 每张图像 |
| **Stable Diffusion 3.5 Large** | `stability.sd3-5-large-v1:0` | $0.08 | 每张图像 |
| **Stable Image Ultra** | `stability.stable-image-ultra-v1:1` | $0.14 | 每张图像 |
| **背景去除** | Stability AI | $0.07 | 每张图像 |
| **Creative Upscale** | Stability AI | $0.60 | 每张图像 |
| **SVG 转换** | 本地（vtracer/potrace） | $0.00 | 免费 |

> [!TIP]
> **关键要点**：图像生成本身很便宜（$0.01-$0.14/张）。**Creative Upscale $0.60/张是最大的成本因素** —— 请在最终选定的资产上选择性使用，而非对整批使用。背景去除 $0.07/张较为合理。SVG 转换免费（本地运行）。

<a id="disclaimer"></a>

## 📌 13. 免责声明

> [!IMPORTANT]
> **生成内容质量**：ArtSmoker 生成的所有图像、视频和其他资产均由通过 Amazon Bedrock 提供的 AI 模型产出。生成内容的质量、准确性和适当性完全取决于用户提供的提示词、所选模型和上传的风格参考。ArtSmoker 的作者和贡献者对生成内容的质量、适用性或目的适合性不作任何保证。
>
> **知识产权**：用户对确保其提示词、参考图像和生成输出不侵犯任何第三方知识产权（包括但不限于著作权、商标权和肖像权）承担全部责任。ArtSmoker 是一个工具，不会过滤、验证或评估输入或输出的知识产权状态。
>
> **AI 模型和服务条款**：生成内容受通过 Amazon Bedrock 访问的底层 AI 模型供应商的服务条款和可接受使用政策的约束。
>
> **无保证**：本软件按"现状"提供，不附带任何形式的保证。完整条款请参阅 [LICENSE](LICENSE)。

## 📌 14. 完整规格说明

请参阅 **[SPEC.md](SPEC.md)** 获取完整的技术规格说明 —— 包含架构、组件设计、模型配置、API 参考、安全模型、定价、部署路线图以及足以从零重建项目的详细信息。
