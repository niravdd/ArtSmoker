# ArtSmoker
> *对你的艺术作品进行冒烟测试！*

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green?logo=fastapi&logoColor=white)
![Amazon Bedrock](https://img.shields.io/badge/Amazon-Bedrock-orange?logo=amazonaws&logoColor=white)
![License](https://img.shields.io/badge/License-MIT--0-yellow)

## 📌 0. 概述

**ArtSmoker 让一个创意在几分钟内变成游戏引擎可用的美术资产 —— 无需您管理任何流程。** 用自然语言描述一个角色、道具、场景或主视觉，即可获得生产就绪的 2D 美术、完全纹理化的 3D 模型和视频 —— 全部匹配您项目的视觉标识，全部保留在您自己的环境中。最新的 AI 图像、编辑、3D 和视频模型都置于一个简洁、艺术家优先、带有真正创意控制的界面之后：ArtSmoker 为您运行整条生产流程，让您的团队专注于把控外观，而非摆弄底层机器。

### 📝 问题

游戏和媒体工作室的创意团队希望借力生成式 AI —— 但如今这份能力被锁在他们本不该去管理的开发者工具背后：

- **它是为工程师而非艺术家打造的** —— 最好的模型都藏在云控制台、命令行、SDK 和 REST API 之后。没有哪位导演或概念艺术家应该为了创作一件作品而去使用终端。
- **清晰的创意，晦涩的提示词** —— 艺术家清楚自己想要什么，但模型并不接受用平实创意语言下达的指令；一致且贴合简报的结果，仍然取决于夹在简报与成品之间的提示词结构、负面提示词和模型特定措辞。
- **最好的 AI 模型分散且难以运行** —— 强大的图像、编辑、3D 和视频 AI 模型不断跨越不同供应商和格式推出；把每一个都搭建起来（打包、GPU、量化、缩放）本身就是一个完整的工程项目。
- **编辑与 3D 是彼此割裂的世界** —— 局部重绘、扩展绘制、重新打光、参考引导编辑，以及将 2D 概念转换为带纹理的 3D 模型，通常各自都需要独立的工具、API 和专家。
- **保持品牌一致靠人工** —— 让每个资产都忠于您既定的外观，通常意味着要手动盯着每一次生成。

### 📝 解决方案

ArtSmoker 是一个自托管的创意工作室，将当今最好的生成式模型置于一个艺术家优先的界面之后 —— 专为游戏资产制作而构建，同时也同样适用于影视、广告、电子商务、出版，以及任何以原创视觉内容为生的团队。

- **用自然语言描述** —— ArtSmoker 在幕后处理提示词分解、增强和模型特定优化。引导式 **Prompt Designer** 让您塑造每个视觉元素 —— 主体、场景、光照、颜色 —— 并借助锁定/变化控制去探索真正不同的方向，同时不丢失已经奏效的部分。
- **默认贴合品牌** —— 把您现有的美术作品交给 ArtSmoker，它的视觉模型会学习您的视觉标识，因此每个资产产出时都会匹配您项目的外观与风格。
- **2D、编辑与 3D —— 端到端** —— 先生成，再用局部重绘、扩展绘制、重新打光、搜索替换和参考引导编辑就地精调；将任意 2D 资产转换为**完全纹理化、游戏引擎可用的 3D 模型**，可直接放入 Unity、Unreal 或 Blender —— 无需手动建模、UV 展开或纹理绘制。另外还有电影级视频和用于构思的多模型聊天工作室。
- **每个模型，一键搞定** —— 跨区域使用最新的托管模型，或将精选的开源模型（Qwen-Image、FLUX.2、HunyuanImage、TripoSG、TRELLIS.2 等）一键部署到您自己的 GPU 上 —— 打包、量化、自动缩放和任务跟踪全部处理妥当，每个模型在发布前都经过端到端验证。
- **在您想要的地方运行 —— 您的 IP 始终归您所有** —— 将它安装在单个艺术家的桌面上，或安装在供整个团队共享的实例上；**无需您自己的 GPU**（繁重的计算运行在托管的 AWS 服务上，或运行在 ArtSmoker 为您启动并在空闲时缩回至零的自动缩放端点上）。它只连接到您自己的 AWS 账户 —— 作品、提示词、风格和生成的资产都留在您的环境中，没有任何内容流向第三方服务，您对自己的创意 IP 保留完全的所有权。

**Amazon Bedrock 模型**：Claude Sonnet/Opus（提示词工程和聊天）、Stable Diffusion 3.5 Large、Stable Image Ultra、Stable Image Core、Stability AI 服务（图像编辑）、Nova Reel、Luma AI Ray（视频生成），以及 Chat Studio 可用的来自 16 个供应商的 80 多个 LLM。**自托管模型**：Qwen-Image（文生图）与 Qwen-Image-Edit（参考引导 + 指令编辑，Apache-2.0）、HunyuanImage 3.0（BF16/NF4）、FLUX.2、FLUX.1、TripoSG 与 TRELLIS.2（图像转 3D）等，通过 Amazon SageMaker 提供 —— 并附带可扩展目录以添加新模型。

**[立即开始 —— 跳转至前置条件和安装 ▸](#get-started)**

### Language / 言語 / 语言 / 언어 / हिन्दी / Язык / Langue / Idioma

ArtSmoker 支持 9 种语言。通过顶部导航栏的语言按钮（EN | 日 | 中 | 한 | हिं | РУ | FR | ES | DE）切换 UI 语言。您的选择会自动保存。

| 语言 | README |
|----------|--------|
| English | [README.md](README.md) |
| 日本語 (Japanese) | [README.ja.md](README.ja.md) |
| 中文 (Chinese) | 本文档 |
| 한국어 (Korean) | [README.ko.md](README.ko.md) |
| हिन्दी (Hindi) | [README.hi.md](README.hi.md) |
| Русский (Russian) | [README.ru.md](README.ru.md) |
| Français (French) | [README.fr.md](README.fr.md) |
| Español (Spanish) | [README.es.md](README.es.md) |
| Deutsch (German) | [README.de.md](README.de.md) |

**多语言提示词支持：**
- 非英语提示词（日语、中文、韩语、印地语、俄语、法语、西班牙语等）会被自动检测，并在生成前翻译为英语
- 提示词区域会显示双语预览：可在原始文本和英语翻译之间切换，查看模型将接收的确切内容
- 原始提示词、检测到的语言和英语翻译都会保存在资产元数据中
- 文件名由翻译后的英语提示词生成（因此 "病院の建物" → `hospital-building_opt1_var1.png`）
- Chat Studio 将提示词直接传递给 LLM（不翻译）—— 因为 Claude 等模型原生支持多语言
- Type Studio 中的文本保持您的语言不变（会按原样渲染到图像上）
- 所有审核预检和内容筛查都基于翻译后的英语提示词执行，以确保一致性

## 📌 1. 功能介绍

ArtSmoker 以两种模式运行 —— **独立模式**（无需设置艺术风格或主题，直接描述并生成）和**风格引导模式**（上传您的现有美术作品，所有生成都匹配您的视觉标识）。两种模式使用相同的工作室和生成管线。

### 📝 独立模式（快速开始）

无需风格或主题设置 —— 打开 2D Image Studio、Video Studio 或 Type Studio 即可立即开始创作。

1. **描述您的需求** —— 输入如 "hospital building" 或 "fire mage character" 的提示词，或使用语音输入。AI 将您的想法分解为视觉组件，用模型特定的优化进行增强，并通过智能锁定/变化控制尊重您的创意意图。支持任何语言输入 —— 非英语提示词会自动翻译。
2. **选择模型和设置** —— 从所有可用的文生图模型（Amazon Bedrock + SageMaker 自托管）中多选，设定尺寸、质量等级和区域。勾选多个模型进行并排比较，或选择一个进行专注生成。成本估算随选择实时更新。
3. **获取真正不同的选项** —— 系统生成最多 5 个明显不同的创意概念（变化服装、情绪、光照、构图 —— 而非仅仅改变相机角度），每个概念最多 5 个种子变体（共 25 张图像）。用户指定的细节被锁定；AI 推断的细节则被大胆变化。
4. **编辑和精调** —— 直接在 Asset Viewer 中使用局部重绘、扩展绘制、擦除、搜索替换或重新着色。每次编辑创建新版本 —— 原始图像始终保留。
5. **下载游戏可用文件** —— 透明背景的 PNG + SVG，带有描述性命名（例如 `hospital-building_opt2_var3.png`）。视频导出为 MP4。

### 📝 风格引导模式（匹配您的艺术风格和主题）

适用于希望所有生成资产都匹配现有艺术风格的团队 —— 上传参考图像，让 AI 先学习您的视觉标识。

1. **上传您的游戏美术** —— 从本地目录（递归扫描，通过符号链接避免重复）或 S3 存储桶（带分页的递归列表）导入参考图像。**智能去重**自动运行 —— 去除旋转变体（barrel_N/E/S/W.png 仅保留 barrel_S.png）和动画帧（Idle0-Idle8 仅保留 Idle）。例如，包含 747 个文件的等距资产包去重后约为 99 个独特对象。支持格式：.png、.jpg、.jpeg、.gif、.bmp、.webp、.tiff、.tif、.tga、.ico、.svg，以及从 3D 模型（.glb、.gltf）自动提取纹理。
2. **AI 学习您的风格** —— 两阶段一致性感知分析：首先进行快速检查，判断您的集合是统一的、结构一致的还是多样化的。然后对完整参考集进行深度分析，生成元数据丰富的风格档案 —— 色彩调板、线条粗细、光照模式、构图规则和制作惯例。如果您提供了生成提示，AI 会将其作为"艺术家指导"接收，使分析不仅理解可见内容，还理解您的意图。
3. **应用风格生成** —— 在 Image Studio 中选择风格后，每个提示词都会自动用您风格的视觉指令进行增强。像 "hospital building" 这样的提示词会变成详细的生成指令，包含您游戏的色彩调板、透视惯例和渲染风格。
4. **独立模式的所有功能同样适用** —— 多选项、模型比较、编辑、版本管理和游戏可用下载都以相同方式运行，现在由您的艺术风格引导。

> [!NOTE]
> 所有生成内容均由 AI 模型产出，取决于您提供的提示词和参考。在生产环境中使用生成资产之前，请查看关于内容质量、知识产权和适用服务条款的[免责声明](#disclaimer)。

### 📝 1.1 功能一览

- 🎨 **Style Library** —— 上传美术作品，AI 学习您的视觉标识
- 🖼️ **2D Image Studio** —— 以选项 x 变体生成图像，引导式 3 步提示词工作流
- 🎨 **Prompt Designer** —— AI 将提示词分解为可编辑的视觉组件（主体、场景、光照、颜色），每个字段可锁定/变化切换，风格集成，智能资产类型分类。Photorealistic、Character、Environment 等
- 🎬 **Video Studio** —— 模型特定的提示词引导（Nova Reel 摄像机控制、Luma Ray 自然语言）的文生视频，多镜头、图生视频
- ✍️ **Type Studio** —— 带字体选择器的 AI 设计文字叠加
- 💬 **Chat Studio** —— 支持流式输出、Markdown、代码高亮、视觉、会话、上下文压缩的多模型 LLM 聊天
- 📁 **统一画廊** —— 瀑布流布局，以每个资产的真实纵横比展示（竖版、方形、横版 —— 从不裁剪）。浏览图像 + 视频、媒体过滤（全部 / 2D 作品 / 3D 模型 / 视频）、搜索、完整的日期-时间-时区戳、下载、删除。已生成 3D 模型的资产带有 **3D 徽章**，**3D 模型**过滤器则专门列出这些资产
- 📥 **导入图像** —— 将现有图像（任意格式）作为一等资产导入图库。自动转换为 PNG，标记您所选的资产类型，并立即可编辑、可转 3D —— 一切（版本管理、编辑、图像转 3D）都与生成图像的行为完全一致
- ✏️ **图像编辑** —— 局部重绘、扩展绘制、擦除、搜索替换、重新着色（在 AssetViewer 中）。每种模式都有 AI **生成提示词**按钮：视觉模型读取图像及其原始提示词，为该模式和所选编辑模型量身定制编辑提示词（Stability 编辑器用描述性说明，Qwen-Image-Edit 用指令）。扩展/外绘会以像素标尺实时预览画布扩展效果，让您在提交前看清画布将扩展多少。指令型编辑器（Qwen-Image-Edit）**无需蒙版即支持全部五种模式** —— 包括真正的画布扩展：ArtSmoker 预先填充画布，让模型只补全新区域，并将您的原始像素原样混合回去。每个编辑版本都会显示**两个模型标签** —— 原始生成模型和制作该版本的编辑器
- 📤 **导出与抠图** —— AssetViewer 中按版本提供导出产物：去背景的透明 PNG 抠图，以及真正的矢量 SVG 描摹（含背景与不含背景）。背景去除方式每次可选：**免费本地处理**（rembg/u2net，无云端费用）或**付费 Amazon Bedrock** 去除器 —— 为 3D 生成准备图像时也提供同样的选择
- 🔄 **实时进度** —— 带重试/限流可见性的 SSE 流式传输
- 🛡️ **智能审核** —— 金丝雀测试、自动模型切换、AI 辅助改写
- ⚙️ **Model Registry** —— 按工作室（Image、Video、Chat、Type、Shared）组织的管理 UI、Bedrock 发现、自定义模型支持
- 📝 **Prompt Templates** —— 28 个可编辑的 LLM 指令提示词、AI 辅助优化、带自动修复的变量验证
- 📦 **资产版本管理** —— 就地编辑并保留版本历史（v1、v2……）、版本导航，以及按版本删除：只删除某一个版本（其他版本编号保持不变），查看器会切换到上一个版本 —— 删除最后一个版本将移除整个资产
- 💰 **成本追踪** —— 每请求、每会话、每资产的预估 AWS 支出，基于分区域实时 AWS 定价计算；自托管模型显示 GPU 实例的每小时运行费率 + 典型生成时长（而非易误导的每张图片价格）
- 🌐 **9 语言 i18n** —— 完整 UI 翻译（EN、JA、ZH、KO、HI、RU、FR、ES、DE），自动检测非英语提示词（英语 UI 完全跳过检测），双语预览
- 🔍 **自定义模型支持** —— 自动发现微调、导入和已部署的自定义 Bedrock 模型
- 🔧 **自托管模型 —— 一键部署** —— 浏览精选的预测试开源模型目录（Qwen-Image、Qwen-Image-Edit、HunyuanImage 3.0、FLUX.2、FLUX.1、TripoSG、TRELLIS.2 等），选择 GPU 实例，点击 Deploy。ArtSmoker 处理一切：打包推理处理器、配置量化、选择正确的 CUDA 工具包、设置自动缩放、注册 CloudWatch 告警，以及连接异步任务跟踪。目录中每个模型从冷启动到生成再到画廊交付都经过端到端验证 —— 因此您无需调试 GPU 驱动、内存溢出或容器兼容性问题。支持 BF16 + FlashInfer 获得最佳质量，NF4 实现成本效率，多 GPU 自动检测，空闲时自动缩容至零（$0），同一模型无需重新配置即可在不同实例类型上运行
- 🧊 **图像到 3D 生成** —— 将任何 Game Asset 或 Character 图像一键转换为带纹理的 3D 网格（GLB）。多视图合成 + 纹理烘焙生成游戏引擎可用的资产。交互式 3D 查看器支持轨道旋转/缩放/平移
- 🩹 **面向 3D 的智能源图补全** —— 图像转 3D 只能构建可见部分，因此被裁剪的角色（腿被截断）会生成没有腿的网格。生成前，ArtSmoker 会用视觉模型检查源图，若被裁剪则**提供**通过外绘补全（AI 建议且可完全编辑的提示词）—— 预览补全前后、重新审查结果、可再次扩展或放弃，并另存为新的图像版本。选择性启用且非阻塞；构图完整的图像直接生成
- 🔄 **Auto-Update** —— 启动时版本门控 git pull、更新后自动重启、24 小时定期检查（`ARTSMOKER_AUTO_UPDATE=false` 可禁用）

### 📝 1.2 屏幕截图

**2D Image Studio** —— 左侧为设置区域，包含多选模型下拉菜单、资产类型、尺寸和后处理选项。右侧为 3 步提示词工作流，带有 Prompt Designer 和 Generate Enhanced Prompt 按钮。底部为 IP 声明和成本估算。

![2D Image Studio — 设置、提示词工作流和生成控制](docs/images/image-studio-top.png)

**2D Image Studio — 生成结果** —— 上方显示增强提示词，下方为多模型比较结果。每个模型独立生成，并进行模型专属的提示词优化。结果显示模型名称、尺寸和生成成本。

![2D Image Studio — 增强提示词和生成结果](docs/images/image-studio-results.png)

**2D Image Studio — 模型比较** —— 所有选定模型的并排比较网格（展示 7 个模型）。所选选项的变体显示在下方。左侧为后处理切换开关（移除背景、转换为 SVG、放大）。

![2D Image Studio — 多模型比较网格与变体](docs/images/image-studio-comparison.png)

**Prompt Designer** —— AI 将提示词分解为可编辑的视觉组件（主体、场景、构图、光照、风格与颜色）。每个字段可通过锁定/变化控制单独编辑，生成真正与众不同的创意选项。

![Prompt Designer — 带可编辑字段的结构化视觉分解](docs/images/prompt-designer-top.png)

**Prompt Designer — 色彩调板** —— 带十六进制色样的命名色彩调板、风格关键词和质量级别控制。AI 学习您的视觉标识，并在所有生成中一致应用。

![Prompt Designer — 色彩调板、风格关键词和质量控制](docs/images/prompt-designer-bottom.png)

**Style Library** —— 上传您游戏的现有美术作品，AI 分析视觉风格并生成元数据丰富的提示词指南。参考图像与完整的 AI 分析和 JSON 风格档案一同显示。

![Style Library — 带参考图像的 AI 风格分析](docs/images/style-library-top.png)

![Style Library — 参考图像、导入选项和分析数据](docs/images/style-library-bottom.png)

**画廊** —— 生成的所有图像和视频的统一视图，带有媒体类型过滤、风格过滤、搜索和排序。点击任意资产打开完整查看器。**导入图像**按钮可将现有图像导入图库 —— 选择资产类型（Character/Game Asset 可用于 3D），即会转换为 PNG 并立即可编辑、可转 3D。

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

对于每个提示词，AI 会创建**选项** —— 根本不同的设计诠释（例如对于 "a warrior"：维京狂战士、日本武士、部落战士、赛博战士、希腊重甲步兵）。对于每个选项，图像模型生成**变体** —— 不同的随机种子带来微妙的视觉差异。这为艺术家提供了广阔的创意调色板可供选择。

### 📝 1.4 多模型选择

模型下拉菜单支持**基于复选框的多选** —— 在单次生成中选择任意模型组合：

- **单一模型** —— 勾选一个模型进行专注生成（最快、最便宜）
- **多个模型** —— 勾选 2-3 个特定模型进行定向比较（例如：仅 SD 3.5 + FLUX.2）
- **All Available Models** —— 底部的切换按钮选择/取消选择所有已启用模型，进行完整的并排比较

每个模型独立运行：如果较严格的模型阻止了提示词，您仍然可以获得接受该提示词的模型的结果，每张选项卡上都有清晰的状态标签（成功、被审核阻止或失败）。成本估算随模型的勾选/取消勾选实时更新。

可选的**"Model-optimized prompts"**切换会针对每个模型的优势调整提示词 —— 提示词按模型重写（例如 SD 3.5 的质量增强词、FLUX.2 的自然语言、Qwen-Image 一流的文本渲染提示）。

### 📝 1.5 参考引导生成

除了从零编写提示词之外，您还可以**从 1–3 张参考图像加一条指令**生成 —— 用 Image Studio 提示词区域顶部的分段控件选择模式：

- **匹配参考** —— 保留参考图中的主体、产品或角色，并按您的指令改变其余部分（主题、背景、服装、光照）。非常适合在不同场景间保持一致的角色或产品镜头。此模式运行于自托管的指令编辑器（Qwen-Image-Edit），**在其部署后**才会出现 —— 若尚未部署，ArtSmoker 会直接引导您从 Custom Models 部署它（一键，与 3D 流程相同）。商业安全（Apache-2.0）。
- **受参考启发** —— ArtSmoker 的视觉 AI 读取您的参考图和指令，编写一段增强提示词（先展示给您），然后用您常用的文生图模型进行生成。**始终可用** —— 无需部署。非常适合借鉴某种外观、调色或构图而不复制主体。

两种模式都需要一条指令，以便您始终掌控参考图的*用途*。参考引导生成与 Style Library（它将许多图像分析为可复用的风格档案）是分开的 —— 用它进行一次性的、由图像驱动的生成。

### 📝 1.6 Video Studio

从文本提示词生成 AI 驱动的视频和动画。支持 **Amazon Nova Reel**（v1.0、v1.1）和 **Luma AI Ray**（v2.0）。

| 功能 | Nova Reel | Luma Ray v2 |
|---------|-----------|-------------|
| **最大时长** | 120 秒（2 分钟） | 9 秒 |
| **分辨率** | 1280x720 | 720p / 540p |
| **宽高比** | 仅 16:9 | 7 个选项（1:1、16:9、9:16 等） |
| **图生视频** | 是（起始帧） | 是（起始 + 结束帧） |
| **循环视频** | 否 | 是 |
| **多镜头控制** | 是（自动 + 手动） | 否 |
| **价格** | ~$0.08/秒 | ~$1.50/秒 |

**工作原理：**
1. 选择视频模型，配置时长、宽高比、区域
2. 输入提示词 —— AI 用电影词汇、镜头运动和时间一致性提示进行增强
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

### 📝 1.7 Chat Studio

全功能 LLM 聊天界面 —— 就像一个自托管的对话式 AI，在您自己的 AWS 账户上运行，没有第三方数据访问。

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
- **上下文压缩** —— AI 总结较旧的消息以释放上下文窗口空间
- **重新生成** —— 使用相同提示词重新运行任意 AI 响应
- **编辑并重发** —— 修改任意用户消息并从该点重新执行
- **分支（Fork）** —— 从任意消息将对话分支到新会话

**定价透明度：** 模型选择器显示每 1K token 的成本，定价信息栏显示 10K 和 100K token 对话的预估成本。

### 📝 1.8 资产类型感知

选定的**资产类型（Asset Type）**从根本上改变 AI 对提示词的诠释 —— 不仅是图像模型，而是管线的每个阶段。当您输入 "hospital" 并选择不同的资产类型时，您会得到完全不同的输出：

| 类型 | 构图 | 取景 | 技术方法 |
|------|-------------|---------|-------------------|
| **Game Asset** | 透明背景上的单个分离对象。无场景、无文字、无 UI。 | 正面或等距视角，对象占据画面的 70-80%。 | 用于背景去除的干净锐利边缘，一致的左上方光照，无地面阴影。设计用于在各种比例下与其他游戏资产组合。 |
| **Character** | 干净背景上分离的全身或 3/4 身人物。仅一个角色。 | 角色占垂直空间的 60-75%，从头到脚，略偏离中心。 | 强可读的轮廓（仅凭轮廓即可识别），传达个性的表现力姿势，清晰的面部特征和服装细节。 |
| **Icon** | 单个醒目的可识别符号，居中放置并留有充足内边距。追求最大简洁性。 | 正面或略微 3/4 倾斜，边缘留有余量。 | 必须在 64x64 像素下清晰可读。高对比度，最多 3-5 种颜色，粗体形状，无细线或精细细节。 |
| **Marketing Banner** | 具有戏剧性构图的全场景插图。一侧预留干净的文本安全区 —— 不渲染文字或排版。 | 宽银幕电影感，镜头拉远展示场景。 | 丰富饱和的色彩，戏剧性光照（轮廓光、体积光线），景深。AI 被明确指示不渲染文字；文本安全区保持干净，供设计工具（Figma、Canva 等）后期制作叠加。 |
| **Environment** | 具有前景/中景/背景深度层和引导线的完整风景。 | 宽全景镜头，地平线位于上方或下方三分之一处。 | 大气透视（远处物体更亮/更模糊），通过细节进行环境叙事，营造氛围的光照。 |

这在每个阶段都很重要：

- **"Preview Enhanced Prompt" 按钮** —— 点击 Compose 时，AI 使用资产类型将您的简短描述重构为详细的生成提示词，将您的文字与风格指南和资产类型指令结合。您的明确意图始终优先于风格默认值。您可以在生成前查看组合版本。
- **概念生成** —— 生成多个选项时，AI 创建 N 个不同的设计诠释，全部遵循资产类型的结构规则。Character 选项始终具有可读的轮廓；Marketing Banner 选项始终具有无渲染文字的文本安全区。
- **结果** —— 来自相同提示词但不同资产类型的两张图像看起来完全不同。Game Asset 的 "warrior" 是居中的单个角色精灵。Marketing Banner 的 "warrior" 是带有标题叠加干净区域的史诗战斗场景。

### 📝 1.9 3D 模型生成（图像到 3D）

从任意 2D 图像生成生产就绪、完全纹理化的 3D 网格 —— 直接在 Asset Viewer 中操作。选择一张 **Game Asset** 或 **Character** 图像，打开 **3D Model** 选项卡，点击 Generate。结果是可直接导入游戏引擎的 GLB，您可以对其进行轨道旋转、缩放和下载 —— 无需手动建模、UV 展开或纹理绘制。

**生成的模型 —— 轨道旋转、检查、下载：**

![3D 模型生成 — 在交互式 3D 查看器中从多个角度查看生成的士兵网格](docs/images/3d-model-result.png)

一张 2D 角色图像（左侧，PNG 选项卡）即可变成可在浏览器中自由旋转的完全纹理化 3D 网格。**3D Model** 选项卡现在还会列出生成每个资产所用的确切**模型与工具**（几何模型、纹理后端、输出类型、实例和生成参数）—— 持久化到资产的元数据中，实现完整溯源。

**两条流程 —— 由您选择。** ArtSmoker 提供两种将图像转换为带纹理 3D 模型的方式。可在 Custom Models 中部署其一（或两者）；当两者都已上线时，您可在 Asset Viewer 中按次生成进行选择 —— 每种方式都会展示其预估成本、时间和许可，让您在充分知情的前提下决定：

| 流程 | 工作原理 | 许可 | 商业用途 | 最适用于 |
|----------|--------------|---------|----------------|----------|
| **TripoSG + 纹理后端** | TripoSG 构建网格；由所选纹理后端（TRELLIS.2 / Hunyuan3D-Paint）为其上色 | 取决于后端（见下文） | 取决于后端 | 几何模型与特定纹理器的自由组合 |
| **TRELLIS.2（完整）** | 单一模型**同时**生成几何与 PBR 纹理（SLAT） | MIT | ✅ 可以 —— 需标注 "Built with DINOv3" 署名 | 生产环境、商业资产、最简路径 |

**TripoSG 流程的工作原理：**

1. **几何提取** —— 整流流变换器（TripoSG，15 亿参数，MIT 许可）使用有向距离场（SDF）表示，将单张 2D 图像转换为高保真 3D 网格。网格密度随质量预设而缩放（在最高八叉树分辨率下最多约 100 万面），以在面部和装备上呈现清晰细节。
2. **纹理处理** —— 网格由**您在部署时选择的纹理后端**进行绘制（默认 **TRELLIS.2**，Microsoft，MIT —— 一种基于 SLAT/体素条件的纹理器，在 4096² 图集上生成完整 PBR 材质）。
3. **PBR 输出** —— 导出为内嵌 PBR 贴图的 GLB，可在任意现代引擎中直接用于基于物理的渲染。

**TRELLIS.2（完整）**流程则在单一模型中端到端完成同样的工作 —— 无需独立的纹理处理步骤。

**许可一目了然 —— 部署时与生成时皆然。** 每个可部署选项都会在部署对话框中展示其**完整的许可与依赖明细** —— 它拉取的每个模型、该模型的许可，以及是否可商用或受限 —— 您须在部署前阅读并接受。在生成时，Asset Viewer 会再次呈现该许可，并确认*"已于 `<date>` 部署时接受"*（无需二次点击）：

| 纹理后端 | 许可 | 商业用途 | 最适用于 |
|---------|---------|----------------|----------|
| **TRELLIS.2** *(默认)* | MIT | ✅ 可以 —— 需在您的产品中标注 "Built with DINOv3" 署名 | 生产环境、商业资产、最高质量 |
| **Hunyuan3D-Paint** | Tencent Community | ❌ 非商业 | 研究 / 非商业用途，面部表现卓越 |

背景移除（抠图步骤）默认使用 **BiRefNet（MIT）** —— 完全商业洁净 —— 并提供一个非商业替代方案（RMBG），作为已披露的可选项。ArtSmoker 绝不会悄无声息地拉取受限依赖：任何受限或非商业的内容都会被命名、标记，并置于显式接受的门槛之后。

**输出：** 标准 GLB 格式，内嵌 PBR 纹理 —— 可直接导入 Unity、Unreal Engine、Blender 及其他游戏引擎。交互式 3D 查看器支持轨道旋转、缩放和平移以便即时检查；**3D Model** 选项卡还会列出生成所用的确切模型与工具（几何模型、纹理后端、依赖、实例、参数），以实现完整的溯源。

**基础设施：** 两条流程均通过相同的一键 Custom Models 流程部署，部署时的选择器会显示每个选项的许可、依赖表、实例基线以及预估成本/时间。完整 TRELLIS.2 流程的合理实例基线为 **`ml.g6e.xlarge`**（约 $2.61/小时；实测峰值约 6.5 GB 显存 + 约 22 GB 主机内存 —— 真正的约束是主机内存，而非 GPU）。更大的 `g6e` 规格则作为内存余量升级选项提供。端点在空闲时缩容至零 —— 作业间成本为 $0。首次冷启动会构建一次 CUDA 扩展（随后缓存至 S3 以加速重启）。在部署受限模型之前，对话框会**预先检查它将拉取的每一个仓库的 HuggingFace 访问权限**，并为每个仓库显示 ✓/✗ 以及确切的后续步骤 —— 这样您就不会在冷启动数分钟后才发现缺少某项许可接受。

> **GLB 查看说明：** 纹理编码为 WebP（`EXT_texture_webp`）以保持文件紧凑 —— 在应用内查看器、Blender 4.x、three.js 以及现代 Unity/Unreal 导入器中均可完美渲染。macOS 的"预览"/QuickLook 不支持 glTF 中的 WebP，会将模型显示为黑色；请使用应用内查看器或任意现代 glTF 工具。

| 指标 | 数值 |
|--------|-------|
| 网格质量 | 最多约 100 万面，完整顶点法线 |
| 纹理分辨率 | 4096² PBR 图集（基础色 + 金属度-粗糙度 + alpha） |
| 许可 | 默认商业安全（TRELLIS.2 MIT + BiRefNet MIT）；非商业后端在完整披露下提供 |
| 支持的资产类型 | Game Asset、Character |

<a id="get-started"></a>

## 📌 2. 前置条件

- **Python 3.11+**（3.12、3.13、3.14 均可）
- 已配置并具有有效凭证的 **AWS CLI**
- 用于 Bedrock 访问的 **IAM 权限**（见下文）

### 📝 2.1 AWS 凭证

ArtSmoker 使用 [boto3 的标准凭证解析](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials)，因此以下任何方法均可：

| 方法 | 最适用于 | 方式 |
|--------|----------|-----|
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

### 📝 2.1.1 验证 Bedrock 访问

确认凭证有效（`sts:GetCallerIdentity`）只验证了身份 —— 并不能确认您拥有 Bedrock 权限。ArtSmoker 使用多个 Bedrock API，因此仅做一次列举测试是不够的。最可靠的检查：

```bash
# 测试 1：能否列出模型？（需要 bedrock:ListFoundationModels）
aws bedrock list-foundation-models --region us-east-1 --query "modelSummaries[0].modelId" --output text

# 测试 2：能否调用图像模型？（需要 bedrock:InvokeModel）
aws bedrock-runtime invoke-model --region us-west-2 \
  --model-id stability.sd3-5-large-v1:0 \
  --content-type application/json --accept application/json \
  --body '{"prompt":"test","aspect_ratio":"1:1"}' \
  /dev/null 2>&1 && echo "InvokeModel: OK" || echo "InvokeModel: FAILED"

# 测试 3：能否使用 Converse API？（需要 bedrock:Converse）
# （替换为任意您有权访问的 Claude 模型 ID —— 例如测试 1 列表中当前的
#  Sonnet 推理配置文件；具体版本会随时间滚动。）
aws bedrock-runtime converse --region us-west-2 \
  --model-id us.anthropic.claude-sonnet-4-6 \
  --messages '[{"role":"user","content":[{"text":"hi"}]}]' \
  --inference-config '{"maxTokens":1}' \
  --query "output.message.content[0].text" --output text 2>&1 && echo "Converse: OK" || echo "Converse: FAILED"

# 测试 4：能否列出自定义模型？（需要 bedrock:ListCustomModels）
aws bedrock list-custom-models --region us-east-1 \
  --query "modelSummaries[0].modelName" --output text 2>&1 && echo "ListCustomModels: OK" || echo "ListCustomModels: no custom models (or permission denied)"
```

如果测试 1-3 通过，您的核心权限已就绪。测试 4 仅在需要自定义模型发现时才需要。如果测试 1 通过但测试 2-3 失败，说明您的 IAM 策略允许列举但不允许调用 —— 请使用下方的权限表更新它。

### 📝 2.2 IAM 权限

您的 IAM 用户、角色或实例配置文件需要以下权限：

| 权限 | 用途 |
|------------|----------|
| `bedrock:InvokeModel` | 图像生成、图像编辑、后处理（所有图像模型） |
| `bedrock:Converse` | LLM 调用 —— 提示词优化、风格分析、概念生成 |
| `bedrock:InvokeModelWithBidirectionalStream` | 语音转写（可选 —— 没有它应用也能工作） |
| `bedrock:StartAsyncInvoke` | 视频生成（异步调用） |
| `bedrock:GetAsyncInvoke` | 轮询视频生成任务状态 |
| `bedrock:ListAsyncInvokes` | 列出视频生成任务 |
| `bedrock:ListFoundationModels` | 基础模型发现（Sync from AWS） |
| `bedrock:ListCustomModels` | 发现您账户中的微调自定义模型 |
| `bedrock:ListImportedModels` | 发现您账户中的导入模型 |
| `bedrock:GetCustomModel` | 读取自定义模型详情（基础模型、状态） |
| `bedrock:GetImportedModel` | 读取导入模型详情（架构、状态） |
| `bedrock:ListProvisionedModelThroughputs` | 查找具有预置吞吐量的可调用自定义模型 |
| `bedrock:ListCustomModelDeployments` | 查找具有按需部署的自定义模型 |
| `bedrock:CreateInference` *(或策略 `AmazonBedrockMantleInferenceAccess`)* | **Amazon Bedrock Mantle** —— 仅通过 Mantle 端点可达的前沿模型（OpenAI GPT‑5.x、Claude Mythos、GLM、Grok、Qwen、Gemma 等）。缺少它只影响这些模型；通过 Converse 的 Claude 仍可正常工作。 |
| `account:ListRegions` | 在 Sync 期间仅扫描您账户**已启用**的区域（快速，opt‑in 区域不会报错）。可选 —— 缺少时回退为扫描所有区域。 |
| `account:GetRegionOptStatus` | 读取每个区域的 opt‑in 状态（`account:ListRegions` 的配套）。可选。 |
| `s3:CreateBucket` | 为视频存储创建 S3 存储桶（可选，通过 UI） |
| `s3:PutObject` / `s3:GetObject` / `s3:DeleteObject` / `s3:ListBucket` | 视频输出存储和检索 |
| `aws-marketplace:Subscribe` | 首次使用第三方模型时自动订阅（含第三方 Mantle 模型） |
| `aws-marketplace:ViewSubscriptions` | 检查现有模型订阅 |
| `sts:GetCallerIdentity` | 启动时凭证验证；也支撑本地签名的 Mantle bearer token |
| `pricing:GetProducts` | 在 Sync from AWS 期间获取模型定价（可选） |
| `sagemaker:*` | Amazon SageMaker 上的自托管自定义模型（可选 —— 仅在使用 Custom Models 时） |
| `iam:PassRole` | 允许 Amazon SageMaker 使用您的角色（可选 —— 仅用于 Custom Models） |
| `iam:CreateRole` / `iam:AttachRolePolicy` | 首次部署时自动创建 Amazon SageMaker 执行角色（可选 —— 仅用于 Custom Models） |
| `iam:GetRole` / `iam:UpdateAssumeRolePolicy` | 自动为现有角色配置 Amazon SageMaker 信任关系（可选） |
| `secretsmanager:CreateSecret` / `secretsmanager:GetSecretValue` / `secretsmanager:DeleteSecret` | 为受限模型的 HuggingFace token 提供加密存储（可选 —— 拆除时自动清理） |

**最快设置**（托管策略 —— 访问范围最广）：

```bash
# 选项 A：将托管策略附加到您的 IAM 用户（本地开发最简单）
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

# Amazon Bedrock Mantle 端点 —— 前沿模型（OpenAI GPT-5.x、
# Claude Mythos、GLM、Grok 等）需要它。仅当您不使用仅 Mantle 的模型时才跳过。
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockMantleInferenceAccess

# 为视频存储添加 S3 访问
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

**范围化设置**（更严格的权限 —— 生产环境推荐）：

```bash
# 创建一个仅包含 ArtSmoker 所需权限的范围化 IAM 策略
aws iam create-policy --policy-name ArtSmokerAccess --policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Bedrock",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:Converse",
        "bedrock:InvokeModelWithBidirectionalStream",
        "bedrock:StartAsyncInvoke",
        "bedrock:GetAsyncInvoke",
        "bedrock:ListAsyncInvokes",
        "bedrock:ListFoundationModels",
        "bedrock:ListCustomModels",
        "bedrock:ListImportedModels",
        "bedrock:GetCustomModel",
        "bedrock:GetImportedModel",
        "bedrock:ListProvisionedModelThroughputs",
        "bedrock:ListCustomModelDeployments",
        "bedrock:CreateInference"
      ],
      "Resource": "*"
    },
    {
      "Sid": "BedrockMantleInference",
      "Effect": "Allow",
      "Action": ["bedrock:CreateInference", "bedrock:GetInference", "bedrock:ListInferences", "bedrock:GetInferenceProfile"],
      "Resource": "*"
    },
    {
      "Sid": "EnabledRegions",
      "Effect": "Allow",
      "Action": ["account:ListRegions", "account:GetRegionOptStatus"],
      "Resource": "*"
    },
    {
      "Sid": "S3VideoStorage",
      "Effect": "Allow",
      "Action": ["s3:CreateBucket", "s3:PutObject", "s3:GetObject", "s3:ListBucket", "s3:DeleteObject", "s3:HeadBucket"],
      "Resource": ["arn:aws:s3:::artsmoker-*", "arn:aws:s3:::artsmoker-*/*"]
    },
    {
      "Sid": "Marketplace",
      "Effect": "Allow",
      "Action": ["aws-marketplace:Subscribe", "aws-marketplace:ViewSubscriptions"],
      "Resource": "*"
    },
    {
      "Sid": "Utility",
      "Effect": "Allow",
      "Action": ["sts:GetCallerIdentity", "pricing:GetProducts"],
      "Resource": "*"
    },
    {
      "Sid": "SageMakerCustomModels",
      "Effect": "Allow",
      "Action": [
        "sagemaker:CreateModel", "sagemaker:CreateEndpointConfig", "sagemaker:CreateEndpoint",
        "sagemaker:DeleteModel", "sagemaker:DeleteEndpointConfig", "sagemaker:DeleteEndpoint",
        "sagemaker:DescribeEndpoint", "sagemaker:InvokeEndpoint", "sagemaker:InvokeEndpointAsync"
      ],
      "Resource": "arn:aws:sagemaker:*:*:*artsmoker*"
    },
    {
      "Sid": "SageMakerRoleManagement",
      "Effect": "Allow",
      "Action": ["iam:CreateRole", "iam:AttachRolePolicy", "iam:GetRole", "iam:UpdateAssumeRolePolicy", "iam:PassRole"],
      "Resource": ["arn:aws:iam::*:role/ArtSmoker*"]
    },
    {
      "Sid": "SecretsManagerHFTokens",
      "Effect": "Allow",
      "Action": ["secretsmanager:CreateSecret", "secretsmanager:UpdateSecret", "secretsmanager:GetSecretValue", "secretsmanager:DeleteSecret"],
      "Resource": "arn:aws:secretsmanager:*:*:secret:artsmoker/*"
    }
  ]
}'

# 附加到您的 IAM 用户（替换 YOUR_ACCOUNT_ID 和 YOUR_USERNAME）
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/ArtSmokerAccess
```

> [!TIP]
> **对于 EC2/ECS/App Runner** —— 请创建 IAM 角色，而不是附加到用户。完整的角色创建命令见 [EC2 部署](#43-ec2--cloud-deployment) 章节。无需访问密钥 —— boto3 会通过实例元数据服务自动发现该角色。

> [!NOTE]
> Bedrock 模型在所有商业 AWS 区域默认可用 —— 无需手动启用步骤。首次调用第三方模型（Anthropic、Stability AI）时，AWS 会在后台自动发起市场订阅（需要上述 `aws-marketplace` 权限）。Anthropic 模型需要一次性完成[首次使用表单](https://console.aws.amazon.com/bedrock/home#/modelaccess)。

### 📝 2.3 可选：SVG 转换工具

SVG 转换使用外部 CLI 工具（而非 Python 包）。没有它们时，SVG 输出会回退为基于 Pillow 的"栅格封装进 SVG"方案 —— 功能可用，但并非真正的矢量输出。

| 工具 | 用途 | macOS | Linux (Debian/Ubuntu) | Windows |
|------|---------|-------|-----------------------|---------|
| **vtracer** | 主要 SVG（彩色矢量描摹） | `pip install vtracer` 或 `cargo install vtracer` | `pip install vtracer` 或 `cargo install vtracer` | `pip install vtracer` 或 `cargo install vtracer` 或 [预构建二进制文件](https://github.com/visioncortex/vtracer/releases) |
| **potrace** | 备选 SVG（单色描摹） | `brew install potrace` | `sudo apt install potrace` | 从 [potrace.sourceforge.net](http://potrace.sourceforge.net/#downloading) 下载 |

验证安装：

```bash
# 检查 SVG 转换工具
which vtracer && echo "vtracer: OK" || echo "vtracer: not installed (optional)"
which potrace && echo "potrace: OK" || echo "potrace: not installed (optional)"
```

### 📝 2.4 可选：视频缩略图与元数据工具

Video Studio 通过 Amazon Nova Reel 和 Luma AI Ray 生成 MP4 视频。要提取缩略图（首帧为 JPEG）和视频元数据（时长、分辨率、FPS），运行 ArtSmoker 后端的机器上必须安装 **ffmpeg** 和 **ffprobe**。

没有 ffmpeg 时：
- 视频仍能正确生成和播放（从 S3 流式传输或下载为 MP4）
- 缺少缩略图 —— 画廊和 Video Studio 会显示黑色占位图而非预览图
- 不显示视频元数据（时长、分辨率）

| 工具 | 用途 | macOS | Linux (Debian/Ubuntu) | Windows |
|------|---------|-------|-----------------------|---------|
| **ffmpeg** | 缩略图提取 + 视频元数据 | `brew install ffmpeg` | `sudo apt install ffmpeg` | 从 [ffmpeg.org/download](https://ffmpeg.org/download.html) 下载或 `winget install ffmpeg` |

> [!NOTE]
> `ffprobe` 随 ffmpeg 一并提供 —— 无需单独安装。ArtSmoker 在运行时检查 ffmpeg 并在找不到时优雅回退 —— 无论哪种情况视频生成都能工作，只是没有缩略图。

验证安装：

```bash
ffmpeg -version 2>&1 | head -1 && echo "ffmpeg: OK" || echo "ffmpeg: not installed (optional)"
ffprobe -version 2>&1 | head -1 && echo "ffprobe: OK" || echo "ffprobe: not installed (optional)"
```

## 📌 3. 安装

### 📝 3.1 macOS

```bash
git clone <repo-url> && cd ArtSmoker

# 选项 A：使用虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 选项 B：不使用虚拟环境（系统级安装）
pip3 install -r backend/requirements.txt
```

> [!NOTE]
> 在 macOS 上，`python3` 和 `pip3` 可通过 Homebrew（`brew install python`）或 Xcode 命令行工具获得。如果看到 "command not found"，请从 [python.org](https://www.python.org/downloads/) 安装 Python，或通过 `brew install python@3.12` 安装。

### 📝 3.2 Linux (Debian/Ubuntu)

```bash
# 如需要，安装 Python
sudo apt update && sudo apt install python3 python3-pip python3-venv

git clone <repo-url> && cd ArtSmoker

# 选项 A：使用虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 选项 B：不使用虚拟环境
pip3 install --user -r backend/requirements.txt
```

> [!NOTE]
> 在某些 Linux 发行版上，在 venv 之外运行 `pip install` 需要 `--user` 标志或 `--break-system-packages`（PEP 668）。使用 venv 可完全避免这个问题。

### 📝 3.3 Windows

```powershell
git clone <repo-url>
cd ArtSmoker

# 选项 A：使用虚拟环境（推荐）
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt

# 选项 B：不使用虚拟环境
pip install -r backend\requirements.txt
```

> [!NOTE]
> 在 Windows 上，使用 `python`（而非 `python3`）。请从 [python.org](https://www.python.org/downloads/) 安装 Python —— 安装期间勾选 "Add to PATH"。Type Studio 字体选择器会从 `C:\Windows\Fonts` 检测字体（系统字体检测目前仅支持 macOS/Linux —— Windows 用户可使用全局或风格专属的自定义字体）。

## 📌 4. 运行

### 📝 4.1 单人开发（所有平台）

单进程，文件更改时自动重载 —— 适合一名开发者在本地工作：

```bash
# 使用 venv（先激活）
source .venv/bin/activate          # macOS / Linux
.venv\Scripts\activate             # Windows

uvicorn backend.main:app --reload
```

```bash
# 不使用 venv（如果系统级安装）
uvicorn backend.main:app --reload

# 或者如果 uvicorn 不在 PATH 上
python3 -m uvicorn backend.main:app --reload     # macOS / Linux
python -m uvicorn backend.main:app --reload       # Windows
```

打开 **http://localhost:8000** —— 前端由 FastAPI 提供，无需单独的 Web 服务器。

启动时，控制台会显示 AWS 凭证验证结果。如果有问题，您会看到清晰的错误框。您也可以访问 `http://localhost:8000/api/health` 查看状态。

**日志。** 除控制台外，ArtSmoker **默认**会将完整的**只追加（append-only）**日志写入 `logs/artsmoker.log`，以便您在应用关闭后回顾过去的会话。每次运行都以会话横幅（启动时间、版本、pid、主机）开头，并以关闭横幅（停止时间、时长）结尾。要更改路径或关闭它：

```bash
ARTSMOKER_LOG_FILE=/var/log/artsmoker/app.log uvicorn backend.main:app   # 自定义路径
ARTSMOKER_LOG_TO_FILE=false uvicorn backend.main:app                      # 禁用文件日志
```

（或在本地 `.env` 中设置 `log_to_file` / `log_file`。使用多个 worker 时，每个 worker 都追加到同一个文件。）

### 📝 4.2 多用户 / 共享测试机 / 生产环境（macOS / Linux）

对于任何有多个并发用户的环境 —— 无论是共享的开发/测试机、预发布还是生产 —— 都请使用带多个 worker 的 **gunicorn**：

```bash
# 安装 gunicorn（一次性，在 requirements.txt 之外）
pip install gunicorn

# 使用 gunicorn 运行（多 worker，处理并发用户）
gunicorn backend.main:app \
  -w 2 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 300
```

| 标志 | 用途 |
|------|---------|
| `-w 2` | 2 个 worker 进程（负载更重时增加） |
| `-k uvicorn.workers.UvicornWorker` | 使用 uvicorn 的异步 worker 类 |
| `--bind 0.0.0.0:8000` | 监听所有接口（不仅是 localhost） |
| `--timeout 300` | 为带重试的大批量生成设置 5 分钟超时 |

> [!TIP]
> **gunicorn** 仅支持 Linux/macOS。在 Windows 上，使用 `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2` 进行多 worker 服务。

> [!NOTE]
> **对并发用户安全。** 所有服务器写入 —— 图像/版本元数据以及模型与提示词注册表 —— 都是原子写入并**跨 worker 进程**串行化的（POSIX 文件锁），因此共享机上多个协作者的同时编辑绝不会损坏文件或丢失更新。文件日志在多个 worker 间同样工作 —— 每个 worker 都追加到同一个 `logs/artsmoker.log`。

<a id="43-ec2--cloud-deployment"></a>

### 📝 4.3 EC2 / 云部署

推荐：**t3.small**（约 $15/月），适用于 1-2 个并发用户。

**步骤 1：为 EC2 实例创建 IAM 角色**（在您的本地机器上运行）：

```bash
# 创建带 EC2 信任策略的 IAM 角色
aws iam create-role --role-name ArtSmokerEC2Role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# 附加 ArtSmoker 策略（使用第 2.2 节的范围化策略，或托管策略）
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# 创建实例配置文件并附加角色
aws iam create-instance-profile --instance-profile-name ArtSmokerEC2Profile
aws iam add-role-to-instance-profile \
  --instance-profile-name ArtSmokerEC2Profile \
  --role-name ArtSmokerEC2Role
```

**步骤 2：启动 EC2 实例**（或将配置文件附加到现有实例）：

```bash
# 附加到现有正在运行的实例
aws ec2 associate-iam-instance-profile \
  --instance-id i-YOUR_INSTANCE_ID \
  --iam-instance-profile Name=ArtSmokerEC2Profile
```

**步骤 3：在实例上安装并运行**（SSH 登录实例）：

```bash
# 安装（一次性）
sudo yum install -y python3 python3-pip git   # Amazon Linux
# sudo apt install -y python3 python3-pip python3-venv git   # Ubuntu

git clone <repo-url> && cd ArtSmoker
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install gunicorn

# 可选：安装 ffmpeg 以获得视频缩略图
sudo yum install -y ffmpeg   # Amazon Linux
# sudo apt install -y ffmpeg   # Ubuntu
```

**步骤 4：作为 systemd 服务运行**（持久化，自动重启）：

```bash
# 创建服务文件
sudo tee /etc/systemd/system/artsmoker.service > /dev/null << 'EOF'
[Unit]
Description=ArtSmoker
After=network.target

[Service]
WorkingDirectory=/home/ec2-user/ArtSmoker
ExecStart=/home/ec2-user/ArtSmoker/.venv/bin/gunicorn backend.main:app \
  -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 300
Restart=always
User=ec2-user

[Install]
WantedBy=multi-user.target
EOF

# 启用并启动
sudo systemctl daemon-reload
sudo systemctl enable artsmoker
sudo systemctl start artsmoker

# 验证是否运行
sudo systemctl status artsmoker

# 查看日志
sudo journalctl -u artsmoker -f
```

打开 **http://YOUR_INSTANCE_IP:8000** —— 请确保您的 EC2 安全组允许入站 TCP 8000。

### 📝 4.4 设置后的首要步骤

ArtSmoker 运行起来后，完成以下步骤以获得最佳效果：

**1. 从 AWS 同步模型** —— 打开**任意工作室中的 Model Settings**（齿轮图标）→ 点击 **Sync from AWS**。这会发现所有 Bedrock 区域中所有可用的图像、视频和聊天模型。耗时 30-60 秒。只需执行一次，或在 AWS 新增模型时执行。

**2. 查看并自定义提示词模板** —— 这是您能做的最有影响力的配置。打开 **Model Settings → Prompt Templates** 选项卡。ArtSmoker 使用 28 个可编辑的指令提示词来控制 AI 的行为：

| 模板 | 它控制什么 |
|----------|-----------------|
| Image Prompt Refinement | 如何将您的文字描述转化为详细的图像生成提示词 |
| Multi-Concept Generation | 如何从单个想法生成多个创意选项 |
| Style Analysis | 如何分析参考图像以学习您的艺术风格 |
| Content Moderation | 预检和改写系统有多严格 |
| Video Enhancement | 如何用镜头运动和光照丰富视频提示词 |
| Text Layout | Type Studio 如何设计图像上的文字定位 |

每个模板都可以：
- **直接编辑** —— 修改指令以符合您团队的需求
- **用 AI 增强** —— 选择任意 LLM 模型，可选地添加指令（例如"针对像素艺术优化"），然后点击 "Enhance with AI"。查看建议，然后接受或忽略
- **重置为默认** —— 随时恢复原始版本

模板按工作室组织（Image Studio、Style Library、Content Safety、Video Studio、Type Studio、Chat Studio、Translation），并附有对各自控制内容的友好说明。

**变量安全：** 模板使用 `{curly_brace}` 变量（例如 `{user_prompt}`、`{model_name}`），会在运行时替换。如果您不小心移除了必需变量，ArtSmoker 会：
1. 阻止保存并显示缺少哪些变量
2. 提供 **"Fix & Save"** —— 由 LLM 自动将缺失的变量重新插入到您编辑文本中的正确位置
3. 在保存前验证修复

模板从 `backend/prompt_templates.json` 加载 —— 运行时的唯一可信来源。您的编辑保存到 `backend/prompt_templates.user.json`（已 gitignore）并叠加于其上，因此更新或 `git pull` 绝不会覆盖您的自定义内容。如果 JSON 缺失或损坏，或代码中新增了模板，它会自愈：内置代码种子只会重新生成/回填缺失的条目，绝不覆盖已有条目。

> [!TIP]
> 先从查看 **Image Prompt Refinement** 和 **Creative Options** 模板开始。它们对输出质量影响最大。如果您的团队专精于某种特定艺术风格（例如像素艺术、水彩、等距），请将这些偏好直接加入模板，使每次生成都受益。

**3. 设置风格档案**（可选）—— 进入 **Style Library**，创建新风格，上传参考图像，然后点击 **Analyze**。这会让 ArtSmoker 学习您的视觉标识。

**4. 选择您的语言** —— 如果您偏好非英语界面，点击导航栏中的语言按钮（EN | JA | ZH | KO | FR | ES）。

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
│  /api/refine-prompt  提示词 + 翻译           │
│  /api/transcribe  语音转文字                 │
└────────────┬────────────────────┬───────────┘
             │                    │
             ▼                    ▼
┌──────────────────────┐  ┌──────────────────────────┐
│  us-west-2           │  │  us-east-1               │
│                      │  │                          │
│  Claude Sonnet       │  │  Nova Sonic (voice)      │
│  Claude Opus         │  │  Nova Reel (video)       │
│  SD 3.5 Large        │  │                          │
│  Stable Image Ultra  │  │                          │
│  Stable Image Core   │  │                          │
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

## 📌 6. 使用方法

### 📝 6.1 工作流概览

```
                            ┌─────────────────┐
                            │   ArtSmoker     │
                            └────────┬────────┘
                                     │
       ┌───────────┼───────────┼───────────┼───────────┐
       │           │           │           │           │
       ▼           ▼           ▼           ▼           ▼
  ┌──────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ ┌────────┐
  │  Style   │ │  2D    │ │ Video  │ │   Type   │ │  Chat  │
  │ Library  │ │ Image  │ │ Studio │ │  Studio  │ │ Studio │
  │          │ │ Studio │ │        │ │          │ │        │
  │ 上传     │ │生成    │ │生成    │ │ 添加文字 │ │ 多模型 │
  │ 分析     │ │ 图像   │ │ 视频   │ │ 到图像   │ │ LLM    │
  │ 设置字体 │ │        │ │        │ │          │ │ 聊天   │
  │          │ │        │ │        │ │          │ │        │
  └────┬─────┘ └───┬────┘ └───┬────┘ └────┬─────┘ └────────┘
             │              │            │               │
             │    ┌─────────┴────────────┴─────────┐     │
             │    │  是否选择了风格？（可选）      │     │
             └───►│  增强输出                      │◄────┘
                  └─────────┬──────────────────────┘
                                    │
                                    ▼
                          ┌─────────────────┐
                          │    画廊         │
                          │                 │
                          │ 浏览全部        │
                          │ 搜索/过滤       │
                          │ 选择并删除      │
                          └────────┬────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
            ┌──────────────┐ ┌──────────┐ ┌──────────────┐
            │ 下载         │ │ 在 2D    │ │ 在 Type      │
            │ PNG / SVG    │ │ Image    │ │ Studio 中    │
            │              │ │ Studio   │ │ 添加文字     │
            │              │ │ 重新载入 │ │              │
            │              │ │ (精调 &  │ │ (叠加文字)   │
            │              │ │  重生成) │ │              │
            └──────────────┘ └──────────┘ └──────────────┘
```

**三个入口，一个统一画廊：**

- **从风格开始** —— 在 Style Library 上传参考美术作品，让 AI 分析它，然后在任意工作室中生成。风格会引导所有输出。
- **无风格开始** —— 直接进入 2D Image Studio、Video Studio 或 Type Studio。AI 使用其最佳判断。
- **从画廊开始** —— 选择任意先前生成的资产，在合适的工作室中重新载入以进行精调、添加文字、播放视频，或下载为 PNG/SVG/MP4。

所有生成的资产（图像、视频、文字叠加、独立文字）都汇入统一画廊。任何内容都不会被覆盖 —— 每次生成都会创建新资产。

### 📝 6.2 生成管线

```
用户提示词： "hospital building"
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 1. 提示词组合                    Claude Sonnet (1 个选项) │
│    （可选的 "Compose" 按钮）     或 Opus (2-5 个选项)    │
│    + 风格 + 资产类型                                    │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 2. 金丝雀测试                                          │
│    单张图像测试审核                                    │
│    通过？ ──► 完整批次   失败？ ──► 模型切换           │
│                                   或改写建议           │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 3. 并行图像生成                                        │
│    最多 5 个选项 × 5 个变体 = 25 张图像                 │
│    ThreadPool (3-5 个 worker)                          │
│    指数退避重试（3 次尝试）                            │
│    SSE 进度流式传输到浏览器                            │
│    审核阻止时的协作式取消                              │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 4. 后处理（每张图像，可选）                            │
│    移除背景 ──► Stability AI ($0.07/张)                │
│    放大 ──► Stability AI Creative Upscale ($0.60)      │
│    SVG ──► vtracer / potrace / Pillow（免费，本地）    │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 5. 存储                                                │
│    data/generated/{asset_id}/                          │
│    ├── asset.png（透明背景）                           │
│    ├── asset.svg（可选）                               │
│    └── metadata.json（完整提示词谱系）                 │
│    智能文件名： prompt-slug_opt1_var2.png              │
└────────────────────────────────────────────────────────┘
```

### 📝 6.3 内容审核流程

```
用户点击 Generate
         │
         ▼
┌──────────────────────┐
│ 是否启用预检？       │
│ (Prompt Pre-Check    │
│  切换，默认           │
│  开启)               │
└───┬────────────┬─────┘
  是             否
    │            │
    ▼            │
┌──────────┐     │
│ Claude   │     │
│ Sonnet   │     │
│ 筛查     │     │
│ 提示词   │     │
└───┬────┬─┘     │
 有问题? 否      │
    │    └──────►│
    ▼            │
┌──────────────┐  │
│ 靛蓝色       │  │
│ 对话框：     │  │
│ • 切换       │  │
│ • 改写       │  │
│ • 继续       │  │
│ • 取消       │  │
└──┬───────────┘  │
   │◄────────────┘
   ▼
┌──────────────────────┐
│ 金丝雀测试           │
│ (向模型发送 1 张图像)│
└───┬────────────┬─────┘
 被阻止         通过
    │            │
    ▼            ▼
┌──────────┐  ┌──────────┐
│ 尝试备用 │  │ 完整     │
│ 模型     │  │ 批次     │
└───┬────┬─┘  │ 运行     │
 可行?  否   └──────────┘
    │    │
    ▼    ▼
翠绿色     琥珀色
对话框     对话框
(切换      (改写 →
 或         增强
 改写)      提示词区域)
```

### 📝 6.4 2D Image Studio（生成资产）

2D Image Studio 使用引导式的 3 步工作流：

**步骤 1 —— 描述您的想法**：在文本框中输入提示词。占位符会根据您选择的资产类型显示一个真实示例（例如 Character 显示 "A young female warrior in ornate silver armor..."，Environment 显示 "A misty Japanese garden at dawn..."）。使用语音输入（麦克风按钮）代替打字来口述。

**步骤 2 —— Prompt Designer** *(可选)*：点击 **🎨 Prompt Designer** 将您的提示词分解为结构化的视觉组件。AI 分析您的提示词并将其拆分为可编辑的部分：

- **Subject（主体）** —— 角色描述、服装、配饰、姿势、表情
- **Scene（场景）** —— 设定、背景、道具、时间
- **Composition（构图）** —— 相机角度、取景、景深
- **Lighting（光照）** —— 主光、补光/轮廓光、氛围
- **Style & Colors（风格与颜色）** —— 艺术风格、质量级别，以及带十六进制色样的命名色彩调板

每个字段都可以单独编辑。**Generate Enhanced Prompt** 会将您的编辑重新组合为扁平的重组提示词（在步骤 2 中只读显示），然后自动生成用于步骤 3 的 Enhanced AI Prompt。

在 Prompt Designer 打开之前，会运行一次 **AI 资产类型分类** —— 如果您的提示词描述的是场景但您选择了 "Game Asset"，会弹出对话框建议切换到 "Environment" 或 "Character"。这确保 Prompt Designer 在正确的上下文中进行分解。

**步骤 3 —— 增强提示词预览** *(可选)*：点击 **Generate Enhanced Prompt** 在生成前查看模型优化的提示词。AI 采用步骤 2 的重组提示词，并用模型特定的指导（解剖、材质、光照、提示词结构）进行增强。您可以在生成前编辑增强提示词。如果您在步骤 2 中使用了 Prompt Designer，此处会自动填充。

**提示词管线**：用户提示词 → 分解 → 重组（`recomposed_prompt`）→ 用模型指导增强（`enhanced_prompt`）→ 图像模型。对于多个选项，增强步骤会从相同的重组基础生成 N 个不同的诠释。所有三个层级都存储在元数据中。

**生成**：随时点击 Generate —— 步骤 2 和 3 都是可选的。如果跳过它们，Generate 会在继续之前自动分解、重组并增强您的提示词。**Prompt Pre-Check**（默认开启）会在生成前筛查提示词的审核问题。

**其他控件：**
- **Asset Type（资产类型）** —— 在侧边栏选择。会更改提示词占位符并影响 AI 对提示词的诠释。系统在检测到不匹配时会建议切换。
- **Art Style（艺术风格）** —— 选择风格档案，以您的视觉标识引导生成。
- **Dimensions、Options、Variations** —— 配置输出尺寸以及要生成多少个创意概念。
- **Post-Processing（后处理）** —— 移除背景、放大、SVG 转换（在生成后应用）。
- **IP Declaration（IP 声明）** —— 声明所有权或授权，以兼容严格模型。
- **Model Settings** —— 查看/编辑模型配置，发现可用的 Amazon Bedrock 模型。

生成进度通过 SSE 实时流式传输 —— UI 显示正在生成哪张图像（例如 "Generating images... 12/25"）、已用时间和当前管线阶段。如果 API 被限流，您会看到 "API throttled — waiting to retry..." 及延迟，然后 "Retrying... (attempt 2/3)" —— 每张图像最多以指数退避重试 3 次，因此大批量不会因瞬时限流而丢失变体。

生成的结果在导航后仍然保留 —— 切换选项卡后返回会保留 2D Image Studio 的 DOM 状态。只有重置按钮才会清除它。

**智能内容审核**：当您的提示词被某个模型的内容审核过滤器阻止时，ArtSmoker 会通过三个颜色编码的对话框逐步处理：

- **靛蓝色（Pre-Check）** —— 生成前，AI 会针对所选模型的已知敏感度预先筛查您的提示词。如果检测到问题，您会看到具体的关注点，并可以：切换到推荐模型、为当前模型**改写提示词**、仍然继续，或取消。
- **翠绿色（Model Switch）** —— 生成被阻止后，如果某个备用模型按原样接受您的提示词，ArtSmoker 会显示哪个模型可行以及原因。一键切换。可查看完整尝试日志（"View N model tests"）。
- **琥珀色（Rewrite）** —— 当所有模型都拒绝时，会在可编辑的文本框中提供 AI 生成的改写，并列出具体问题。已验证/未验证徽章表明改写是否通过了金丝雀测试。

**提示词改写行为**：在所有三个对话框中，选择 "Rewrite" 绝不会覆盖您的原始提示词。改写后的版本出现在原始文本下方的**增强提示词区域**，并带有持久的琥珀色免责声明：*"This rewrite is an attempt to make the prompt compatible — it is still subject to the model's own moderation assessment and may be rejected."* 您查看并编辑增强提示词，满意后点击 Generate。您的原始提示词始终保留在历史和元数据中。

常见触发因素包括受版权保护的 IP 名称和角色引用、暴力/武器用语，以及成人内容引用。提示：**"Preview Enhanced Prompt"** 按钮通常能生成自然通过审核的提示词，因为 AI 会用描述性术语重新表述。

**智能金丝雀测试**：在生成完整批次之前，ArtSmoker 会发送单个"金丝雀"图像请求，用模型的审核过滤器测试提示词。如果金丝雀被阻止，批次立即停止（浪费 1 次 API 调用而非 N×M×3 次）。如果金丝雀通过，其余任务并行运行并支持协作式取消 —— 如果任何任务遇到审核阻止，其余任务会自动跳过其 API 调用。

### 📝 6.5 使用风格档案

1. 进入 **Style Library** 选项卡。
2. 点击 **Create New Style** —— 输入名称并可选地添加生成提示。在创建模态框中，使用带 **Local** 和 **S3** 浏览按钮的 **"Import References From"** 部分来选择源目录或存储桶路径。浏览会打开服务器端的文件/目录浏览器模态框（单击选择项目，双击进入目录）。导入的参考图会在创建时自动分析。
3. 本地目录导入会**递归**扫描所有子目录中的图像（.png、.jpg、.jpeg、.gif、.bmp、.webp、.tiff、.tif、.tga、.ico、.svg）和 3D 模型（.glb、.gltf）。图像文件使用**相对符号链接**进行**符号链接**（无重复，可跨机器移植）。3D 模型文件（.glb/.gltf）的内嵌纹理会被**自动提取** —— base64 data URI、二进制缓冲区块和外部纹理引用都会被处理。提取的纹理会保存为副本（以模型名称为前缀以避免冲突）。S3 导入会带分页递归列出并将文件**下载**到本地。每个风格最多导入 **100 张参考图像**。支持的扩展名集中定义在 `backend/config.py`（`IMAGE_EXTENSIONS` 和 `MODEL_EXTENSIONS_WITH_TEXTURES`）。
4. **两阶段一致性感知分析**：阶段 1 向 Claude Sonnet 发送 8 张图像以确定一致性级别（高/中/低）—— 高表示统一风格，中表示结构共享但主题不同，低表示风格多样。阶段 2 将一致性评估连同参考图像一起提供给 Claude Opus，引导它针对该集合类型进行恰当分析。当风格拥有超过 20 张参考图时，分析器会为 Opus 视觉调用选取 20 张多样化的代表性子集 —— 确保覆盖各文件名分组和文件大小的多样性。AI 会被告知总共有多少张图像以及它实际看到多少张。分析提示词专为透明背景上的游戏资产设计 —— 会要求提供材质特定的渲染细节、比例系统以及阴影/光照细节。提取 9 个风格属性，包括 `materials`（石头、木头、金属如何渲染）和 `detail_level`（哪些表面细节可见、哪些被简化）。生成提示会被扩展为涵盖 8 个维度的 200 字内容：透视、渲染、材质、色彩调板、比例、边缘处理、阴影/光照、细节级别和背景 —— 足够具体，使生成的资产在视觉上与现有参考融为一体。
5. 在风格详情视图中，使用 **"Import & Analyze"** 一步添加更多参考并触发分析。也支持拖放上传，并在添加新图像时**自动重新分析**。
6. **"Re-Analyze Style"** 在初次分析后出现，让您随时手动重新运行分析。
7. **生成提示**是分析上下文的一部分 —— AI 在分析时会同时接收参考图像和您的提示作为"艺术家指导"，因此风格档案理解的是意图，而不仅仅是视觉外观。编辑生成提示也会触发**自动重新分析**。
8. 回到 **2D Image Studio**，从下拉菜单中选择您的风格 —— 所有生成的资产都会匹配其视觉标识（调板、透视、渲染风格、氛围）。

### 📝 6.6 风格分析流程

```
┌──────────────────────────────────────────┐
│ 创建 / 导入风格                          │
│ （上传或导入参考图像）                    │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│ 阶段 1：一致性检查                       │
│ Claude Sonnet — 8 张图像 — ~$0.01        │
│ 确定：高 / 中 / 低                       │
│   高   = 统一风格                        │
│   中   = 结构共享，主题不同              │
│   低   = 多样化集合                      │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│ 阶段 2：完整分析                         │
│ Claude Opus — 最多 20 张图像             │
│ 由一致性级别引导                         │
│ + 艺术家指导（用户提示）                 │
│ 提取 9 个风格属性                        │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│ 阶段 3：提示生成                         │
│ Claude Sonnet — 200 字提示               │
│ 8 个维度：透视、渲染、                    │
│ 材质、调板、比例、边缘、                  │
│ 阴影/光照、细节级别                       │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│ 存储于 profile.json                      │
│ 每次风格分析总计约 $0.14                 │
│ 用于所有未来生成                         │
└──────────────────────────────────────────┘
```

### 📝 6.7 Type Studio

向图像添加文字，或用 AI 设计的排版生成独立的文字资产。

- **两种模式**："On Image" 将文字合成到画廊图像上；"Standalone" 在透明背景上渲染文字。
- **多行文本编辑器**，支持逐行字体选择、定位控件，以及**语音输入**（每行一个麦克风按钮 —— 通过 Nova Sonic 转写口述文字）。
- **AI 设计的布局** —— AI 建议颜色、大小、位置和效果（阴影、描边、发光）。请求 1–5 个布局选项以获得不同的创意方向。用于布局的 **LLM 模型**可配置（Complex LLM 获得最佳质量，Fast LLM 更便宜）—— 读取自注册表分类。
- **带实时预览的字体选择器** —— 风格字体、8 种内置字体（Roboto、Open Sans、Lato、Montserrat、Playfair Display、Oswald、Raleway、Source Code Pro）、系统字体，以及**客户端检测到的字体**（通过 Local Font Access API 或 canvas 探测）。
- **预处理 / 后处理** —— 与 2D Image Studio 相同的工作流，后处理带 "Apply" 按钮。SVG 转换默认开启。
- **点击缩放** —— 点击结果预览会打开 AssetViewer，带完整的缩放/平移、元数据、下载和图像编辑工具。
- 结果保存为新的画廊资产（原始图像永不被覆盖）。

### 📝 6.8 画廊

- 所有生成的图像和视频的**统一视图**，采用**瀑布流布局**（每个资产以其真实纵横比展示 —— 竖版、方形或横版 —— 从不居中裁剪），带有 **Media 过滤器**（全部 / 2D 作品 / 3D 模型 / 视频）。**3D 模型**过滤器仅显示已生成 3D 模型的资产，这些资产的图块上带有 **3D 徽章**。
- **搜索栏**，可对所有资产（提示词、风格、模型）即时过滤。
- 带复选框的**多选**，用于批量删除（同时处理图像和视频资产）。删除是**批次感知**的 —— 存活的兄弟资产会跟踪有多少变体被移除，因此在 Image Studio 中重新载入部分批次时会显示 "X of Y images remaining (Z deleted)"。
- 资产借助内存中的元数据缓存立即加载。按最新优先排序。
- 支持分页（limit/offset）以处理大型集合。
- 当您导航回画廊时，以及在任何编辑或视频生成完成后，画廊会自动刷新。
- **视频卡片**显示带播放叠加、VIDEO 徽章和时长指示器的缩略图。点击打开视频播放器模态框。
- 根据类型为每个资产提供**上下文操作按钮**：**"2D Studio"**（靛蓝色）在图像工作室中重新载入，**"Add Text"**（翠绿色）在 Type Studio 中打开，**"Edit in Type Studio"**（紫色）用于文字资产。
- 点击任意图像打开 **AssetViewer** 模态框，包含：
  - **缩放/平移** —— 鼠标滚轮缩放，拖动平移，Fit/1:1 按钮并高亮当前激活模式。
  - **Edit 选项卡** —— 直接对图像进行局部重绘、擦除、外绘、搜索替换或重新着色。每种模式提供两类编辑器：**基于蒙版**（Stability）—— 用画笔工具绘制蒙版，输入提示词并应用；以及**无蒙版指令编辑器**（Qwen-Image-Edit，已部署时）—— 只需用文字描述更改，无需蒙版。对于无蒙版模型，画笔控件会自动隐藏。选择编辑模型并应用；默认替换原始图像，取消勾选 "Replace original" 可另存为新资产（每次编辑都保留版本历史）。
  - **Previous / Next** —— 箭头按钮和键盘左/右键可在列表中导航而无需关闭查看器。
  - **完整元数据**：原始提示词、AI 改进的提示词、生成提示词、负面提示词、风格、资产类型、图像模型（友好名称）、尺寸、种子、批次 ID、选项/变体索引、IP 声明状态、文件名和创建日期。
- **风格快照**：每个资产都存储生成时所用风格的快照（名称、描述、提示、分析）。如果原始风格后来被删除，资产仍保留完整上下文。向后兼容 —— 没有快照的旧资产也能正常显示。

### 📝 6.9 语音输入

点击提示词编辑器旁的麦克风按钮来口述您的提示词。音频会发送到 Nova Sonic 进行转写。

> [!NOTE]
> 语音转写需要 Nova Sonic 的双向流式 API，它依赖于兼容的 boto3 版本以及在 us-east-1 中启用的模型访问。如果流式 API 不可用，服务会返回一个占位确认。当 Nova Sonic 流式传输正确配置后，完整的实时转写即可工作。

### 📝 6.10 视图状态保留

导航顺序：**Style Library → 2D Image Studio → Type Studio → Video Studio → Gallery**。在视图之间切换会保留每个视图的 DOM 状态。生成的结果、表单输入和滚动位置在导航后仍然保留。2D Image Studio 和 Video Studio 中的琥珀色重置按钮是清除它们状态的唯一方式。

### 📝 6.11 模型管理

所有 AI 模型配置都集中在 `backend/model_registry.json` —— 唯一可信来源。模型、区域、定价、质量等级和格式模板全都存储于此，并通过 UI 或 API 管理：

- 点击任意工作室侧边栏中的 **"Model Settings"** 打开管理模态框 —— 它会打开到该工作室的相关选项卡。
- 按工作室组织的 **7 个选项卡**：
  - **Image Studio** —— 图像生成模型（SD 3.5 Large、Stable Image Ultra、Stable Image Core，以及自托管的 FLUX、HunyuanImage、Qwen-Image）、区域、质量等级、提示词限制、审核严格度
  - **Video Studio** —— 视频模型（Nova Reel、Luma Ray）、S3 存储桶设置、区域、定价
  - **Chat Studio** —— 发现的聊天/LLM 模型（来自 16 个供应商的 80 多个）、上下文窗口、视觉能力、每 1K token 定价
  - **Type Studio** —— 用于文字布局生成的 LLM 模型（Complex 或 Fast LLM）
  - **Shared Studio** —— 跨工作室的 LLM 分类（Fast LLM、Complex LLM、Fallback LLM、Voice）、后处理模型（移除背景、放大）
  - **Prompt Templates** —— 28 个可编辑的 LLM 指令提示词，组织为 6 个工作流部分（见第 4.4 节）
  - **Registry JSON** —— 完整模型注册表的原始 JSON 编辑器
- 所有部分都**可折叠**，带 **Show All / Hide All** 切换以便快速导航。
- LLM 分类和后处理使用**下拉模型选择器**（由发现的模型填充）—— 而非原始文本字段。
- **Sync from AWS**：扫描所有支持 Bedrock 的 AWS 区域（动态发现），自动注册新的图像、视频和**聊天模型**，更新区域可用性，从 AWS Pricing API 获取每个模型的定价，并禁用不再可用的模型。**实时进度叠加层**会在每个区域被扫描时流式展示。这是**唯一**调用 AWS 发现 API 的操作 —— 所有其他操作都从缓存的注册表读取。
- **始终使用最新的 Claude**：每次 Sync 都会自动将您的 **Fast LLM** 滚动到账户中可用的最新 Claude Sonnet，将 **Complex LLM** 滚动到最新的 Claude Opus，因此您永远不会被困在弃用的模型上 —— 无需手动配置。如果您为某个分类手动选择了特定模型，它会被**固定**，自动滚动不会动它（只在有更新版本出现时通知您）。
- **自定义模型发现**：Sync 还会发现**微调的自定义模型**（`ListCustomModels`）、**导入的模型**（`ListImportedModels`），以及具有**按需部署**（`ListCustomModelDeployments`）或**预置吞吐量**（`ListProvisionedModelThroughputs`）的模型。自定义模型会自动从基础模型继承其格式族。
- **自动发现**：新的基础模型以 `enabled=true` 注册 —— 管理员可禁用它们。现有模型的 `available_regions` 和 Bedrock 元数据（模态、生命周期、ARN）会自动更新。
- **样式化确认对话框**：所有破坏性操作（Sync、删除、重置）都使用自定义样式化模态框 —— 没有浏览器 `confirm()` 弹窗。
- 更改会通过 Admin API 立即持久化到 `model_registry.json`。
- 注册表向后兼容 —— 现有资产引用模型键（例如 `sd35_large`），而非原始 Bedrock 模型 ID。

### 📝 6.12 自托管模型（Amazon SageMaker 上的自定义模型）

ArtSmoker 可以在您自己的 AWS 账户中于 **Amazon SageMaker** 上部署开源 AI 模型，将您的能力扩展到 Amazon Bedrock 所提供的范围之外。它们与 Bedrock 模型并行运行，并出现在相同的工作室下拉菜单中。

**可扩展的模型目录：** 附带一个内置的开源模型目录，涵盖图像生成、放大、背景移除、深度估计、分割和视频。添加新模型只需一个目录条目 —— 无需更改代码。您也可以通过 UI 添加自定义模型（+ Add Model）。目录和可用模型会随时间演进。

**部署选项：**
- **异步（scale-to-zero）** —— 仅在生成时付费。空闲时缩容至零（$0 成本），新请求到来时自动扩容。冷启动约 5-10 分钟。
- **Always-On** —— 即时响应，约 $1.41/小时（ml.g5.xlarge）

**如何部署：** Model Settings → Custom Models 选项卡 → 点击 Deploy。SageMaker 容器在启动时直接从 HuggingFace 拉取模型权重 —— 无需数 GB 的本地下载。

**CPU 卸载：** 大型扩散模型使用智能 CPU 卸载以适配较小的 GPU 实例。每个模型的目录条目指定策略 —— `model_cpu_offload`（将活跃层保留在 GPU 上）或 `sequential_cpu_offload`（针对超大模型的激进逐层卸载）。由推理处理器自动应用。

**带 Pending Jobs 的异步生成：** 自托管模型异步生成。2D Image Studio 中会出现一个 **Pending Jobs** 面板，显示带进度指示器的活跃任务。完成的图像会自动到达画廊 —— 无需轮询或刷新页面。

**HuggingFace token 管理：** 受限模型需要只读 HuggingFace token。该 token 加密存储在您账户的 **AWS Secrets Manager** 中，通过 UI 管理（设置/更新/删除），并在所有需要它的模型间共享。当您拆除所有模型时，token 会被自动清理。

**受限访问预检：** 在受限部署之前，对话框会使用您存储的 token 探测模型将拉取的**每一个** HuggingFace 仓库（其自身权重加上任何依赖），并为每个仓库显示 ✓/✗ 以及确切的后续步骤 —— 在 HuggingFace 上接受*这个*仓库的许可，或添加 token。在每个必需仓库都可达之前，部署会保持阻塞状态，因此遗忘的许可接受会在对话框中快速失败，而不是在冷启动数分钟后才失败。

**设置：** 将 Amazon SageMaker 和 Secrets Manager 权限添加到您已用于 Bedrock 的**同一 IAM 角色** —— 无需单独的角色或环境变量。ArtSmoker 会在 EC2/ECS 上自动发现您的角色，或在需要时自动创建 `ArtSmokerSageMakerRole`。

```bash
# 将 Amazon SageMaker 权限添加到您现有的 ArtSmoker 角色（一条命令）
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
```

**Python 依赖：** `huggingface_hub>=0.23`（用 `pip install huggingface_hub` 安装）

### 📝 6.13 图像与视频生成模型

所有模型都从注册表**动态发现** —— 而非硬编码。Image Studio 下拉菜单在页面加载时由 `GET /api/admin/models/image-options` 填充，Video Studio 下拉菜单由 `GET /api/admin/models/video-options` 填充。任何在注册表中注册并启用的模型都会自动出现。

**Image Model** 下拉菜单是主要选择。其下方有一行智能摘要，显示激活的区域、质量等级和每图像成本。可展开的 **Advanced** 部分让您覆盖：

- **Quality（质量）** —— 支持质量等级（Standard/Premium 价格拆分）的模型显示下拉菜单；没有等级的模型显示 "Default"。等级通过 `quality_options` 在注册表中按模型声明。
- **Region（区域）** —— 显示所选模型可用的区域，按最便宜优先并附带定价排序。"Auto" 选择最便宜的区域。

**成本估算**会根据所有选择（模型 × 质量 × 区域 × 选项 × 变体）动态更新。

**格式族**：模型通过一个通用调用器（`invoke_image_model`）调用，该调用器从注册表（`format_families`）读取请求模板。目前有 15 个族，涵盖图像生成（2）、图像编辑（8）、后处理（2）和视频生成（2）：
- **图像生成**：`stability_text_to_image`（SD 3.5 Large、Stable Image Ultra、Stable Image Core），以及用于 FLUX、HunyuanImage 和 Qwen-Image 的自托管族（`sagemaker_*`）
- **图像编辑**：`amazon_inpainting`、`amazon_outpainting`、`stability_inpaint`、`stability_outpaint`、`stability_erase`、`stability_search_replace`、`stability_search_recolor`、`stability_control`、`stability_style_transfer`
- **后处理**：`stability_remove_bg`、`stability_upscale`
- **视频**：`nova_reel`、`luma_ray`

添加新的 Bedrock 图像模型无需任何代码更改 —— 只需通过管理 API 或自动发现以正确的格式族注册它。

**模型优化的提示词工程**：提示词会按照 [AWS 文档](https://docs.aws.amazon.com/nova/latest/userguide/prompting-image-generation.html)自动构造为描述性说明（而非命令）。否定词会从主提示词中移除，排除术语作为单独的**负面提示词**发送。提示词会截断到注册表中每个模型特定的 `prompt_limit`。

> [!NOTE]
> **审核敏感度因模型而异**，并在注册表中跟踪（`moderation_strictness`）。Amazon Bedrock 的 Stability 模型（SD 3.5 Large、Stable Image Ultra、Stable Image Core）应用 AWS 平台审核并被调校为 "moderate"；自托管模型（FLUX、HunyuanImage、Qwen-Image）在您自己的账户中运行，没有平台强加的内容过滤器。ArtSmoker 会自动处理阻止 —— 当提示词被拒绝时，系统会按严格度排序尝试备用模型，然后才建议改写。

## 📌 7. 技术栈

| 层级 | 技术 |
|-------|-----------|
| 后端 | FastAPI (Python 3.11+)、boto3、Pydantic |
| 前端 | Vanilla JS、Tailwind CSS (CDN) |
| AI (LLM) | Claude Sonnet（快速任务）、Claude Opus（复杂任务） |
| AI (图像) | Stable Diffusion 3.5 Large、Stable Image Ultra、Stable Image Core（Amazon Bedrock）；FLUX.2/FLUX.1、HunyuanImage 3.0、Qwen-Image（SageMaker 自托管） |
| AI (后处理) | Stability AI（移除背景、Creative Upscale） |
| AI (聊天) | 通过 Bedrock ConverseStream 的来自 16 个供应商的 80 多个 LLM（Claude、Nova、Llama、Mistral 等） |
| AI (视频) | Nova Reel v1.0/v1.1（最长 2 分钟）、Luma AI Ray v2（最长 9 秒） |
| AI (语音) | Nova Sonic（通过双向流式传输的语音转文字） |
| i18n | 自定义 t() 函数、817 个键 × 6 种语言、反向查找 DOM 翻译 |
| SVG 转换 | vtracer（主要）、potrace（备选）、Pillow（最后手段） |
| 文字渲染 | Pillow（阴影、描边、发光效果） |
| 存储 | 本地文件系统（兼容 S3 的接口） |
| 开发 | 静态文件无缓存中间件；通过 `POST /api/log` 的客户端错误日志 |

前端无需构建步骤。

## 📌 8. 安全模型

ArtSmoker 设计为**本地/受信网络开发工具** —— 它在开发者自己的机器或私有 EC2 实例上运行。安全模型反映了这一点：

- **无认证** —— 所有 API 端点均开放。适用于本地开发和私有团队部署。
- **文件系统浏览器** —— `GET /api/browse/local` 端点允许浏览服务器进程可访问的任意目录。这是为从您的机器导入参考美术资源而特意设计的。
- **字体服务** —— 路径穿越保护会验证字体文件请求是否停留在预期目录内。
- **S3 访问** —— S3 浏览和导入使用服务器的 AWS 凭证。用户可以访问其 IAM 角色允许的任何 S3 存储桶。

> [!WARNING]
> 不要在未添加认证和路径限制的情况下将 ArtSmoker 暴露到不受信任的网络。有关生产环境加固指南（第 4 阶段增加 Cognito 认证），请参阅 [SPEC.md 中的部署路线图](SPEC.md#16-deployment--scaling-roadmap)。

## 📌 9. API

交互式文档位于 **http://localhost:8000/docs**（Swagger UI）。

关键端点：

| 端点 | 用途 |
|----------|---------|
| **生成** | |
| `POST /api/generate/` | 通过 SSE 流式传输生成资产（选项 × 变体） |
| `POST /api/generate/post-process` | 对现有资产应用处理 |
| `POST /api/generate/edit` | 图像编辑：局部重绘、外绘、擦除、搜索替换等。接受源图像、蒙版、提示词、模型。 |
| `POST /api/generate/suggest-edit-prompt` | Edit 选项卡的 AI "Generate Prompt"：读取图像 + 原始提示词，为给定模式返回编辑提示词，并为目标编辑模型量身定制（描述性说明 vs. 指令） |
| `POST /api/generate/analyze-moderation` | 分析被审核阻止的提示词并建议安全改写 |
| **风格** | |
| `POST /api/styles/` | 创建风格档案 |
| `POST /api/styles/{id}/import` | 从本地文件夹或 S3 URI 批量导入参考 |
| `POST /api/styles/{id}/analyze` | 触发 AI 风格分析 |
| **提示词** | |
| `POST /api/refine-prompt/` | 预览精调后的提示词 |
| `POST /api/transcribe/` | 语音转文字（Nova Sonic） |
| **画廊** | |
| `GET /api/gallery/` | 浏览生成的资产（支持 limit/offset 分页） |
| `GET /api/gallery/batch/{batch_id}` | 为一个批次重建完整的选项 × 变体结构 |
| `DELETE /api/gallery/` | 批量删除资产 |
| **Type Studio** | |
| `POST /api/type-studio/preview` | 渲染文字叠加预览 |
| `POST /api/type-studio/suggest` | 文字的 AI 布局建议 |
| `GET /api/type-studio/fonts` | 列出可用字体 |
| **浏览** | |
| `GET /api/browse/local?path=~` | 浏览本地目录内容 |
| `GET /api/browse/s3/buckets` | 列出可用的 S3 存储桶 |
| `GET /api/browse/s3?bucket=name&prefix=path` | 浏览 S3 存储桶内容 |
| **聊天** | |
| `POST /api/chat/stream` | 通过 SSE 流式传输 LLM 响应（Bedrock ConverseStream） |
| `GET /api/chat/models` | 列出所有可用的聊天模型（基础 + 自定义 + 导入） |
| `POST /api/chat/sessions` | 创建新的聊天会话 |
| `GET /api/chat/sessions` | 列出聊天会话 |
| `GET /api/chat/sessions/{id}` | 加载完整会话（消息 + 元数据） |
| `PUT /api/chat/sessions/{id}` | 更新会话（标题、消息、模型、temperature） |
| `DELETE /api/chat/sessions/{id}` | 删除会话 |
| `POST /api/chat/sessions/{id}/duplicate` | 复制会话 |
| `GET /api/chat/sessions/{id}/export` | 将会话导出为 Markdown |
| `GET /api/chat/sessions/{id}/search?q=` | 在会话消息内搜索 |
| `POST /api/chat/compact` | 通过 LLM 摘要压缩较旧的消息 |
| `POST /api/chat/generate-title` | 从首次交流自动生成会话标题 |
| **视频** | |
| `POST /api/video/generate` | 启动异步视频生成任务 |
| `GET /api/video/status/{job_id}` | 轮询视频生成任务状态 |
| `GET /api/video/jobs` | 列出所有视频生成任务 |
| `GET /api/video/{id}/mp4` | 提供视频 MP4 文件 |
| `GET /api/video/{id}/thumbnail` | 提供视频缩略图 |
| `DELETE /api/video/{id}` | 删除视频 |
| **管理** | |
| `GET /api/admin/models` | 获取完整模型注册表（LLM、图像模型、后处理） |
| `GET /api/admin/models/image-options` | 用于下拉菜单的已启用文生图模型（带定价、质量等级、区域）。接受 `?region=` 过滤器。 |
| `GET /api/admin/regions` | 缓存的支持 Bedrock 的 AWS 区域列表（无 AWS 调用） |
| `PATCH /api/admin/models/category/{name}` | 更新 LLM 分类配置 |
| `PATCH /api/admin/models/image/{key}` | 更新图像模型配置 |
| `POST /api/admin/models/image` | 添加新的图像模型 |
| `POST /api/admin/discover/refresh-all` | 完整刷新：发现区域 + 扫描模型 + 获取定价 + 清理陈旧数据。唯一调用 AWS 发现 API 的端点。 |
| `POST /api/admin/discover/{region}/auto-register` | 扫描单个区域的模型，注册新的，为现有模型更新区域 |
| `GET /api/admin/discover/{region}` | 发现某区域中可用的 Bedrock 模型（原始列表） |
| `GET /api/admin/templates` | 获取全部 28 个可编辑提示词模板 |
| `PATCH /api/admin/templates/{name}` | 更新模板（验证必需变量） |
| `POST /api/admin/templates/{name}/reset` | 将模板重置为默认 |
| `POST /api/admin/templates/{name}/enhance` | 用 AI 增强模板 |
| **系统** | |
| `POST /api/log` | 客户端错误/警告日志（在服务器控制台中记录为 `[CLIENT]`） |
| `GET /api/health` | 健康检查 + AWS 凭证/Bedrock 验证 |

## 📌 10. 项目结构

```
ArtSmoker/
├── backend/
│   ├── main.py              # FastAPI 应用、启动验证、静态挂载
│   ├── config.py            # 设置（AWS 区域、模型 ID、路径、限制）
│   ├── model_registry.json  # 唯一可信来源：模型、区域、定价、格式族、质量等级
│   ├── requirements.txt
│   ├── prompt_templates.json # 可编辑的 LLM 指令提示词 —— 运行时唯一可信来源（28 个模板）
│   ├── routers/
│   │   ├── generate.py      # 两级资产生成 + SSE 流式传输
│   │   ├── styles.py        # 风格档案 CRUD + 目录/S3 导入 + 分析
│   │   ├── gallery.py       # 资产浏览 + 文件服务 + 批量删除
│   │   ├── typestudio.py    # Type Studio：文字叠加、字体服务、AI 布局
│   │   ├── video.py         # 视频生成（异步）、任务轮询、MP4/缩略图服务
│   │   ├── chat.py          # Chat Studio：LLM 流式传输、会话、导出、上下文压缩
│   │   ├── browse.py        # 用于参考导入的服务器端文件/S3 浏览器
│   │   ├── refine.py        # 提示词精调预览 + 翻译预览
│   │   ├── transcribe.py    # 语音转写
│   │   └── admin.py         # 模型注册表管理 + Bedrock 发现 + 提示词模板
│   ├── services/
│   │   ├── bedrock_client.py     # 带连接池的共享 Bedrock 客户端
│   │   ├── model_registry.py     # 模型注册表：加载/保存 model_registry.json
│   │   ├── prompt_engineer.py    # Claude：提示词精调 + 概念生成
│   │   ├── image_generator.py    # 路由到 Bedrock（SD 3.5 / Ultra / Core）或 SageMaker（FLUX / Hunyuan / Qwen）
│   │   ├── style_analyzer.py     # 两阶段风格分析（一致性 + 完整）
│   │   ├── post_processor.py     # Stability AI：背景移除、放大；vtracer：SVG
│   │   ├── transcriber.py        # Nova Sonic：流式语音转文字
│   │   ├── import_dedup.py       # 智能去重（旋转、动画、文件夹）
│   │   ├── texture_extractor.py  # glTF/GLB 纹理提取
│   │   ├── prompt_translator.py  # 自动检测语言 + 翻译为英语
│   │   ├── prompt_templates.py   # 可编辑的 LLM 指令提示词（加载/保存/验证）
│   │   ├── video_generator.py   # 视频：异步 Bedrock 调用、S3 下载、ffmpeg 缩略图
│   │   ├── cost_tracker.py      # 请求范围的成本累加器
│   │   ├── custom_models.py    # 自托管模型目录（可扩展）
│   │   ├── async_jobs.py       # 异步生成任务队列（Pending Jobs 面板）
│   │   ├── sagemaker_deployer.py # Amazon SageMaker 端点管理（HF 模型直接从 HF 拉取）
│   │   └── sagemaker_invoker.py  # 将推理路由到 Amazon SageMaker 端点
│   ├── models/
│   │   ├── style_profile.py       # StyleProfile、AnalyzedStyle、Create/Update
│   │   ├── generation_request.py  # GenerationRequest、AssetType、ImageModel 枚举
│   │   └── generation_result.py   # GenerationResult、OptionResult、VariantResult
│   └── storage/
│       └── local_store.py         # 本地文件系统（兼容 S3 的接口）
├── frontend/
│   ├── index.html           # SPA 入口点
│   ├── css/styles.css       # 深色主题 + 动画
│   └── js/
│       ├── app.js               # SPA 路由 + DOM 缓存 + 导航 + showConfirm()
│       ├── i18n/
│       │   ├── i18n.js          # 核心：t() 函数、语言切换、反向查找
│       │   ├── en.json          # 英语（基础）—— 817 个键
│       │   ├── ja.json          # 日语
│       │   ├── zh.json          # 简体中文
│       │   ├── ko.json          # 韩语
│       │   ├── fr.json          # 法语
│       │   └── es.json          # 西班牙语
│       ├── services/api.js      # 后端 API 客户端
│       └── components/
│           ├── ImageStudio.js   # 2D Image Studio（选项 × 变体）
│           ├── TypeStudio.js    # Type Studio（文字叠加）
│           ├── VideoStudio.js   # Video Studio（文生视频生成）
│           ├── ChatStudio.js    # Chat Studio（多模型 LLM 聊天）
│           ├── Gallery.js       # 画廊网格 + 搜索 + 批量操作
│           ├── StyleLibrary.js  # 风格管理 + 文件浏览器
│           ├── AssetViewer.js   # 全尺寸预览 + 元数据 + 下载
│           ├── ModelSettings.js # 模型注册表管理 UI（模态框）
│           ├── PromptEditor.js  # 双区域提示词编辑器 + compose
│           └── VoiceInput.js    # MediaRecorder + 转写
├── data/
│   ├── styles/              # 风格档案 + 参考图像（符号链接）
│   ├── generated/           # 输出资产（PNG + SVG + metadata.json）
│   ├── video/               # 视频资产（MP4 + 缩略图 + 任务元数据）
│   └── chat/                # 聊天会话（每会话一个 JSON）
├── SPEC.md                  # 完整技术规格说明（重建蓝图）
└── README.md                # 本文件
```

## 📌 11. 可配置的限制

`backend/config.py` 中的设置可通过环境变量（前缀 `ARTSMOKER_`）覆盖：

| 设置 | 环境变量 | 默认值 | 用途 |
|---------|-------------|---------|---------|
| `max_reference_images` | `ARTSMOKER_MAX_REFERENCE_IMAGES` | 100 | 每个风格导入的最大图像数 |
| `max_analysis_images` | `ARTSMOKER_MAX_ANALYSIS_IMAGES` | 20 | 每次分析调用发送给 AI 的最大图像数 |
| `aws_region_models` | `ARTSMOKER_AWS_REGION_MODELS` | us-west-2 | Claude + Stability AI 模型的区域 |
| `aws_region_images` | `ARTSMOKER_AWS_REGION_IMAGES` | us-east-1 | Amazon 服务的区域（Nova Sonic 语音、Nova Reel 视频） |
| `aws_profile` | `ARTSMOKER_AWS_PROFILE` | None | AWS 配置文件名称（未设置时使用默认链） |
| `auto_update` | `ARTSMOKER_AUTO_UPDATE` | true | 启动时 git pull + 24 小时定期检查，更新时自动重启 |

减少 `max_analysis_images` 可降低每次分析的 AI 视觉成本。减少 `max_reference_images` 可限制存储。两者都可以根据预算调整。

## 📌 12. Amazon Bedrock 定价与成本明细

> [!IMPORTANT]
> **模型弃用和变更很快。** 新模型频繁推出、旧模型频繁退役，因此文档中硬编码的任何具体模型名称或价格都会很快过时。ArtSmoker 会自动处理这一点 —— 每次 **Sync from AWS** 都会重新发现当前的模型阵容，将共享 LLM 槽位自动滚动到最新的 Claude Sonnet/Opus，并从 AWS Pricing API 将实时的每模型定价刷新到 `model_registry.json`。**应用才是唯一可信来源** —— 无论是哪些模型存在，还是它们各自的价格（根据您所选的模型、质量档位、区域和批量大小，在 Image Studio 侧边栏中实时显示）。下方的模型名称和任何数字**仅为示例说明** —— 请始终在应用内或官方 [Amazon Bedrock 定价页面](https://aws.amazon.com/bedrock/pricing/)确认当前的模型/价格。

应用的**默认区域**为 `us-west-2`（Claude、Stability AI）和 `us-east-1`（Amazon Nova Sonic、Nova Reel）；价格因区域而异。成本模型另请参阅 [SPEC.md](SPEC.md#14-amazon-bedrock-pricing--cost-breakdown)。

### 📝 12.1 单位定价

哪些操作会产生费用及其计费单位（当前单价请参阅应用内）：

| 服务 | 计费方式 | 说明 |
|---------|--------|-------|
| **LLM 提示词工程与聊天**（Claude Sonnet / Opus，同步时自动滚动到最新版） | 按输入/输出 token | 提示词精调、概念、聊天、风格分析、审核 |
| **Bedrock 图像生成**（Stable Diffusion 3.5 Large、Stable Image Ultra、Stable Image Core） | 按每张图像 | 价格 Ultra ≫ SD 3.5 ≫ Core；实时数字在应用内显示 |
| **自托管图像 / 3D**（FLUX、HunyuanImage、Qwen-Image、TripoSG、TRELLIS.2） | 按您 SageMaker 实例的 GPU 秒 | 空闲时 scale-to-zero（$0）；不按每张图像计费 |
| **后处理**（移除背景、Creative Upscale） | 按每张图像 | Stability AI 服务 |
| **SVG 转换** | 免费 | 本地（vtracer/potrace）—— $0.00 |

> [!NOTE]
> 价格取自官方 [Amazon Bedrock 定价页面](https://aws.amazon.com/bedrock/pricing/)，截至 2026 年 3 月。价格可能变动 —— 在做预算前请始终对照官方来源核实。

### 📝 12.2 额外的 LLM 成本（每次使用）

这些 LLM 调用包含在生成工作流中，但未在下方的批次成本表中单独列出：

| 调用 | 模型 | 何时 | 约成本 |
|------|-------|------|-------------|
| **Prompt Pre-Check** | Claude Sonnet | 生成前（如果切换启用） | ~$0.005 |
| **Moderation Rewrite** | Claude Sonnet | 仅当所有模型都拒绝某提示词时 | ~$0.005 |
| **Type Studio Layout** | Claude Opus | 每次 AI 布局建议请求 | ~$0.02–$0.05 |

这些都很小 —— 预检和审核改写各只花费不到一美分。Type Studio 布局与单选项提示词精调相当。

### 📝 12.3 风格分析成本（每个风格一次性）

每个风格约 **$0.14**（20 张图像发送给 Claude Opus + 8 张图像用 Claude Sonnet 做一致性检查）。一致性检查增加约 $0.01（带 8 张图像的 Sonnet 非常便宜）。

### 📝 12.4 按批量大小的生成成本

包含提示词精调/概念生成 + 图像生成：

| 场景 | Stable Image Core | Stable Diffusion 3.5 Large | Stable Image Ultra |
|----------|-------------------|-------------|-------------------|
| 1 选项 × 1 变体 | ~$0.05 | ~$0.09 | ~$0.15 |
| 1 选项 × 5 变体 | ~$0.21 | ~$0.41 | ~$0.71 |
| 5 选项 × 5 变体 | ~$1.05 | ~$2.05 | ~$3.55 |

自托管 SageMaker 模型（FLUX、HunyuanImage、Qwen-Image）按您自己实例上的 GPU 时间计费（空闲时 scale-to-zero），而非按每张图像 —— 计算成本模型见 [SPEC.md](SPEC.md#14-amazon-bedrock-pricing--cost-breakdown)。

### 📝 12.5 后处理附加项（每张图像）

| 附加项 | 每张图像 | 1 张图像 | 5 张图像 | 25 张图像 |
|--------|-----------|---------|----------|-----------|
| 移除背景 | $0.07 | $0.07 | $0.35 | $1.75 |
| Creative Upscale | $0.60 | $0.60 | $3.00 | $15.00 |
| 转换为 SVG | $0.00 | $0.00 | $0.00 | $0.00 |

> [!TIP]
> **Creative Upscale 说明**：通过内部使用 JPEG 输出格式、然后转换回 PNG，自动处理 Stability AI 的 16MB 响应负载限制。包含针对 API 限流的指数退避重试。

### 📝 12.6 实例计算

| 示例 | 配置 | 总成本 |
|---------|-------------|-----------|
| **最便宜** | 1×1，Stable Image Core，无处理 | ~$0.05 |
| **标准** | 1×5，Stable Diffusion 3.5 Large，移除背景 | ~$0.76 |
| **完整探索** | 5×5，Stable Diffusion 3.5 Large，移除背景 + SVG | ~$3.80 |
| **高端** | 5×5，Stable Image Ultra，移除背景 + 放大 + SVG | ~$20.30 |

> [!TIP]
> **关键要点**：图像生成本身很便宜（$0.01–$0.14/张）。**Creative Upscale $0.60/张是最大的成本因素** —— 请在最终选定的资产上选择性使用，而非对整批使用。移除背景 $0.07/张较为合理。SVG 转换免费（本地运行）。

<a id="disclaimer"></a>

## 📌 13. 免责声明

> [!IMPORTANT]
> **生成内容质量**：ArtSmoker 生成的所有图像、视频和其他资产均由通过 Amazon Bedrock 提供的 AI 模型产出，包括第一方 AWS 模型和第三方模型。生成内容的质量、准确性和适当性完全取决于用户提供的提示词、所选模型和上传的风格参考。ArtSmoker 的作者和贡献者对生成内容的质量、适用性或目的适合性不作任何保证。
>
> **知识产权**：用户须自行全权负责确保其提示词、参考图像和生成输出不侵犯任何第三方知识产权（包括但不限于著作权、商标权和肖像权）。ArtSmoker 是一个工具 —— 它不会过滤、验证或评估输入或输出的知识产权状态。工具作者和贡献者对因使用本软件而产生的任何知识产权侵权不承担任何责任。
>
> **AI 模型和服务条款**：生成内容受通过 Amazon Bedrock 访问的底层 AI 模型供应商的服务条款和可接受使用政策约束。在生产或商业环境中使用生成资产之前，用户应查看 [AWS 服务条款](https://aws.amazon.com/service-terms/)、[Amazon Bedrock SLA](https://aws.amazon.com/bedrock/sla/) 以及各个模型供应商条款。
>
> **费用仅为估算 —— 请自行监控支出**：ArtSmoker 中显示的所有费用（每张图像、每个视频、每个 token、3D 计算、部署以及会话/资产合计）均为**仅供参考的估算值**，根据 AWS 公布价格和预期用量计算得出。它**不是账单，也不保证**您的实际费用。实际成本取决于您的 AWS 账户价格、区域、折扣、税费、数据传输、端点运行时间（包括空闲/预热的 SageMaker 实例）、自动扩缩行为以及本工具无法控制的因素。**您须自行负责监控和控制自己的 AWS 支出** —— 请使用 [AWS 账单控制台](https://console.aws.amazon.com/billing/)、[AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/) 和[预算/账单告警](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)来跟踪并限制实际费用。尤其是自托管的 SageMaker 端点，只要处于部署或预热状态，即使空闲也会持续计费 —— 用完请务必拆除。作者与贡献者对因使用本软件而产生的任何 AWS 费用不承担任何责任。
>
> **无保证**：本软件按"现状"提供，不附带任何形式的保证。完整条款请参阅 [LICENSE](LICENSE)。

## 📌 14. 完整规格说明

请参阅 **[SPEC.md](SPEC.md)** 获取完整的技术规格说明 —— 架构、组件设计、模型配置、API 参考、安全模型、定价、部署路线图，以及足以从零重建项目的详细信息。
