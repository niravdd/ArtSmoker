# ArtSmoker
> *アートワークのスモークテスト！*

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green?logo=fastapi&logoColor=white)
![Amazon Bedrock](https://img.shields.io/badge/Amazon-Bedrock-orange?logo=amazonaws&logoColor=white)
![License](https://img.shields.io/badge/License-MIT--0-yellow)

## 📌 0. 概要

**ArtSmokerは、アイデアをゲームエンジン対応のアートへと変えます — 数分で、あなたが管理すべきパイプラインは一切なしに。** キャラクター、小道具、環境、キーアートを自然言語で説明するだけで、プロダクション対応の2Dアート、完全にテクスチャリングされた3Dモデル、動画が得られます — すべてがプロジェクトのビジュアルアイデンティティに合致し、すべてがあなた自身の環境内に留まります。最新のAI画像・編集・3D・動画モデルが、本物のクリエイティブコントロールを備えた1つのクリーンでアーティストファーストなインターフェースの背後に収まっています：ArtSmokerが制作パイプライン全体をあなたの代わりに動かすため、チームは機械の操作に追われることなく、ルックの方向づけに専念できます。

### 📝 課題

ゲームやメディアのスタジオのクリエイティブチームは、生成AIのレバレッジを求めています — しかし現状、その力は、彼らが本来管理するはずのなかった開発者向けツールの背後に閉じ込められています：

- **アーティストではなくエンジニア向けに作られている** — 最良のモデルは、クラウドコンソール、コマンドライン、SDK、REST APIの背後にあります。ディレクターやコンセプトアーティストが、アート作品を作るためにターミナルを必要とするべきではありません。
- **明確なアイデア、難解なプロンプト** — アーティストは自分が何を求めているかを正確に分かっていますが、モデルは平易なクリエイティブ言語での指示を受け付けません。一貫した、ブリーフに沿った結果は、依然としてプロンプトの構造、ネガティブプロンプト、そしてブリーフと出力の間に横たわるモデル固有の言い回しに左右されます。
- **最良のAIモデルは散在していて、動かすのが難しい** — 画像・編集・3D・動画向けの強力なAIモデルが、さまざまなプロバイダーやフォーマットで絶えずリリースされます。そのそれぞれを立ち上げること（パッケージング、GPU、量子化、スケーリング）は、それ自体が一つの本格的なエンジニアリングプロジェクトです。
- **編集と3Dは別世界** — インペインティング、アウトペインティング、リライティング、参照ガイド編集、そして2Dコンセプトをテクスチャ付き3Dモデルに変えることは、通常それぞれに独自のツール、API、専門家を必要とします。
- **ブランドの統一は手作業** — すべてのアセットを確立されたルックに忠実に保つことは、通常、各生成を手作業で見守ることを意味します。

### 📝 ソリューション

ArtSmokerは、今日最良の生成モデルを1つのアーティストファーストなインターフェースの背後に据えた、セルフホスト型のクリエイティブスタジオです — ゲームアセット制作のために専用設計されつつ、映画、広告、Eコマース、出版、そしてオリジナルのビジュアルコンテンツで成り立つあらゆるチームにも、同じように馴染みます。

- **平易な言葉で説明するだけ** — ArtSmokerが、プロンプトの分解、強化、モデル固有の最適化を裏側で処理します。ガイド付きの**Prompt Designer**では、個々のビジュアル要素（被写体、シーン、照明、色）をロック/バリエーションコントロールで形づくり、すでにうまくいっているものを失うことなく、真に異なる方向性を探れます。
- **デフォルトでブランドに準拠** — ArtSmokerに既存のアートを与えると、そのビジョンモデルがあなたのビジュアルアイデンティティを学習するため、生成されるすべてのアセットがプロジェクトのルック＆フィールに合致します。
- **2Dで、編集し、3Dへ — エンドツーエンド** — 生成し、その場でインペインティング、アウトペインティング、リライティング、検索＆置換、参照ガイド編集で改良できます。任意の2Dアセットを、Unity、Unreal、Blenderに直接ドロップできる**完全にテクスチャリングされた、ゲームエンジン対応の3Dモデル**へと変えます — 手動モデリング、UV展開、テクスチャペイントは不要です。さらに、シネマティックな動画と、アイデア出しのためのマルチモデルチャットスタジオも。
- **あらゆるモデルを、ワンクリックで** — 各リージョンにわたる最新のホスト型モデルを使うか、キュレーションされたオープンソースモデル（Qwen-Image、FLUX.2、HunyuanImage、TripoSG、TRELLIS.2など）を、シングルクリックであなた自身のGPUにデプロイできます — パッケージング、量子化、オートスケーリング、ジョブトラッキングはすべて処理され、すべてのモデルは出荷前にエンドツーエンドで検証されています。
- **好きな場所で動作 — そしてあなたのIPはあなたのもの** — 1人のアーティストのデスクトップにも、チーム全体で共有するインスタンスにもインストールできます。**あなた自身のGPUは不要**です（重い計算はマネージドなAWSサービス上、またはArtSmokerが立ち上げてゼロまでスケールバックしてくれるオートスケーリングエンドポイント上で実行されます）。接続先はあなた自身のAWSアカウントのみ — アートワーク、プロンプト、スタイル、生成されたアセットはあなたの環境内に留まり、サードパーティサービスには何も送られず、クリエイティブIPの完全な所有権を保持できます。

**Amazon Bedrockモデル**：Claude Sonnet/Opus（プロンプトエンジニアリング＆チャット）、Stable Diffusion 3.5 Large、Stable Image Ultra、Stable Image Core、Stability AIサービス（画像編集）、Nova Reel、Luma AI Ray（動画生成）、さらにChat Studio向けに16プロバイダーから80以上のLLM。**セルフホストモデル**：Qwen-Image（テキストから画像へ）＆Qwen-Image-Edit（参照ガイド＋指示編集、Apache-2.0）、HunyuanImage 3.0（BF16/NF4）、FLUX.2、FLUX.1、TripoSG＆TRELLIS.2（画像から3Dへ）など、Amazon SageMaker経由 — 新しいモデルを追加できる拡張可能なカタログ付き。

**[今すぐ始める — 前提条件とインストールへジャンプ ▸](#get-started)**

### Language / 言語 / 语言 / 언어 / हिन्दी / Язык / Langue / Idioma

ArtSmokerは9言語に対応しています。上部ナビゲーションバーの言語ボタン（EN | 日 | 中 | 한 | हिं | РУ | FR | ES | DE）でUI言語を切り替えられます。選択は自動的に保存されます。

| 言語 | README |
|----------|--------|
| English | [README.md](README.md) |
| 日本語 (Japanese) | このドキュメント |
| 中文 (Chinese) | [README.zh.md](README.zh.md) |
| 한국어 (Korean) | [README.ko.md](README.ko.md) |
| हिन्दी (Hindi) | [README.hi.md](README.hi.md) |
| Русский (Russian) | [README.ru.md](README.ru.md) |
| Français (French) | [README.fr.md](README.fr.md) |
| Español (Spanish) | [README.es.md](README.es.md) |
| Deutsch (German) | [README.de.md](README.de.md) |

**多言語プロンプト対応：**
- 英語以外のプロンプト（日本語、中国語、韓国語、ヒンディー語、ロシア語、フランス語、スペイン語など）は自動検出され、生成前に英語へ翻訳されます
- プロンプトエリアにバイリンガルプレビューが表示されます：元のテキストと英語翻訳を切り替えて、モデルが実際に受け取る内容を確認できます
- 元のプロンプト、検出された言語、英語翻訳は、すべてアセットのメタデータに保存されます
- ファイル名は翻訳後の英語プロンプトから生成されます（例：「病院の建物」→ `hospital-building_opt1_var1.png`）
- Chat StudioはプロンプトをLLMに直接渡します（翻訳なし）— Claudeなどのモデルはネイティブに多言語対応しているためです
- Type Studioのテキストはあなたの言語のまま残ります（画像にそのままレンダリングされます）
- すべてのモデレーション事前チェックとコンテンツスクリーニングは、一貫性のために翻訳後の英語プロンプトに対して動作します

## 📌 1. 機能概要

ArtSmokerは2つのモードで動作します — **スタンドアロン**（アートスタイルやテーマの設定は不要、説明して生成するだけ）と、**スタイルガイド**（既存のアートをアップロードすると、すべての生成がビジュアルアイデンティティに合致）。両モードとも、同じスタジオと生成パイプラインを使用します。

### 📝 スタンドアロンモード（クイックスタート）

スタイルやテーマの設定は不要 — 2D Image Studio、Video Studio、またはType Studioを開いて、すぐに制作を開始できます。

1. **必要なものを説明** — 「hospital building」や「fire mage character」のようなプロンプトを入力するか、音声入力を使用します。AIがアイデアをビジュアルコンポーネントに分解し、モデル固有の最適化で強化し、スマートなロック/バリエーションコントロールでクリエイティブな意図を尊重します。どの言語でも入力可能 — 英語以外のプロンプトは自動翻訳されます。
2. **モデルと設定を選択** — 利用可能なすべてのテキストから画像へのモデル（Amazon Bedrock＋SageMakerセルフホスト）からマルチセレクトで選び、サイズ、品質ティア、リージョンを選択します。複数モデルをチェックして横並びで比較したり、1つを選んで集中的に生成したりできます。コスト見積もりはリアルタイムで更新されます。
3. **真に異なるオプションを取得** — システムは最大5つの明確に異なるクリエイティブコンセプト（衣装、ムード、照明、構図を変化させる — カメラアングルだけではありません）を生成し、それぞれに最大5つのシードバリエーション（合計25画像）を持たせます。ユーザーが指定した詳細はロックされ、AIが推論した詳細は大胆に変化させます。
4. **編集と改良** — Asset Viewerで、インペインティング、アウトペインティング、消去、検索＆置換、リカラーを直接使用できます。各編集は新しいバージョンを作成します — オリジナルは常に保持されます。
5. **ゲーム対応ファイルをダウンロード** — 透明背景のPNG＋SVG、説明的な名前付き（例：`hospital-building_opt2_var3.png`）。動画はMP4でエクスポートされます。

### 📝 スタイルガイドモード（アートスタイルとテーマに合わせる）

生成されるすべてのアセットを既存のアートスタイルに合わせたいチーム向け — リファレンス画像をアップロードして、まずAIにビジュアルアイデンティティを学習させます。

1. **ゲームのアートをアップロード** — ローカルディレクトリ（再帰スキャン、重複回避のためシンボリックリンク）またはS3バケット（ページネーション付き再帰リスト）からリファレンス画像をインポートします。**スマート重複排除**が自動的に実行されます — 回転バリアント（barrel_N/E/S/W.pngからbarrel_S.pngのみを保持）とアニメーションフレーム（Idle0-Idle8からIdleのみを保持）を除去します。例えば、747ファイルのアイソメトリックアセットパックは約99のユニークオブジェクトに重複排除されます。対応形式：.png、.jpg、.jpeg、.gif、.bmp、.webp、.tiff、.tif、.tga、.ico、.svg、さらに3Dモデル（.glb、.gltf）からの自動テクスチャ抽出。
2. **AIがスタイルを学習** — 2フェーズのコヒージョン認識分析：まず、コレクションが統一されているか、構造的に一貫しているか、多様かを判定するクイックチェック。次に、完全なリファレンスセットの詳細分析が、メタデータリッチなスタイルプロファイル — カラーパレット、線の太さ、照明パターン、構図ルール、制作規約 — を生成します。生成ヒントを提供すると、AIはそれを「アーティストのガイダンス」として受け取り、分析が見た目だけでなく意図も理解できるようになります。
3. **スタイルを適用して生成** — Image Studioでスタイルを選択すると、すべてのプロンプトがスタイルのビジュアル指示で自動的に強化されます。「hospital building」のようなプロンプトが、ゲームのカラーパレット、パースペクティブ規約、レンダリングスタイルを含む詳細な生成指示になります。
4. **スタンドアロンモードのすべてが適用** — 複数オプション、モデル比較、編集、バージョニング、ゲーム対応ダウンロードは、すべて同じように機能し、今度はあなたのアートスタイルによってガイドされます。

> [!NOTE]
> 生成されるすべてのコンテンツはAIモデルによって作成され、提供するプロンプトとリファレンスに依存します。本番環境で生成アセットを使用する前に、コンテンツ品質、知的財産、適用されるサービス条件に関する[免責事項](#disclaimer)をご確認ください。

### 📝 1.1 機能一覧

- 🎨 **Style Library** — アートをアップロードすると、AIがビジュアルアイデンティティを学習
- 🖼️ **2D Image Studio** — オプション×バリエーションで画像を生成、ガイド付き3ステッププロンプトワークフロー
- 🎨 **Prompt Designer** — AIがプロンプトを編集可能なビジュアルコンポーネント（被写体、シーン、照明、色）に分解、フィールドごとのロック/バリエーショントグル、スタイル統合、スマートなアセットタイプ分類。Photorealistic、Character、Environmentなど
- 🎬 **Video Studio** — モデル固有のプロンプトガイダンス（Nova Reelのカメラコントロール、Luma Rayの自然言語）付きのテキストから動画へ、マルチショット、画像から動画へ
- ✍️ **Type Studio** — フォントピッカー付きのAIデザインテキストオーバーレイ
- 💬 **Chat Studio** — ストリーミング、Markdown、コードハイライト、ビジョン、セッション、コンテキスト圧縮を備えたマルチモデルLLMチャット
- 📁 **統合ギャラリー** — 各アセットを本来のアスペクト比（縦長、正方形、横長 — 決してクロップしない）で表示するメイソンリーレイアウト。画像＋動画の閲覧、メディアフィルター（All / 2D Artwork / 3D Models / Video）、検索、完全な日付・時刻・タイムゾーンのタイムスタンプ、ダウンロード、削除。すでに生成済みの3Dモデルを持つアセットには**3Dバッジ**が付き、**3D Models**フィルターはそれらだけを表示します
- 📥 **画像インポート** — 既存の画像（任意の形式）をギャラリーに第一級のアセットとして取り込みます。自動的にPNGへ変換され、選択したアセットタイプが付与され、すぐに編集・3D化が可能になります — 生成画像とまったく同じように、すべて（バージョニング、編集、画像から3Dへ）が機能します
- ✏️ **画像編集** — インペインティング、アウトペインティング、消去、検索＆置換、リカラー（AssetViewer内）。各モードにはAI**プロンプト生成**ボタンがあり、ビジョンモデルが画像＋元プロンプトを読み取り、そのモードと選択中の編集モデルに合わせた編集プロンプトを提案します（Stability編集モデルには説明的なキャプション、Qwen-Image-Editには指示文）。拡張/アウトペイントは、確定前にキャンバスがどこまで拡大するかをピクセル定規付きでライブに成長するフレームプレビューで表示します。指示型エディタ（Qwen-Image-Edit）は、**5つのモードすべてをマスク不要**でサポートします — 真のキャンバス拡張も含みます：ArtSmokerがキャンバスを事前パディングし、モデルに新領域のみを補完させ、元のピクセルはそのままブレンドで戻します。編集された各バージョンには、元の生成モデルとそのバージョンを編集したエディタの**両方のタグ**が表示されます
- 📤 **エクスポート＆切り抜き** — AssetViewer内のバージョンごとのエクスポート成果物：背景除去済みの透過PNG切り抜きと、真のベクターSVGトレース（背景あり/なし）。背景除去は実行ごとにあなたが選択できます：**無料のオンデバイス処理**（rembg/u2net、クラウドコストなし）または**有料のAmazon Bedrock**リムーバー — 3D生成用に画像を準備する際にも同じ選択肢が提供されます
- 🔄 **リアルタイム進捗** — リトライ/スロットルの可視化を備えたSSEストリーミング
- 🛡️ **スマートモデレーション** — カナリアテスト、自動モデル切り替え、AI支援リライト
- ⚙️ **Model Registry** — スタジオ別に整理された管理UI（Image、Video、Chat、Type、Shared）、Bedrock検出、カスタムモデルサポート
- 📝 **Prompt Templates** — 28の編集可能なLLM指示プロンプト、AI支援による改良、自動修正付きの変数検証
- 📦 **アセットバージョニング** — バージョン履歴（v1、v2、…）付きのインプレース編集、バージョンナビゲーション、バージョン単位の削除：1つのバージョンだけを削除（他は番号を維持）でき、ビューアは前のバージョンに切り替わります — 最後のバージョンを削除するとアセット全体が削除されます
- 💰 **コスト追跡** — リクエスト、セッション、アセットごとの推定AWS支出。リージョン別のライブAWS料金から算出。セルフホストモデルは（誤解を招く画像単価ではなく）GPUインスタンスの時間あたり稼働料金＋標準的な生成時間を表示
- 🌐 **9言語i18n** — 完全なUI翻訳（EN、JA、ZH、KO、HI、RU、FR、ES、DE）、非英語プロンプトの自動検出（英語UIでは検出を完全にスキップ）、バイリンガルプレビュー
- 🔍 **カスタムモデルサポート** — ファインチューニング済み、インポート済み、デプロイ済みのカスタムBedrockモデルを自動検出
- 🔧 **Self-Hosted Models — ワンクリックデプロイ** — テスト済みオープンソースモデル（Qwen-Image、Qwen-Image-Edit、HunyuanImage 3.0、FLUX.2、FLUX.1、TripoSG、TRELLIS.2など）のキュレーションカタログを閲覧し、GPUインスタンスを選択してDeployをクリック。ArtSmokerが、推論ハンドラーのパッケージング、量子化の設定、適切なCUDAツールキットの選択、オートスケーリングの設定、CloudWatchアラームの登録、非同期ジョブトラッキングの接続まで、すべてを処理します。カタログの全モデルは、コールドスタートから生成、ギャラリー配信までエンドツーエンドで検証済みなので、GPUドライバー、メモリオーバーフロー、コンテナ互換性のデバッグは不要です。最高品質のためのBF16＋FlashInfer、コスト効率のためのNF4、マルチGPU自動検出をサポートし、ゼロまで自動スケール（アイドル時$0）し、同じモデルが再設定なしで異なるインスタンスタイプで動作します
- 🧊 **Image-to-3D生成** — 任意のGame AssetまたはCharacter画像を、ワンクリックでテクスチャ付き3Dメッシュ（GLB）に変換。マルチビュー合成＋テクスチャベイキングにより、ゲームエンジン対応のアセットを生成します。オービット/ズーム/パン操作が可能なインタラクティブ3Dビューア付き
- 🩹 **3D向けスマートソース補完** — 画像から3Dへの変換は見えている部分しか構築できないため、見切れたキャラクター（脚が切れている等）は脚のないメッシュになります。生成前に、ArtSmokerはソースをビジョンでチェックし、見切れている場合は、アウトペインティングによる補完（AIが提案し、完全に編集可能なプロンプト）を**提案**します — 補完前後をプレビューし、結果を再レビューし、再度拡張するか破棄するかを選べ、新しい画像バージョンとして保存します。オプトインかつ非ブロッキングで、うまくフレーミングされた画像はそのまま生成されます
- 🔄 **Auto-Update** — 起動時のバージョンゲート付きgit pull、更新時の自動再起動、24時間ごとの定期チェック（`ARTSMOKER_AUTO_UPDATE=false`で無効化）

### 📝 1.2 スクリーンショット

**2D Image Studio** — 左側にマルチセレクトモデルドロップダウン、アセットタイプ、サイズ、後処理オプションを備えた設定。右側にPrompt DesignerとGenerate Enhanced Promptボタンを含む3ステッププロンプトワークフロー。下部にIP宣言とコスト見積もり。

![2D Image Studio — Settings, prompt workflow, and generation controls](docs/images/image-studio-top.png)

**2D Image Studio — 生成結果** — 上部にエンハンスドプロンプト、下部にマルチモデル比較結果。各モデルは、モデルごとのプロンプト最適化で独立して生成します。結果にはモデル名、サイズ、生成コストが表示されます。

![2D Image Studio — Enhanced prompt and generation results](docs/images/image-studio-results.png)

**2D Image Studio — モデル比較** — 選択したすべてのモデル（8モデルを表示 — Amazon Bedrockもセルフホストも同様に）の横並び比較グリッド。各オプションカードは独自のバリエーションフィルムストリップを持ち、選択中のオプションにはモデルごとのネガティブプロンプトが表示されます。後処理トグル（背景削除、SVG変換、アップスケール）は再生成なしで既存の結果に適用できます。

![2D Image Studio — Multi-model comparison grid with variations](docs/images/image-studio-comparison.png)

**Image Inspiration（リファレンス誘導）** — 1〜3枚のリファレンス画像をドロップし、やりたいことを記述して、使い方を選択：**Match the reference**（デプロイ済みの画像編集モデルによるピクセル忠実な編集）または**Inspired by the reference**（ビジョンAIが強化プロンプトを作成 — 任意のモデル選択・オプション・バリエーションで動作）。導出されたプロンプトは生成前にプレビューでき、完全に編集可能です。

![Image Inspiration — reference images, instruction, and the editable enhanced-prompt preview](docs/images/image-inspiration.png)

**Image Inspiration — 結果** — リファレンスが新しい作品になります（ここではリファレンス写真から描かれた似顔絵）。モデルに送信された正確なプロンプトと画像ごとのコストが記録されます。

![Image Inspiration — generated caricature results from a reference image](docs/images/image-inspiration-results.png)

**Prompt Designer** — AIがプロンプトを編集可能なビジュアルコンポーネント（Subject、Scene、Composition、Lighting、Style & Colors）に分解します。各フィールドは、真に異なるクリエイティブオプションのためのロック/バリエーションコントロールで個別に編集できます。

![Prompt Designer — Structured visual decomposition with editable fields](docs/images/prompt-designer-top.png)

**Prompt Designer — カラーパレット** — 16進スウォッチ付きの名前付きカラーパレット、スタイルキーワード、品質レベルコントロール。AIがビジュアルアイデンティティを学習し、すべての生成に一貫して適用します。

![Prompt Designer — Color palette, style keywords, and quality controls](docs/images/prompt-designer-bottom.png)

**Style Library** — ゲームの既存アートをアップロードすると、AIがビジュアルスタイルを分析し、メタデータリッチなプロンプトガイドを生成します。リファレンス画像は、完全なAI分析とJSONスタイルプロファイルとともに表示されます。

![Style Library — AI style analysis with reference images](docs/images/style-library-top.png)

![Style Library — Reference images, import options, and analysis data](docs/images/style-library-bottom.png)

**ギャラリー** — メディアタイプフィルター、スタイルフィルター、検索、ソートを備えた、生成済みの全画像と動画の統合ビュー。任意のアセットをクリックするとフルビューアが開きます。**画像インポート**ボタンで既存の画像をギャラリーに取り込めます — アセットタイプ（Character/Game Assetは3Dを有効化）を選ぶと、PNGに変換され、すぐに編集・3D化が可能になります。

![Gallery — Generated assets grid with filters](docs/images/gallery.png)

**Asset Viewer** — タブ付きインターフェース（PNG、Edit、Export & Cutouts、Metadata、3D Model）、画像バージョンバー、PNG/SVGの直接ダウンロードを備えたフルサイズプレビュー。チェッカーボード合成画像上のズーム/フィット/計測コントロール。

![Asset Viewer — Full-size preview with download options](docs/images/asset-viewer.png)

**Asset Viewer — 画像編集** — 5つの編集モード：Fill/Replace、Remove、Extend、Find & Replace、Recolor。表示中：計測ルーラー、辺ごとのピクセル量、画像を読み取って編集プロンプトを書いてくれる ✨ Generate Prompt ボタンを備えた**Extend**。バージョン履歴が保持され、オリジナルが上書きされることはありません。

![Asset Viewer — Extend editing with measurement ruler and AI-suggested prompt](docs/images/asset-viewer-edit.png)

**Asset Viewer — Export & Cutouts** — ゲーム・エンジン・デザインツールにすぐ使えるバージョンごとのアーティファクト：フル画像のベクターSVG、背景除去済みカットアウトPNG、カットアウトSVG。背景除去はデバイス上で無料実行（有料のAmazon Bedrockパスも選択可能）。

![Asset Viewer — Export & Cutouts with vector SVG and background-removed cutouts](docs/images/asset-viewer-export-cutouts.png)

アウトペインティング後（下のv3）、同じタブが改善された全身バージョンの3つのアーティファクトすべてを再生成します。

![Asset Viewer — Export & Cutouts for the outpainted full-body version](docs/images/asset-viewer-export-cutouts-outpainted.png)

**Asset Viewer — Metadata** — 完全なプロンプト系譜（あなたのプロンプト → Prompt Designer分解 → 再構成プロンプト → モデル向けに調整された洗練プロンプト）、生成詳細、コスト内訳、完全なバージョン履歴。

![Asset Viewer — Metadata with full prompt lineage and version history](docs/images/asset-viewer-metadata.png)

**3Dモデル生成** — Asset Viewerの3D Modelタブ：デプロイ済みパイプラインのエンドポイント、品質ティア（推定時間とコスト付き）、詳細パラメータを選択。ライセンスパネルには各パイプラインの条件が表示され、**Improve the Source**がGPU時間を使う前に画像をビジョンチェックします。

![3D Model Generation — Settings and generation in the Asset Viewer](docs/images/3d-model-generation.png)

**Improve the Source** — 生成前に、ArtSmokerが被写体のシルエットを計測して切れ（ここでは下端で切断）を検出し、拡張量とAIが書いたアウトペイントプロンプトを提案 — 拡張、塗りつぶし、またはそのまま使用できます。

![3D source review — automatic crop detection with suggested extension](docs/images/3d-source-review.png)

**3Dビューア + エンジン対応エクスポート** — テクスチャ付きメッシュをオービットで確認し、エンジン向けに準備：ターゲットプリセット（Unreal、Unity、Godot、Blender、3ds Max…）、テクスチャパッキング、LODチェーン、コリジョンメッシュ、ライトマップUV2 — ヘッドレスBlenderでローカル変換され、ダウンロード可能な組み合わせはバージョンごとに記憶されます。

![3D Model viewer with per-variant tools and engine-ready FBX/USD export options](docs/images/3d-model-viewer-export.png)

**3Dバリアント** — 画像バージョンごとに複数の3Dテイクを保持（ここではTripoSGとTRELLIS.2フルパイプライン）し、いつでも切り替えやデフォルト設定が可能。各バリアントは生成に使用した正確なモデルとツールを記録します。

![3D variants — TripoSG and TRELLIS.2 takes side by side with full provenance](docs/images/3d-model-variants.png)

**Video Studio** — 左側に設定（モデル、生成モード、長さ、リージョン、コスト見積もり）、右側にプロンプト。Nova Reel（シングルショット、最大2分のマルチショット自動/手動）とLuma AI Ray（アスペクト比、ループ）に対応。

![Video Studio — Settings and prompt](docs/images/video-studio.png)

![Video Studio — Generation in progress with AI-enhanced prompt](docs/images/video-studio-generating.png)

![Video Studio — Completed video with thumbnail and recent videos](docs/images/video-studio-completed.png)

**動画プレイヤー** — 動画をクリックすると、完全なメタデータ（元のプロンプト、AI強化プロンプト、モデル、長さ、リージョン）とともにインラインで再生します。

![Video Player — Playing a generated video with metadata](docs/images/video-player.png)

### 📝 1.3 2段階生成

各プロンプトに対して、AIは**オプション** — 根本的に異なるデザイン解釈（例えば「a warrior」の場合：ヴァイキングのバーサーカー、日本のサムライ、部族の戦士、サイバーソルジャー、ギリシャのホプリタイ）を作成します。各オプションに対して、画像モデルは**バリエーション** — 微妙な視覚的違いを与える異なるランダムシード — を生成します。これにより、アーティストは選択できる幅広いクリエイティブパレットを得られます。

### 📝 1.4 マルチモデル選択

モデルドロップダウンは**チェックボックスベースのマルチセレクト**に対応しています — 1回の生成実行で任意のモデルの組み合わせを選べます：

- **単一モデル** — 1つのモデルをチェックして集中生成（最速、最安）
- **複数モデル** — 2〜3の特定モデルをチェックして対象を絞った比較（例：SD 3.5 + FLUX.2のみ）
- **All Available Models** — 下部のトグルで、有効なすべてのモデルを選択/解除し、完全な横並び比較を行います

各モデルは独立して実行されます：より厳格なモデルがプロンプトをブロックしても、受け入れたモデルからの結果は得られ、各オプションカードに明確なステータスラベル（成功、モデレーションによるブロック、失敗）が表示されます。コスト見積もりは、モデルのチェック/チェック解除に応じてリアルタイムで更新されます。

オプションの**「Model-optimized prompts」**トグルは、各モデルの強みに合わせてプロンプトを調整します — プロンプトはモデルごとに書き換えられます（例：SD 3.5には品質ブースター、FLUX.2には自然言語、Qwen-Imageにはクラス最高のテキスト描画キュー）。

### 📝 1.5 参照ガイド生成

プロンプトをゼロから書く以外にも、**1〜3枚のリファレンス画像と指示**から生成できます — Image Studioのプロンプトエリア上部のセグメントコントロールでモードを選びます：

- **リファレンスに合わせる（Match the reference）** — リファレンスの被写体、製品、キャラクターを保ちつつ、それ以外（テーマ、背景、衣装、照明）を指示どおりに変更します。シーンをまたいだ一貫したキャラクターや製品ショットに最適。このモードはセルフホスト型の指示エディタ（Qwen-Image-Edit）で動作し、**デプロイ済みになると**表示されます — 未デプロイの場合、ArtSmokerはCustom Modelsからのデプロイ（ワンクリック、3Dパイプラインと同じフロー）へ直接誘導します。商用利用安全（Apache-2.0）。
- **リファレンスにインスパイアされる（Inspired by the reference）** — ArtSmokerのビジョンAIがリファレンスと指示を読み取り、エンハンスドプロンプト（先にあなたに表示）を作成し、通常のテキストから画像へのモデルで生成します。**常に利用可能** — デプロイ不要です。被写体をコピーせずに、ルック、パレット、構図を借りたいときに最適。

どちらのモードも指示を必要とし、リファレンスを*何のために*使うかをあなたがコントロールし続けられます。参照ガイド生成は、Style Library（多数の画像を再利用可能なスタイルプロファイルに分析するもの）とは別物です — 単発の画像駆動生成に使います。

### 📝 1.6 Video Studio

テキストプロンプトからAI駆動の動画やアニメーションを生成します。**Amazon Nova Reel**（v1.0、v1.1）と**Luma AI Ray**（v2.0）に対応。

| 機能 | Nova Reel | Luma Ray v2 |
|---------|-----------|-------------|
| **最大長** | 120秒（2分） | 9秒 |
| **解像度** | 1280x720 | 720p / 540p |
| **アスペクト比** | 16:9のみ | 7オプション（1:1、16:9、9:16など） |
| **画像から動画へ** | はい（開始フレーム） | はい（開始＋終了フレーム） |
| **ループ動画** | なし | はい |
| **マルチショット制御** | はい（自動＋手動） | なし |
| **価格** | ～$0.08/秒 | ～$1.50/秒 |

**仕組み：**
1. 動画モデルを選択し、長さ、アスペクト比、リージョンを設定
2. プロンプトを入力 — AIが映画的な語彙、カメラワーク、時間的一貫性のキューで強化
3. Generateをクリック — ジョブは`StartAsyncInvoke`を通じて非同期に実行され、出力は設定したS3バケットへ
4. 5秒ごとにステータスをポーリング — 完了時、サムネイルが抽出され（ffmpeg経由）、MP4がローカルにダウンロードされます（またはS3からストリーミング）
5. 動画は、Video Studioの「Recent Videos」セクションと統合ギャラリーの両方に表示されます

**S3バケットが必要**：動画生成はS3に出力します。UIのVideo Settingsで設定する（既存バケットの参照または新規作成）か、CLIで作成できます：

```bash
# Create an S3 bucket for video storage (replace REGION and YOUR_ORG)
aws s3api create-bucket --bucket artsmoker-video-YOUR_ORG --region us-east-1

# For regions other than us-east-1, add the LocationConstraint:
aws s3api create-bucket --bucket artsmoker-video-YOUR_ORG --region us-west-2 \
  --create-bucket-configuration LocationConstraint=us-west-2
```

ストレージモード：ローカルにダウンロード（デフォルト）、またはオンデマンドでS3からストリーミング。

**動画プロンプト強化**：LLMがカメラワーク（パン、ズーム、ドリー、トラッキング）、照明の詳細、時間的キューを追加します。動画モデルはネガティブプロンプトをサポートしないため、回避すべきコンセプトはポジティブプロンプトに自然に織り込まれます。

### 📝 1.7 Chat Studio

フル機能のLLMチャットインターフェース — セルフホスト型の対話AIのように、サードパーティのデータアクセスなしで、あなた自身のAWSアカウント上で動作します。

**16プロバイダーから80以上のモデル** — Claude（Sonnet、Opus、Haiku）、Amazon Nova、Meta Llama、Mistral、Cohere、Qwen、DeepSeek、Google Gemma、NVIDIA Nemotronなど。さらにアカウント内の任意のカスタム/インポートモデル。すべてSync from AWSで自動検出されます。

**コア機能：**
- **ストリーミングレスポンス** — Bedrock ConverseStreamによるリアルタイムのトークン単位レンダリング
- **Markdownレンダリング** — 見出し、太字/斜体、リスト、テーブル、引用、水平線
- **コードブロック** — 言語バッジ＋コピーボタン付きのシンタックスハイライト（highlight.js）
- **メッセージごとのメトリクス** — 入力/出力トークン、レイテンシ、推定コスト、使用モデル
- **コンテキストウィンドウバー** — 使用/最大トークン数付きの視覚的な充填インジケーター（緑/黄/赤）
- **リージョン切り替え** — 各モデルが利用可能なすべてのリージョンを表示、最も近いまたは最も安いものを選択

**セッション管理：**
- 自動保存付きの複数同時セッション
- サイドバーでのインライン名前変更、複製、削除、検索/フィルター
- 会話をMarkdownとしてエクスポート
- セッション合計：トークン数、推定コスト、メッセージ数

**高度な機能：**
- **システムプロンプトテンプレート** — General Assistant、Coding Expert、Creative Writer、Game Designer、Data Analyst、Technical Writer
- **ビジョン/マルチモーダル** — ビジョン対応モデル向けに、ドラッグ＆ドロップ、ファイルピッカー、Ctrl+Vでの画像貼り付け
- **コンテキスト圧縮** — AIが古いメッセージを要約し、コンテキストウィンドウの空きを確保
- **再生成** — 任意のAIレスポンスを同じプロンプトで再実行
- **編集＆再送** — 任意のユーザーメッセージを修正し、その時点からリプレイ
- **フォーク** — 任意のメッセージから会話を分岐し、新しいセッションを作成

**料金の透明性：** モデルピッカーは1Kトークンあたりのコストを表示し、料金情報バーは10Kおよび100Kトークンの会話の推定コストを表示します。

### 📝 1.8 アセットタイプ認識

選択された**アセットタイプ**は、AIがプロンプトをどう解釈するかを根本的に変えます — 画像モデルだけでなく、パイプラインのすべての段階で。「hospital」と入力して異なるアセットタイプを選択すると、まったく異なる出力が得られます：

| タイプ | 構図 | フレーミング | 技術的アプローチ |
|------|-------------|---------|-------------------|
| **Game Asset** | 透明背景に単一の分離されたオブジェクト。シーン、テキスト、UIなし。 | 正面またはアイソメトリック、オブジェクトがフレームの70〜80%を占める。 | 背景除去用のクリーンでシャープなエッジ、一貫した左上からの照明、地面の影なし。さまざまなスケールで他のゲームアセットと合成できるよう設計。 |
| **Character** | クリーンな背景に分離された、フルボディまたは3/4ボディのフィギュア。キャラクターは1体のみ。 | キャラクターが縦の60〜75%を占め、頭からつま先まで、やや中心からずらして。 | 強く読みやすいシルエット（シルエットだけで識別可能）、パーソナリティを伝える表現力のあるポーズ、明確な顔の特徴と衣装のディテール。 |
| **Icon** | 単一の大胆で認識しやすいシンボル、たっぷりのパディングで中央配置。最大限のシンプルさ。 | 正面またはわずかな3/4傾き、エッジに余白。 | 64x64ピクセルで明確に読めること。高コントラスト、最大3〜5色、大胆な形状、細い線や細かいディテールなし。 |
| **Marketing Banner** | ドラマチックな構図のフルシーンイラスト。片側にクリーンなテキストセーフゾーンを確保 — レンダリングされたテキストやタイポグラフィはなし。 | ワイドでシネマティックな印象、シーンを見せるためにカメラを引く。 | 豊かで彩度の高い色、ドラマチックな照明（リムライト、ボリューメトリックレイ）、被写界深度。AIはテキストをレンダリングしないよう明示的に指示され、テキストセーフゾーンはデザインツール（Figma、Canvaなど）でのポストプロダクションオーバーレイ用にクリーンに保たれます。 |
| **Environment** | 前景/中景/背景の深度レイヤーとリーディングラインを持つフルランドスケープ。 | ワイドなエスタブリッシングショット、地平線は上部または下部の3分の1に。 | 大気遠近法（遠いオブジェクトはより明るく/かすんで）、ディテールによる環境ストーリーテリング、ムードを設定する照明。 |

これはすべての段階で重要です：

- **「Preview Enhanced Prompt」ボタン** — Composeをクリックすると、AIはアセットタイプを使ってあなたの概要を詳細な生成プロンプトへと作り替え、あなたの言葉をスタイルガイドラインとアセットタイプ指示と組み合わせます。あなたの明示的な意図は、常にスタイルのデフォルトよりも優先されます。生成前に、構成されたバージョンを確認できます。
- **コンセプト生成** — 複数のオプションを生成する際、AIはアセットタイプの構造ルールをすべて尊重するN個の異なるデザイン解釈を作成します。Characterオプションは常に読みやすいシルエットを持ち、Marketing Bannerオプションは常にレンダリングされたテキストのないテキストセーフゾーンを持ちます。
- **結果** — 同じプロンプトでもアセットタイプが異なる2つの画像は、まったく似ていないものになります。Game Assetの「warrior」は中央配置の単一キャラクタースプライトです。Marketing Bannerの「warrior」は、ヘッドラインオーバーレイ用のクリーンゾーンを備えたエピックなバトルシーンです。

### 📝 1.9 3Dモデル生成（Image-to-3D）

任意の2D画像から、完全にテクスチャリングされた3Dメッシュを生成します — Asset Viewer内で直接。**Game Asset**または**Character**画像を選択し、**3D Model**タブを開いてGenerateをクリックします。結果は、オービット・ズーム・ダウンロードが可能な、ゲームエンジン対応のGLBです — 手動モデリング、UV展開、テクスチャペイントは一切不要です。

**生成されたモデル — オービット、検査、ダウンロード：**

![3D Model Generation — the generated soldier mesh viewed from multiple angles in the interactive 3D viewer](docs/images/3d-model-result.png)

1枚の2Dキャラクター画像（左、PNGタブ）が、ブラウザ内で自由に回転できる完全テクスチャ付き3Dメッシュになります。**3D Model**タブには、各アセットの生成に使用した正確な**モデルとツール**（ジオメトリモデル、テクスチャリングバックエンド、出力タイプ、インスタンス、生成パラメータ）も一覧表示され — アセットのメタデータに保存されて完全なプロベナンスを提供します。

**2つのパイプライン — 選べるのはあなた。** ArtSmokerは、画像をテクスチャ付き3Dモデルに変換する方法を2通り用意しています。Custom Modelsからどちらか（または両方）をデプロイできます。両方が稼働している場合は、Asset Viewerで生成ごとに選択します — 各オプションには推定コスト、時間、ライセンスが表示されるため、情報を踏まえて判断できます：

| パイプライン | 仕組み | ライセンス | 商用利用 | 最適な用途 |
|----------|--------------|---------|----------------|----------|
| **TripoSG + テクスチャバックエンド** | TripoSGがメッシュを構築し、選択したテクスチャバックエンド（TRELLIS.2 / Hunyuan3D-Paint）がペイント | バックエンドごと（下記参照） | バックエンドごと | ジオメトリ＋特定のテクスチャラーの組み合わせ |
| **TRELLIS.2（フル）** | 1つのモデルがジオメトリとPBRテクスチャの**両方**を生成（SLAT） | MIT | ✅ 可 — 「Built with DINOv3」のクレジット表記 | プロダクション、商用アセット、最もシンプルな経路 |

**TripoSGパイプラインの仕組み：**

1. **ジオメトリ抽出** — レクティファイドフロートランスフォーマー（TripoSG、15億パラメータ、MITライセンス）が、符号付き距離場（SDF）表現を用いて、単一の2D画像を高忠実度の3Dメッシュに変換します。メッシュ密度は品質プリセットに応じてスケールし（最高オクツリー解像度で最大約100万フェイス）、顔や装備の鮮明なディテールを実現します。
2. **テクスチャリング** — メッシュは、**デプロイ時に選択したテクスチャバックエンド**（デフォルトは**TRELLIS.2**、Microsoft、MIT — 4096²アトラスで完全なPBRマテリアルを生成するSLAT/ボクセル条件付きテクスチャラー）でペイントされます。
3. **PBR出力** — PBRマップを埋め込んだGLBとしてエクスポートされ、最新のあらゆるエンジンで物理ベースレンダリングにすぐ使えます。

**TRELLIS.2（フル）**パイプラインは、これと同じ処理を1つのモデルでエンドツーエンドに行います — 別途のテクスチャリングステップはありません。

**ライセンスを一目で確認 — デプロイ時にも、生成時にも。** デプロイ可能な各オプションは、デプロイダイアログで**ライセンスと依存関係の全内訳**を表示します — 取得するすべてのモデル、そのモデルのライセンス、商用OKかゲート付きか — デプロイ前に内容を読んで同意します。生成時には、Asset Viewerがライセンスを再度提示し、*「`<date>`にデプロイ時に同意済み」*と確認します（2度目のクリックは不要）：

| テクスチャバックエンド | ライセンス | 商用利用 | 最適な用途 |
|---------|---------|----------------|----------|
| **TRELLIS.2** *(デフォルト)* | MIT | ✅ 可 — 製品に「Built with DINOv3」のクレジット表記が必要 | プロダクション、商用アセット、最高品質 |
| **Hunyuan3D-Paint** | Tencent Community | ❌ 非商用 | 研究/非商用、卓越した顔の再現 |

背景除去（切り抜きステップ）は、デフォルトで**BiRefNet（MIT）**を使用します — 完全に商用クリーン — で、開示済みのオプトインとして非商用の代替（RMBG）も利用できます。ArtSmokerは、制限付きの依存関係を黙って取得することは決してありません：ゲート付きまたは非商用のものはすべて名称が明示され、バッジが付き、明示的な同意を経なければ利用できないようゲートされます。

**出力：** PBRテクスチャを埋め込んだ標準GLB — Unity、Unreal Engine、Blenderなどのゲームエンジンに直接インポートできます。インタラクティブ3Dビューアはオービット、ズーム、パンに対応し、すぐに検査できます。**3D Model**タブには、使用した正確なモデルとツール（ジオメトリモデル、テクスチャリングバックエンド、依存関係、インスタンス、パラメータ）が一覧表示され、完全なプロベナンスを提供します。

**インフラ：** どちらのパイプラインも同じワンクリックCustom Modelsフローでデプロイし、デプロイ時のピッカーが各オプションのライセンス、依存関係テーブル、インスタンスのベースライン、推定コスト/時間を表示します。完全なTRELLIS.2パイプラインの最適なベースラインは**`ml.g6e.xlarge`**（～$2.61/時間。実測ピークはVRAM約6.5 GB＋ホストRAM約22 GB — ボトルネックはGPUではなくホストRAMです）。より大きな`g6e`サイズは、RAMの余裕を増やすアップセルとして提供されます。エンドポイントはアイドル時にゼロにスケールします — ジョブ間のコストは$0。初回のコールドスタート時に一度だけCUDA拡張をビルドします（以降はS3にキャッシュされ、高速に再起動します）。ゲート付きモデルをデプロイする前に、ダイアログが**取得するすべてのリポジトリについてHuggingFaceアクセスを事前チェック**し、リポジトリごとに✓/✗と正確な次のステップを表示します — コールドスタートの数分後にライセンス同意の漏れに気づく、ということがなくなります。

> **GLBの表示について：** テクスチャはファイルをコンパクトに保つためWebP（`EXT_texture_webp`）としてエンコードされています — アプリ内ビューア、Blender 4.x、three.js、最新のUnity/Unrealインポーターでは完璧にレンダリングされます。macOSのプレビュー/QuickLookはglTF内のWebPに対応しておらず、モデルが黒く表示されます。アプリ内ビューアまたは最新のglTFツールをご利用ください。

| メトリック | 値 |
|--------|-------|
| メッシュ品質 | 最大約100万フェイス、完全な頂点法線 |
| テクスチャ解像度 | 4096² PBRアトラス（ベースカラー＋メタリック・ラフネス＋アルファ） |
| ライセンス | デフォルトで商用利用安全（TRELLIS.2 MIT＋BiRefNet MIT）。非商用バックエンドは完全な開示付きで提供 |
| サポートするアセットタイプ | Game Asset、Character |

### 📝 1.9.1 エンジン対応エクスポート（GLB · FBX · USD）

生成したすべての3Dモデルは、Asset Viewerの3Dタブから直接、**ゲームエンジン向けに準備した状態で**エクスポートできます：

- **ターゲットエンジン** — Generic（glTF、Y-up）、Unreal Engine（Z-up）、Unity、Godot、Maya、3ds Maxから選択します。FBXおよびUSDエクスポートは、そのエンジンに合った正しいアップ軸・前方軸で向きが調整されるため、モデルは正しい姿勢でインポートされます — 手動での回転修正は不要です。
- **オプションの下準備、選ぶのはあなた**（それぞれ独立したドロップダウン — 強制されるものは何もありません）：
  - **テクスチャパッキング** — エンジンごとのテクスチャセット：Unreal **ORM**（AO/Roughness/Metallic）、Unity **Metallic＋アルファ内Smoothness**、Unity **HDRP Mask Map**。選択すると、エクスポートはモデル＋`textures/`フォルダを含むZIPになります。
  - **LOD** — デシメーションによる**LOD0〜LOD3チェーン**（100/50/20/5%）。Unrealが自動インポートする本物のFBX LODグループ付きで、`_LOD0…_LOD3`という命名はそのままUnityの規約としても機能します。
  - **コリジョン** — 凸包または**CoACD凸分解**を、エンジンごとの命名規約に沿って生成します（Unrealの自動インポート用に`UCX_*`、Godot用に`-convcolonly`サフィックス）。
  - **ライトマップUV2** — ベイクドライティング用に、スマート投影された第2のUVチャンネルを追加します。
- **2ステップのフロー** — まだ存在しない組み合わせに対しては、ボタンが**Generate FBX/USD/GLB**と表示されます。クリックするとサーバー側で変換が実行されます（ステータス行が進行状況を知らせます — 大きなモデルでは1〜2分かかることがあります）。ビルドが完了すると、ボタンは✓付きの**Download**に切り替わり、即座にダウンロードできます。個別の組み合わせはすべてキャッシュされ — 再生成されることは決してありません。
- **ダウンロード可能チップ** — 3Dタブには、現在のバージョンで生成済みのすべての組み合わせが一覧表示され、ワンクリックでどれでも再ダウンロードできます。
- **オリジナルのGLBは不可侵** — 「Download GLB (original)」は常に、生成パイプラインの出力そのまま、バイト単位で同一の未加工ファイルを返します。加工済みエクスポート（LOD/コリジョンを焼き込んだ加工済みGLBを含む）は、その横に別名のファイルとして並びます。
- **セットアップ不要** — 変換はマネージドなヘッドレスBlenderを通じてサーバー側で実行されます：既存のインストールがあればそれを再利用し、なければ初回使用時にポータブル版が自動的にダウンロードされます（バージョンと更新はModel Settings → Maintenanceタブを参照）。エンドユーザーが何かをインストールする必要はありません。

### 📝 1.9.2 AI生成3Dに期待できること — 率直なガイド

Image-to-3Dはまだ若い技術です。今日の最高水準のモデル（ArtSmokerが動かしているものを含む）が本当に提供できるもの — そしてできないもの — を知っておく価値があります。出力は**スキャンオブジェクト風の高密度メッシュ**です：最大約100万の非構造化トライアングルに、PBRテクスチャがベイクされています。近くで見ると特有のごつごつした表面の質感に気づくでしょうし、細い形状（髪の毛、ストラップ、布のフリンジ）はAIジオメトリが最も苦手とする部分です。**きれいなクアッドトポロジーも、アニメーションに適したエッジループも、リグもありません** — これは業界全体における現時点の技術水準であって、特定のツールに固有の制限ではありません。

**これらのアセットが輝く場面 — そしてアーティストの手が必要な場面：**

| ユースケース | そのまま使える？ |
|----------|---------------|
| プロップ、環境の小物、セットドレッシング | ✅ はい — そのまま使えます |
| 背景/中距離のキャラクター、群衆 | ✅ はい — 距離を置けば表面のノイズは消えます。LODチェーンを活用してください |
| プロトタイピング、ブロックアウト、プレビズ、ピッチデモ | ✅ はい — 間違いなく最も強力なユースケースです |
| モバイル/スタイライズドゲーム | ✅ 多くの場合 — デシメーション済みLODが役立ちます |
| ヒーローキャラクター、クローズアップ、アニメーションするキャラクター | ⚠️ 出発点として — アーティストによるリトポロジー、クリーンアップ、リギングを見込んでください |

ArtSmokerが生のメッシュに上乗せする価値は、すべてが**エンジン向けに正しくパッケージングされて**届くことです — ターゲットごとの正しいアップ軸、LODチェーン、コリジョンプロキシ、エンジン固有のテクスチャパッキング — 残る作業はクリエイティブなものだけで、配管仕事ではありません。

**エクスポートをBlender（や他のDCCツール）で検査する場合、奇妙に見えるものが2つあります — どちらも正常です：**

- **LOD付きで生成した場合？** ファイルにはモデルの**4つの重なったコピー**（LOD0〜3）が含まれています。まとめて表示するとちらつき（Zファイティング）が発生してノイジーに見えます — OutlinerでLOD1〜3を非表示にし、LOD0だけで品質を判断してください。ゲームエンジンは常に1つのLODだけを表示するため、エンジン内でこの現象が起きることはありません。
- **コリジョン付きで生成した場合？** 白いブロック状の`UCX_*`メッシュのシェルが**モデルを包み込んで**います — これは物理プロキシであって、あなたのアセットではありません。それらのオブジェクトを非表示にすれば、中のテクスチャ付きモデルが見えます。エンジンはこれらを不可視のコリジョンとして自動的にインポートします。

<a id="-193-using-a-model-commercially--who-to-pay-and-how"></a>

### 📝 1.9.3 モデルの商用利用 — 誰に、どのように支払うか

あるモデルの出力が気に入って商用利用したくなったとき、その道筋はモデルの**作成者がどのように収益化しているか**で決まります。ArtSmokerはデプロイ時にすべてのモデルのライセンスを表示します — 本節はその「次に何をすればいい？」に答えるガイドです。*（2026年8月時点でベンダーサイトとHuggingFaceのライセンスファイルに照らして検証済み — ライセンスは頻繁に変わるため、必ずベンダーの最新の条件を確認してください。あくまで参考情報です — [免責事項](#disclaimer)を参照してください。）*

出会うことになる4つのパターン：

1. **すでにあなたのもの（Apache-2.0 / MIT）** — 商用利用は無料で含まれています。購入すべきライセンス製品は存在せず、作成者は代わりに自社ホスト型のAPIで収益化しています。あなたの義務はライセンス表記/帰属表示の遵守だけです。
2. **大きくなるまでは無料（コミュニティライセンス）** — **一定のしきい値（収益または月間アクティブユーザー数）を下回る限り**、商用利用が含まれています。それを超えると、ライセンス自体がベンダーへのエンタープライズグラントの申請を指示します — ストアでの購入ではなく、営業との商談です。
3. **ライセンスを購入し、ウェイトはそのまま** — HuggingFaceのウェイトは非商用ですが、作成者が別途**セルフホスト商用ライセンス**を販売しています。それを取得すれば、*すでにデプロイ済みのまったく同じウェイト*が商用利用で合法になります — ArtSmoker側で技術的に変わるものは何もありません。
4. **ゲートそのものがペイウォール** — HuggingFaceリポジトリ自体がゲート付きで、ベンダーとの商用契約によってあなたのHFアカウントのアクセスが解放されます。ArtSmokerのHuggingFaceトークン＋ゲート付きリポジトリ事前チェックのフローは、そのまま機能します。

| 作成者 / モデル | パターン | 商用セルフホストのための次のステップ |
|---|---|---|
| **Alibaba** — Qwen-Image、Qwen-Image-Edit | 1 | 購入するものはありません（Apache-2.0）。ライセンス表記を保持してください。 |
| **Microsoft** — TRELLIS.2 · **VAST** — TripoSG | 1 | 購入するものはありません（MIT）。注意：上流の依存関係（例：Meta DINOv3）には独自のゲートや条件があります。 |
| **Black Forest Labs** — FLUX.2 [klein] 4B | 1 | 購入するものはありません — Apache-2.0で、商用利用は無料です。 |
| **Stability AI** — SD 3.5（セルフホスト） | 2 | **年間総収益100万ドル未満**なら商用利用込みで無料（HFゲートの承諾が*そのまま*ライセンスになります）。超えるとライセンスは**自動的に終了**します — stability.ai/enterprise でEnterpriseライセンスを申請してください。**「Powered by Stability AI」の帰属表示はすべてのティアで必須です。** |
| **Tencent** — HunyuanImage 3.0 / Hunyuan3D | 2 | しきい値未満なら商用利用込みで無料 — **モデルごとに異なる点に注意**：HunyuanImage 3.0 = 1億MAU、**Hunyuan3D-2.1 = わずか100万MAU**（超えたら hunyuan3d@tencent.com にメール）。規模にかかわらず、**EU・英国・韓国ではグラントが一切ありません**。 |
| **Black Forest Labs** — FLUX.1/.2 [dev]、Kontext | 3 | **FLUX Commercial Weights License**を購入します（dashboard.bfl.ai/licensing でセルフサービス。ティアは画像生成量に上限のあるサブスクリプションです）。同じHFウェイトをそのまま使い続けられます。義務に注意：使用量レポート、出力フィルタリング、**モデルをAPIとして公開・再販することの禁止**。新しいモデルバージョンはEnterprise以外では自動的にはカバー**されません**。 |
| **Bria** — FIBO、RMBG-2.0 | 4 | HFゲートは即座に**非商用**アクセスを付与しますが、商用セルフホストには**Briaとの有償契約**が必要です（各モデルカード / bria.ai からリンクされた購入フォーム）。無料で商用利用できるしきい値は存在しません。承認されれば、これまでどおりArtSmokerからデプロイできます。 |

**ArtSmokerとの関係**：ライセンスの調達によって技術的に変わることは、ほぼありません。パターン1〜3では、デプロイするウェイトは取得の前後でまったく同じです — 変わるのはあなたが保持する契約です（ライセンスの記録を保管してください。ArtSmokerのデプロイダイアログが記録するのは*ウェイト*ライセンスへの承諾であり、商用グラントはベンダーとあなたを直接拘束します）。パターン4では、ベンダーがあなたのHuggingFaceアカウントを承認すると、ArtSmokerの既存のゲート付きリポジトリアクセスチェックが緑になり、デプロイは通常どおり進みます。ベンダーが新しいモデルバージョンをリリースしたら、あなたのグラントがそれをカバーしているか再確認してください（Stabilityは自動的にカバーし、BFLはEnterprise以外では通常カバーせず、Tencentはバージョンごとに新しいライセンステキストを発行します）。

<a id="get-started"></a>

## 📌 2. 前提条件

- **Python 3.11+**（3.12、3.13、3.14はすべて動作）
- 有効な認証情報で設定済みの**AWS CLI**
- Bedrockアクセス用の**IAMパーミッション**（以下を参照）

### 📝 2.1 AWS認証情報

ArtSmokerは[boto3の標準認証情報解決](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials)を使用するため、以下のいずれの方法も機能します：

| 方法 | 最適な用途 | 設定方法 |
|--------|----------|-----|
| **環境変数** | CI/CD、コンテナ | `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` |
| **共有認証情報ファイル** | ローカル開発 | `aws configure`経由の`~/.aws/credentials` |
| **名前付きプロファイル** | 複数アカウント | `ARTSMOKER_AWS_PROFILE=myprofile`または`AWS_PROFILE`を設定 |
| **AWS SSO** | エンタープライズSSO | `aws configure sso` |
| **IAMインスタンスプロファイル** | EC2、ECS、App Runner | インスタンスにIAMロールをアタッチ — マシン上に認証情報は不要 |
| **ECSタスクロール** | ECS/Fargateコンテナ | 必要なパーミッションを持つタスク実行ロールを割り当て |

認証情報が機能しているかのクイックチェック：

```bash
aws sts get-caller-identity
```

> [!NOTE]
> EC2やその他のAWSコンピューティングサービスでは、明示的な認証情報を設定する必要はありません。必要なパーミッションを持つ[IAMインスタンスプロファイル](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2_instance-profiles.html)をアタッチすれば、boto3がインスタンスメタデータサービス経由で自動的に取得します。

### 📝 2.1.1 Bedrockアクセスの確認

認証情報が機能すること（`sts:GetCallerIdentity`）を確認しても、それはアイデンティティを検証するだけで、Bedrockのパーミッションがあることは確認できません。ArtSmokerは複数のBedrock APIを使用するため、単純なリスト取得テストだけでは不十分です。最も信頼できるチェックは次のとおりです：

```bash
# Test 1: Can you list models? (requires bedrock:ListFoundationModels)
aws bedrock list-foundation-models --region us-east-1 --query "modelSummaries[0].modelId" --output text

# Test 2: Can you invoke an image model? (requires bedrock:InvokeModel)
aws bedrock-runtime invoke-model --region us-west-2 \
  --model-id stability.sd3-5-large-v1:0 \
  --content-type application/json --accept application/json \
  --body '{"prompt":"test","aspect_ratio":"1:1"}' \
  /dev/null 2>&1 && echo "InvokeModel: OK" || echo "InvokeModel: FAILED"

# Test 3: Can you use the Converse API? (requires bedrock:Converse)
# (Substitute any Claude model ID you have access to — e.g. the current Sonnet
#  inference profile from Test 1's list; the exact version rolls over time.)
aws bedrock-runtime converse --region us-west-2 \
  --model-id us.anthropic.claude-sonnet-4-6 \
  --messages '[{"role":"user","content":[{"text":"hi"}]}]' \
  --inference-config '{"maxTokens":1}' \
  --query "output.message.content[0].text" --output text 2>&1 && echo "Converse: OK" || echo "Converse: FAILED"

# Test 4: Can you list custom models? (requires bedrock:ListCustomModels)
aws bedrock list-custom-models --region us-east-1 \
  --query "modelSummaries[0].modelName" --output text 2>&1 && echo "ListCustomModels: OK" || echo "ListCustomModels: no custom models (or permission denied)"
```

Test 1〜3が通れば、コアのパーミッションは設定されています。Test 4はカスタムモデル検出にのみ必要です。Test 1が通ってもTest 2〜3が失敗する場合、IAMポリシーはリスト取得を許可しているが呼び出しは許可していない状態です — 下記のパーミッション表を使って更新してください。

### 📝 2.2 IAMパーミッション

あなたのIAMユーザー、ロール、またはインスタンスプロファイルには、次のパーミッションが必要です：

| パーミッション | 用途 |
|------------|----------|
| `bedrock:InvokeModel` | 画像生成、画像編集、後処理（すべての画像モデル） |
| `bedrock:Converse` | LLM呼び出し — プロンプト精緻化、スタイル分析、コンセプト生成 |
| `bedrock:InvokeModelWithBidirectionalStream` | 音声文字起こし（オプション — なくてもアプリは動作） |
| `bedrock:StartAsyncInvoke` | 動画生成（非同期呼び出し） |
| `bedrock:GetAsyncInvoke` | 動画生成ジョブのステータスをポーリング |
| `bedrock:ListAsyncInvokes` | 動画生成ジョブを一覧表示 |
| `bedrock:ListFoundationModels` | 基盤モデルの検出（Sync from AWS） |
| `bedrock:ListCustomModels` | アカウント内のファインチューニング済みカスタムモデルを検出 |
| `bedrock:ListImportedModels` | アカウント内のインポート済みモデルを検出 |
| `bedrock:GetCustomModel` | カスタムモデルの詳細（ベースモデル、ステータス）を読み取り |
| `bedrock:GetImportedModel` | インポート済みモデルの詳細（アーキテクチャ、ステータス）を読み取り |
| `bedrock:ListProvisionedModelThroughputs` | プロビジョンドスループットで呼び出し可能なカスタムモデルを検索 |
| `bedrock:ListCustomModelDeployments` | オンデマンドデプロイメントを持つカスタムモデルを検索 |
| `bedrock:CreateInference` *(またはポリシー`AmazonBedrockMantleInferenceAccess`)* | **Amazon Bedrock Mantle** — Mantleエンドポイント経由でのみ到達可能なフロンティアモデル（OpenAI GPT‑5.x、Claude Mythos、GLM、Grok、Qwen、Gemmaなど）。これがないとそれらのモデルにのみ影響します。Converse経由のClaudeは引き続き動作します。 |
| `account:ListRegions` | Sync時にアカウントの**有効化された**リージョンのみをスキャン（高速、オプトインリージョンでもエラーなし）。オプション — なければ全リージョンのスキャンにフォールバック。 |
| `account:GetRegionOptStatus` | リージョンごとのオプトインステータスを読み取り（`account:ListRegions`の相棒）。オプション。 |
| `s3:CreateBucket` | 動画ストレージ用のS3バケットを作成（オプション、UI経由） |
| `s3:PutObject` / `s3:GetObject` / `s3:DeleteObject` / `s3:ListBucket` | 動画出力の保存と取得 |
| `aws-marketplace:Subscribe` | サードパーティモデル（サードパーティのMantleモデルを含む）の初回使用時の自動サブスクリプション |
| `aws-marketplace:ViewSubscriptions` | 既存のモデルサブスクリプションを確認 |
| `sts:GetCallerIdentity` | 起動時の認証情報検証。ローカル署名されるMantleベアラートークンの基盤にもなる |
| `pricing:GetProducts` | Sync from AWS時にモデル料金を取得（オプション） |
| `sagemaker:*` | Amazon SageMaker上のセルフホスト型カスタムモデル（オプション — Custom Modelsを使う場合のみ） |
| `iam:PassRole` | Amazon SageMakerがあなたのロールを使えるようにする（オプション — Custom Modelsの場合のみ） |
| `iam:CreateRole` / `iam:AttachRolePolicy` | 初回デプロイ時にAmazon SageMaker実行ロールを自動作成（オプション — Custom Modelsの場合のみ） |
| `iam:GetRole` / `iam:UpdateAssumeRolePolicy` | Amazon SageMakerの信頼関係用に既存ロールを自動設定（オプション） |
| `secretsmanager:CreateSecret` / `secretsmanager:GetSecretValue` / `secretsmanager:DeleteSecret` | ゲート付きモデル用HuggingFaceトークンの暗号化ストレージ（オプション — teardown時に自動クリーンアップ） |

**最速のセットアップ**（マネージドポリシー — 最も広範なアクセス）：

```bash
# Option A: Attach managed policies to your IAM user (simplest for local development)
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

# Amazon Bedrock Mantle endpoint — needed for frontier models (OpenAI GPT-5.x,
# Claude Mythos, GLM, Grok, etc.). Skip only if you won't use Mantle-only models.
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockMantleInferenceAccess

# Add S3 access for video storage
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

**スコープを絞ったセットアップ**（より厳格なパーミッション — 本番環境に推奨）：

```bash
# Create a scoped IAM policy with only the permissions ArtSmoker needs
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

# Attach to your IAM user (replace YOUR_ACCOUNT_ID and YOUR_USERNAME)
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/ArtSmokerAccess
```

> [!TIP]
> **EC2/ECS/App Runnerの場合** — ユーザーにアタッチする代わりにIAMロールを作成してください。完全なロール作成コマンドについては[EC2デプロイメント](#43-ec2--cloud-deployment)セクションを参照してください。アクセスキーは不要です — boto3がインスタンスメタデータサービスからロールを自動検出します。

> [!NOTE]
> Bedrockモデルは、すべての商用AWSリージョンでデフォルトで利用可能です — 手動の有効化ステップは不要です。サードパーティモデル（Anthropic、Stability AI）の初回呼び出し時、AWSはバックグラウンドで自動的にマーケットプレイスサブスクリプションを開始します（上記の`aws-marketplace`パーミッションが必要）。Anthropicモデルは、一度だけ[First Time Useフォーム](https://console.aws.amazon.com/bedrock/home#/modelaccess)の記入が必要です。

### 📝 2.3 オプション：SVG変換ツール

SVG変換は外部CLIツール（Pythonパッケージではありません）を使用します。それらがない場合、SVG出力はPillowベースのラスター埋め込みSVGラッパーにフォールバックします — 機能はしますが、真のベクター出力ではありません。

| ツール | 目的 | macOS | Linux (Debian/Ubuntu) | Windows |
|------|---------|-------|-----------------------|---------|
| **vtracer** | 主要SVG（カラーベクタートレース） | `pip install vtracer`または`cargo install vtracer` | `pip install vtracer`または`cargo install vtracer` | `pip install vtracer`または`cargo install vtracer`または[pre-built binaries](https://github.com/visioncortex/vtracer/releases) |
| **potrace** | フォールバックSVG（モノクロトレース） | `brew install potrace` | `sudo apt install potrace` | [potrace.sourceforge.net](http://potrace.sourceforge.net/#downloading)からダウンロード |

インストールの確認：

```bash
# Check SVG conversion tools
which vtracer && echo "vtracer: OK" || echo "vtracer: not installed (optional)"
which potrace && echo "potrace: OK" || echo "potrace: not installed (optional)"
```

### 📝 2.4 オプション：動画サムネイル＆メタデータツール

Video StudioはAmazon Nova ReelとLuma AI Ray経由でMP4動画を生成します。サムネイル（最初のフレームをJPEGとして）と動画メタデータ（長さ、解像度、FPS）を抽出するには、ArtSmokerバックエンドを実行するマシンに**ffmpeg**と**ffprobe**がインストールされている必要があります。

ffmpegがない場合：
- 動画は引き続き正しく生成・再生されます（S3からストリーミング、またはMP4としてダウンロード）
- サムネイルは表示されません — ギャラリーとVideo Studioは、プレビュー画像の代わりに黒いプレースホルダーを表示します
- 動画メタデータ（長さ、解像度）は表示されません

| ツール | 目的 | macOS | Linux (Debian/Ubuntu) | Windows |
|------|---------|-------|-----------------------|---------|
| **ffmpeg** | サムネイル抽出＋動画メタデータ | `brew install ffmpeg` | `sudo apt install ffmpeg` | [ffmpeg.org/download](https://ffmpeg.org/download.html)からダウンロードまたは`winget install ffmpeg` |

> [!NOTE]
> `ffprobe`はffmpegに含まれています — 別途のインストールは不要です。ArtSmokerは実行時にffmpegをチェックし、見つからない場合はグレースフルにフォールバックします — 動画生成はどちらの場合も動作し、単にサムネイルが得られないだけです。

インストールの確認：

```bash
ffmpeg -version 2>&1 | head -1 && echo "ffmpeg: OK" || echo "ffmpeg: not installed (optional)"
ffprobe -version 2>&1 | head -1 && echo "ffprobe: OK" || echo "ffprobe: not installed (optional)"
```

## 📌 3. インストール

### 📝 3.1 macOS

```bash
git clone <repo-url> && cd ArtSmoker

# Option A: With virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Option B: Without virtual environment (system-wide install)
pip3 install -r backend/requirements.txt
```

> [!NOTE]
> macOSでは、`python3`と`pip3`はHomebrew（`brew install python`）またはXcodeコマンドラインツール経由で利用できます。「command not found」と表示される場合は、[python.org](https://www.python.org/downloads/)からPythonをインストールするか、`brew install python@3.12`でインストールしてください。

### 📝 3.2 Linux (Debian/Ubuntu)

```bash
# Install Python if needed
sudo apt update && sudo apt install python3 python3-pip python3-venv

git clone <repo-url> && cd ArtSmoker

# Option A: With virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Option B: Without virtual environment
pip3 install --user -r backend/requirements.txt
```

> [!NOTE]
> 一部のLinuxディストリビューションでは、venv外での`pip install`に`--user`フラグまたは`--break-system-packages`（PEP 668）が必要です。venvを使えばこれを完全に回避できます。

### 📝 3.3 Windows

```powershell
git clone <repo-url>
cd ArtSmoker

# Option A: With virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt

# Option B: Without virtual environment
pip install -r backend\requirements.txt
```

> [!NOTE]
> Windowsでは、`python3`ではなく`python`を使用してください。[python.org](https://www.python.org/downloads/)からPythonをインストールし、インストール時に「Add to PATH」をチェックしてください。Type Studioのフォントピッカーは`C:\Windows\Fonts`からフォントを検出します（システムフォント検出は現在macOS/Linuxのみ — Windowsユーザーはグローバルまたはスタイル固有のカスタムフォントを使用できます）。

## 📌 4. 実行

### 📝 4.1 ソロ開発（全プラットフォーム）

ファイル変更時に自動リロードするシングルプロセス — 1人の開発者がローカルで作業するのに最適：

```bash
# With venv (activate first)
source .venv/bin/activate          # macOS / Linux
.venv\Scripts\activate             # Windows

uvicorn backend.main:app --reload
```

```bash
# Without venv (if installed system-wide)
uvicorn backend.main:app --reload

# Or if uvicorn isn't on PATH
python3 -m uvicorn backend.main:app --reload     # macOS / Linux
python -m uvicorn backend.main:app --reload       # Windows
```

**http://localhost:8000** を開いてください — フロントエンドはFastAPIによって配信されるため、別のWebサーバーは不要です。

起動時、コンソールにAWS認証情報の検証結果が表示されます。何か問題があれば、明確なエラーボックスが表示されます。ステータスは`http://localhost:8000/api/health`でも確認できます。

**ログ。** ArtSmokerは、コンソールに加えて、**デフォルトで**`logs/artsmoker.log`に完全な**追記専用**ログを書き込むため、アプリを閉じた後でも過去のセッションを確認できます。各実行はセッションバナー（起動時刻、バージョン、pid、ホスト）で始まり、シャットダウンバナー（停止時刻、継続時間）で閉じられます。パスの変更やオフにするには：

```bash
ARTSMOKER_LOG_FILE=/var/log/artsmoker/app.log uvicorn backend.main:app   # custom path
ARTSMOKER_LOG_TO_FILE=false uvicorn backend.main:app                      # disable file logging
```

（またはローカルの`.env`で`log_to_file` / `log_file`を設定します。複数ワーカーの場合、各ワーカーが同じファイルに追記します。）

### 📝 4.2 マルチユーザー / 共有テストボックス / 本番環境（macOS / Linux）

同時ユーザーが2人以上の環境 — 共有の開発/テストボックス、ステージング、本番のいずれであっても — では、複数ワーカーの**gunicorn**を使用してください：

```bash
# Install gunicorn (one-time, in addition to requirements.txt)
pip install gunicorn

# Run with gunicorn (multi-worker, handles concurrent users)
gunicorn backend.main:app \
  -w 2 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 300
```

| フラグ | 目的 |
|------|---------|
| `-w 2` | 2つのワーカープロセス（負荷が高い場合は増やす） |
| `-k uvicorn.workers.UvicornWorker` | uvicornの非同期ワーカークラスを使用 |
| `--bind 0.0.0.0:8000` | すべてのインターフェースでリッスン（localhostだけでなく） |
| `--timeout 300` | リトライを伴う大規模バッチ生成のための5分タイムアウト |

> [!TIP]
> **gunicorn**はLinux/macOSのみです。Windowsでは、マルチワーカー配信に`uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2`を使用してください。

> [!NOTE]
> **同時ユーザーに対して安全。** すべてのサーバー書き込み — 画像/バージョンメタデータおよびモデル＆プロンプトレジストリ — はアトミックに書き込まれ、**ワーカープロセスをまたいで**シリアライズされます（POSIXファイルロック）。そのため、共有ボックス上の複数のコラボレーターによる同時編集が、ファイルを破損したり更新を失ったりすることは決してありません。ファイルロギングもワーカーをまたいで同じように機能します — 各ワーカーが1つの`logs/artsmoker.log`に追記します。

<a id="43-ec2--cloud-deployment"></a>

### 📝 4.3 EC2 / クラウドデプロイメント

推奨：1〜2人の同時ユーザーには**t3.small**（～$15/月）。

**ステップ1：EC2インスタンス用のIAMロールを作成**（ローカルマシンから実行）：

```bash
# Create the IAM role with EC2 trust policy
aws iam create-role --role-name ArtSmokerEC2Role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach the ArtSmoker policy (use the scoped policy from section 2.2, or the managed policy)
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# Create an instance profile and attach the role
aws iam create-instance-profile --instance-profile-name ArtSmokerEC2Profile
aws iam add-role-to-instance-profile \
  --instance-profile-name ArtSmokerEC2Profile \
  --role-name ArtSmokerEC2Role
```

**ステップ2：EC2インスタンスを起動**（または既存のインスタンスにプロファイルをアタッチ）：

```bash
# Attach to an existing running instance
aws ec2 associate-iam-instance-profile \
  --instance-id i-YOUR_INSTANCE_ID \
  --iam-instance-profile Name=ArtSmokerEC2Profile
```

**ステップ3：インスタンス上でインストールして実行**（インスタンスにSSH接続）：

```bash
# Install (one-time)
sudo yum install -y python3 python3-pip git   # Amazon Linux
# sudo apt install -y python3 python3-pip python3-venv git   # Ubuntu

git clone <repo-url> && cd ArtSmoker
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install gunicorn

# Optional: install ffmpeg for video thumbnails
sudo yum install -y ffmpeg   # Amazon Linux
# sudo apt install -y ffmpeg   # Ubuntu
```

**ステップ4：systemdサービスとして実行**（永続的、自動再起動）：

```bash
# Create the service file
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

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable artsmoker
sudo systemctl start artsmoker

# Verify it's running
sudo systemctl status artsmoker

# View logs
sudo journalctl -u artsmoker -f
```

**http://YOUR_INSTANCE_IP:8000** を開いてください — EC2セキュリティグループがインバウンドTCP 8000を許可していることを確認してください。

### 📝 4.4 セットアップ後の最初のステップ

ArtSmokerが起動したら、最良の結果を得るために次のステップを完了してください：

**1. AWSからモデルを同期** — **Model Settings**（任意のスタジオの歯車アイコン）を開く → **Sync from AWS**をクリック。これにより、すべてのBedrockリージョンにわたって利用可能なすべての画像、動画、チャットモデルが検出されます。30〜60秒かかります。一度だけ、またはAWSが新しいモデルを追加したときに必要です。

**2. プロンプトテンプレートの確認とカスタマイズ** — これは、実行できる最もインパクトの大きい設定です。**Model Settings → Prompt Templates**タブを開きます。ArtSmokerは、AIの振る舞いを制御する28の編集可能な指示プロンプトを使用します：

| テンプレート | 制御する内容 |
|----------|-----------------|
| Image Prompt Refinement | テキスト記述がどのように詳細な画像生成プロンプトに変換されるか |
| Multi-Concept Generation | 1つのアイデアから複数のクリエイティブオプションがどのように生成されるか |
| Style Analysis | リファレンス画像がどのように分析され、アートスタイルを学習するか |
| Content Moderation | 事前チェックとリライトシステムの厳格さ |
| Video Enhancement | 動画プロンプトがカメラワークと照明でどのように豊かにされるか |
| Text Layout | Type Studioが画像上のテキスト配置をどのようにデザインするか |

各テンプレートは次のことができます：
- **直接編集** — チームのニーズに合わせて指示を修正
- **AIで強化** — 任意のLLMモデルを選択し、オプションで指示を追加（例：「ピクセルアート向けに最適化」）し、「Enhance with AI」をクリック。提案を確認して、AcceptまたはDismiss
- **デフォルトにリセット** — いつでもオリジナルを復元

テンプレートはスタジオ別（Image Studio、Style Library、Content Safety、Video Studio、Type Studio、Chat Studio、Translation）に整理され、各テンプレートが制御する内容の分かりやすい説明が付いています。

**変数の安全性：** テンプレートは、実行時に置換される`{curly_brace}`変数（例：`{user_prompt}`、`{model_name}`）を使用します。誤って必須変数を削除した場合、ArtSmokerは次のことを行います：
1. 保存をブロックし、どの変数が欠落しているかを表示
2. **「Fix & Save」**を提供 — LLMが、編集したテキストの正しい位置に欠落した変数を自動的に挿入
3. 保存前に修正を検証

テンプレートは`backend/prompt_templates.json`からロードされます — ランタイムの信頼できる唯一の情報源です。編集内容は`backend/prompt_templates.user.json`（gitignore済み）に保存されて上に重ねられるため、更新や`git pull`があってもカスタマイズが上書きされることはありません。JSONが欠落・破損している場合、またはコードに新しいテンプレートが同梱された場合、自己修復します：組み込みのコードシードが、欠落したエントリのみを再生成/補填し、既存のものを上書きすることは決してありません。

> [!TIP]
> まず**Image Prompt Refinement**と**Creative Options**テンプレートを確認することから始めてください。これらが出力品質に最も大きな影響を与えます。チームが特定のアートスタイル（例：ピクセルアート、水彩、アイソメトリック）に特化している場合、それらの好みをテンプレートに直接追加すれば、すべての生成がその恩恵を受けます。

**3. スタイルプロファイルをセットアップ**（オプション） — **Style Library**に移動し、新しいスタイルを作成し、リファレンス画像をアップロードして、**Analyze**をクリックします。これにより、ArtSmokerにあなたのビジュアルアイデンティティを教えます。

**4. 言語を選択** — 英語以外のインターフェースを好む場合は、ナビバーの言語ボタン（EN | JA | ZH | KO | FR | ES）をクリックしてください。

## 📌 5. アーキテクチャ

```
┌─────────────────────────────────────────────┐
│  Browser (SPA)                              │
│  Vanilla JS + Tailwind CSS                  │
└──────────────────────┬──────────────────────┘
                       │ HTTP / SSE
                       ▼
┌─────────────────────────────────────────────┐
│  FastAPI Backend (Python)                   │
│                                             │
│  /api/styles      Style CRUD + import       │
│  /api/generate    Two-level generation      │
│  /api/type-studio Text overlay + fonts      │
│  /api/video       Video generation + jobs   │
│  /api/chat        LLM chat + sessions       │
│  /api/gallery     Asset browsing + export   │
│  /api/browse      File/S3 browser           │
│  /api/admin       Model registry + templates│
│  /api/refine-prompt  Prompt + translate      │
│  /api/transcribe  Voice-to-text             │
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
└──────────────────────┘  └──────────────────────────┘ ... (other regions)
             │
             ▼
┌──────────────────────┐
│  Local Storage        │
│  data/styles/         │
│  data/generated/      │
│  data/video/          │
│  data/chat/           │
└──────────────────────┘
```

## 📌 6. 使い方

### 📝 6.1 ワークフロー概要

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
  │ Upload   │ │Generate│ │Generate│ │ Add text │ │ Multi- │
  │ Analyze  │ │ images │ │ videos │ │ to imgs  │ │ model  │
  │ Set fonts│ │        │ │        │ │          │ │ LLM    │
  │          │ │        │ │        │ │          │ │ chat   │
  └────┬─────┘ └───┬────┘ └───┬────┘ └────┬─────┘ └────────┘
             │              │            │               │
             │    ┌─────────┴────────────┴─────────┐     │
             │    │  Style selected? (optional)    │     │
             └───►│  Enhances output               │◄────┘
                  └─────────┬──────────────────────┘
                                    │
                                    ▼
                          ┌─────────────────┐
                          │    Gallery      │
                          │                 │
                          │ Browse all      │
                          │ Search/filter   │
                          │ Select & delete │
                          └────────┬────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
            ┌──────────────┐ ┌──────────┐ ┌──────────────┐
            │ Download     │ │ Reload   │ │ Add Text     │
            │ PNG / SVG    │ │ in 2D    │ │ in Type      │
            │              │ │ Image    │ │ Studio       │
            │              │ │ Studio   │ │              │
            │              │ │ (refine &│ │ (overlay     │
            │              │ │  regen)  │ │  text)       │
            └──────────────┘ └──────────┘ └──────────────┘
```

**3つのエントリーポイント、1つの統合ギャラリー：**

- **スタイルから始める** — Style Libraryにリファレンスアートをアップロードし、AIに分析させ、任意のスタジオで生成します。スタイルがすべての出力をガイドします。
- **スタイルなしで始める** — 2D Image Studio、Video Studio、Type Studioに直接飛び込みます。AIが最善の判断を下します。
- **ギャラリーから始める** — 以前生成したアセットを選び、改良のために適切なスタジオで再読み込みしたり、テキストを追加したり、動画を再生したり、PNG/SVG/MP4としてダウンロードしたりします。

生成されたすべてのアセット（画像、動画、テキストオーバーレイ、スタンドアロンテキスト）は、統合ギャラリーに集約されます。何も上書きされません — 各生成が新しいアセットを作成します。

### 📝 6.2 生成パイプライン

```
User prompt: "hospital building"
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 1. Prompt Composition            Claude Sonnet (1 opt) │
│    (optional "Compose" button)   or Opus (2-5 options) │
│    + style + asset type                                │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 2. Canary Test                                         │
│    Single image tests moderation                       │
│    Pass? ──► Full batch    Fail? ──► Model switch      │
│                                  or rewrite suggestion │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 3. Parallel Image Generation                           │
│    Up to 5 options × 5 variations = 25 images          │
│    ThreadPool (3-5 workers)                            │
│    Retry with exponential backoff (3 attempts)         │
│    SSE progress streaming to browser                   │
│    Cooperative cancellation on moderation block        │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 4. Post-Processing (per image, optional)               │
│    Remove Background ──► Stability AI ($0.07/img)      │
│    Upscale ──► Stability AI Creative Upscale ($0.60)   │
│    SVG ──► vtracer / potrace / Pillow (free, local)    │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 5. Storage                                             │
│    data/generated/{asset_id}/                          │
│    ├── asset.png (transparent background)              │
│    ├── asset.svg (optional)                            │
│    └── metadata.json (full prompt lineage)             │
│    Smart filenames: prompt-slug_opt1_var2.png          │
└────────────────────────────────────────────────────────┘
```

### 📝 6.3 コンテンツモデレーションフロー

```
User clicks Generate
         │
         ▼
┌──────────────────────┐
│ Pre-Check enabled?   │
│ (Prompt Pre-Check    │
│  toggle, on by       │
│  default)            │
└───┬────────────┬─────┘
  Yes            No
    │            │
    ▼            │
┌──────────┐     │
│ Claude   │     │
│ Sonnet   │     │
│ screens  │     │
│ prompt   │     │
└───┬────┬─┘     │
 Issues? No      │
    │    └──────►│
    ▼            │
┌──────────────┐  │
│ Indigo       │  │
│ dialog:      │  │
│ • Switch     │  │
│ • Rewrite    │  │
│ • Proceed    │  │
│ • Cancel     │  │
└──┬───────────┘  │
   │◄────────────┘
   ▼
┌──────────────────────┐
│ Canary test          │
│ (1 image to model)   │
└───┬────────────┬─────┘
 Blocked        Pass
    │            │
    ▼            ▼
┌──────────┐  ┌──────────┐
│ Try alt  │  │ Full     │
│ models   │  │ batch    │
└───┬────┬─┘  │ runs     │
 Works?  No   └──────────┘
    │    │
    ▼    ▼
Emerald    Amber
dialog     dialog
(switch    (rewrite →
 or         enhanced
 rewrite)   prompt area)
```

### 📝 6.4 2D Image Studio（アセットを生成）

2D Image Studioは、ガイド付きの3ステップワークフローを使用します：

**ステップ1 — アイデアを説明**：テキストエリアにプロンプトを入力します。プレースホルダーは、選択したアセットタイプに応じて変わる現実的な例を表示します（例：Characterには「A young female warrior in ornate silver armor...」、Environmentには「A misty Japanese garden at dawn...」）。入力の代わりに、音声入力（マイクボタン）で口述もできます。

**ステップ2 — Prompt Designer** *(オプション)*：**🎨 Prompt Designer**をクリックして、プロンプトを構造化されたビジュアルコンポーネントに分解します。AIがプロンプトを分析し、編集可能なセクションに分割します：

- **Subject** — キャラクターの説明、服装、アクセサリー、ポーズ、表情
- **Scene** — 設定、背景、小道具、時間帯
- **Composition** — カメラアングル、フレーミング、被写界深度
- **Lighting** — キーライト、フィル/リムライト、ムード
- **Style & Colors** — アートスタイル、品質レベル、16進スウォッチ付きの名前付きカラーパレット

各フィールドは個別に編集できます。**Generate Enhanced Prompt**は、編集内容をフラットな再構成プロンプト（ステップ2に読み取り専用で表示）に再構成し、その後、ステップ3のEnhanced AI Promptを自動的に生成します。

Prompt Designerが開く前に、**AIアセットタイプ分類**が実行されます — プロンプトがシーンを記述しているのに「Game Asset」を選択している場合、「Environment」または「Character」への切り替えを提案するダイアログが表示されます。これにより、Prompt Designerが正しいコンテキストで分解できるようになります。

**ステップ3 — エンハンスドプロンプトプレビュー** *(オプション)*：**Generate Enhanced Prompt**をクリックして、生成前にモデル最適化されたプロンプトを確認します。AIは、ステップ2の再構成プロンプトを取り込み、モデル固有のガイダンス（解剖学、マテリアル、照明、プロンプト構造）で強化します。生成前にエンハンスドプロンプトを編集できます。ステップ2でPrompt Designerを使用した場合、これは自動的に入力されます。

**プロンプトパイプライン**：ユーザープロンプト → 分解 → 再構成（`recomposed_prompt`）→ モデルガイダンスで強化（`enhanced_prompt`）→ 画像モデル。複数オプションの場合、強化ステップは同じ再構成ベースからN個の異なる解釈を生成します。3つのレベルすべてがメタデータに保存されます。

**生成**：いつでもGenerateをクリックできます — ステップ2と3はオプションです。スキップした場合、Generateは処理を進める前にプロンプトを自動的に分解、再構成、強化します。**Prompt Pre-Check**（デフォルトでオン）は、生成前にプロンプトのモデレーション問題をスクリーニングします。

**追加コントロール：**
- **Asset Type** — サイドバーで選択。プロンプトのプレースホルダーを変え、AIがプロンプトをどう解釈するかに影響します。不一致を検出すると、システムが切り替えを提案します。
- **Art Style** — スタイルプロファイルを選択して、あなたのビジュアルアイデンティティで生成をガイドします。
- **Dimensions、Options、Variations** — 出力サイズと、生成するクリエイティブコンセプトの数を設定します。
- **Post-Processing** — 背景削除、アップスケール、SVG変換（生成後に適用）。
- **IP Declaration** — 厳格なモデルの互換性のために、所有権またはライセンスを表明します。
- **Model Settings** — モデル設定の表示/編集、利用可能なAmazon Bedrockモデルの検出。

生成の進捗はSSEを通じてリアルタイムでストリーミングされます — UIは、どの画像が生成されているか（例：「Generating images... 12/25」）、経過時間、現在のパイプラインステージを表示します。APIがスロットルされている場合、「API throttled — waiting to retry...」と遅延が表示され、その後「Retrying... (attempt 2/3)」と表示されます — 各画像は指数バックオフで最大3回リトライするため、大規模バッチが一時的なスロットリングでバリアントを失うことはありません。

生成された結果はナビゲーションを越えて残ります — タブを切り替えて戻っても、2D Image StudioのDOM状態が保持されます。リセットボタンのみがそれをクリアします。

**スマートコンテンツモデレーション**：プロンプトがモデルのコンテンツモデレーションフィルターによってブロックされると、ArtSmokerは3つの色分けされたダイアログを通じて段階的に対処します：

- **Indigo（事前チェック）** — 生成前に、AIが選択したモデルの既知の感度に対してプロンプトを事前スクリーニングします。問題が検出されると、具体的な懸念が表示され、次のことができます：推奨モデルに切り替える、現在のモデル向けに**プロンプトをリライトする**、そのまま進める、キャンセルする。
- **Emerald（モデル切り替え）** — 生成ブロック後、代替モデルがプロンプトをそのまま受け入れる場合、ArtSmokerはどのモデルが機能するか、なぜかを表示します。ワンクリックで切り替え。完全な試行ログを利用可能（「View N model tests」）。
- **Amber（リライト）** — すべてのモデルが拒否した場合、AI生成のリライトが、具体的な問題のリストとともに編集可能なテキストエリアで提供されます。検証済み/未検証バッジは、リライトがカナリアテストを通過したかどうかを示します。

**プロンプトリライトの挙動**：3つのダイアログすべてで、「Rewrite」を選んでも元のプロンプトが上書きされることは決してありません。リライトされたバージョンは、元のテキストの下の**エンハンスドプロンプトエリア**に表示され、永続的なアンバーの免責事項が付きます：*「このリライトはプロンプトを互換性のあるものにする試みです — それでもモデル自身のモデレーション評価の対象であり、拒否される可能性があります。」* エンハンスドプロンプトを確認・編集し、満足したらGenerateをクリックします。元のプロンプトは常に履歴とメタデータに保持されます。

一般的なトリガーには、著作権のあるIP名やキャラクター参照、暴力/武器の表現、成人向けコンテンツの参照が含まれます。ヒント：**「Preview Enhanced Prompt」**ボタンは、AIが説明的な表現に言い換えるため、モデレーションを自然に通過するプロンプトを生成することがよくあります。

**スマートカナリアテスト**：完全なバッチを生成する前に、ArtSmokerは単一の「カナリア」画像リクエストを送信して、モデルのモデレーションフィルターに対してプロンプトをテストします。カナリアがブロックされると、バッチは即座に停止します（N×M×3回ではなく、1回の無駄なAPIコール）。カナリアが通過すると、残りのタスクは協調的キャンセルとともに並列実行されます — いずれかのタスクがモデレーションブロックに達すると、残りは自動的にAPIコールをスキップします。

### 📝 6.5 スタイルプロファイルを使う

1. **Style Library**タブに移動します。
2. **Create New Style**をクリック — 名前を入力し、オプションで生成ヒントを追加します。作成モーダルで、**Local**と**S3**の参照ボタンを備えた**「Import References From」**セクションを使って、ソースディレクトリまたはバケットパスを選択します。参照すると、サーバーサイドのファイル/ディレクトリブラウザモーダルが開きます（シングルクリックでアイテムを選択、ダブルクリックでディレクトリに移動）。インポートされたリファレンスは、作成時に自動分析されます。
3. ローカルディレクトリのインポートは、すべてのサブディレクトリを**再帰的に**スキャンして、画像（.png、.jpg、.jpeg、.gif、.bmp、.webp、.tiff、.tif、.tga、.ico、.svg）と3Dモデル（.glb、.gltf）を探します。画像ファイルは**相対シンボリックリンク**を使って**シンボリックリンク**されます（重複なし、マシン間でポータブル）。3Dモデルファイル（.glb/.gltf）は、埋め込まれたテクスチャが**自動的に抽出**されます — base64データURI、バイナリバッファチャンク、外部テクスチャ参照のすべてが処理されます。抽出されたテクスチャはコピーとして保存されます（衝突を避けるためモデル名をプレフィックス）。S3インポートはページネーション付きで再帰的にリストし、ファイルをローカルに**ダウンロード**します。スタイルごとに最大**100枚のリファレンス画像**がインポートされます。サポートされる拡張子は`backend/config.py`（`IMAGE_EXTENSIONS`と`MODEL_EXTENSIONS_WITH_TEXTURES`）に集約されています。
4. **2フェーズのコヒージョン認識分析**：フェーズ1は8枚の画像をClaude Sonnetに送り、コヒージョンレベル（高/中/低）を判定します — 高は統一されたスタイル、中は異なるテーマを持つ共有された構造、低は多様なスタイルを意味します。フェーズ2は、コヒージョン評価をリファレンス画像とともにClaude Opusに供給し、コレクションの種類に応じて適切に分析するよう導きます。スタイルに20枚を超えるリファレンスがある場合、アナライザーはOpusビジョンコール用に20枚の多様な代表サブセットを選択します — ファイル名グループとファイルサイズの多様性にわたるカバレッジを確保します。AIには、合計何枚の画像が存在し、そのうち何枚を見ているかが伝えられます。分析プロンプトは、透明背景上のゲームアセット向けに特別に設計されています — マテリアル固有のレンダリング詳細、プロポーションシステム、影/照明の詳細を尋ねます。`materials`（石、木、金属がどうレンダリングされるか）や`detail_level`（どの表面ディテールが見えるか、簡略化されているか）を含む9つのスタイル属性を抽出します。生成ヒントは、パースペクティブ、レンダリング、マテリアル、カラーパレット、プロポーション、エッジ処理、影/照明、ディテールレベル、背景の8次元をカバーする200ワードに拡張されます — 生成されたアセットが既存のリファレンスと視覚的に溶け込むほど具体的です。
5. スタイル詳細ビューで、**「Import & Analyze」**を使って、リファレンスの追加と分析のトリガーを1ステップで行います。ドラッグ＆ドロップアップロードもサポートされ、新しい画像が追加されると**自動的に再分析**されます。
6. **「Re-Analyze Style」**は初回分析後に表示され、いつでも手動で分析を再実行できます。
7. **生成ヒント**は分析コンテキストの一部です — AIは分析時に、リファレンス画像とあなたのヒントの両方を「アーティストのガイダンス」として受け取るため、スタイルプロファイルは視覚的な外観だけでなく意図を理解します。生成ヒントの編集も、**自動再分析**をトリガーします。
8. **2D Image Studio**に戻り、ドロップダウンからスタイルを選択します — 生成されるすべてのアセットが、そのビジュアルアイデンティティ（パレット、パースペクティブ、レンダリングスタイル、ムード）に合致します。

### 📝 6.6 スタイル分析フロー

```
┌──────────────────────────────────────────┐
│ Create / Import style                    │
│ (reference images uploaded or imported)  │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│ Phase 1: Cohesion Check                  │
│ Claude Sonnet — 8 images — ~$0.01        │
│ Determines: high / medium / low          │
│   high   = unified style                 │
│   medium = shared structure, diff themes │
│   low    = diverse collection            │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│ Phase 2: Full Analysis                   │
│ Claude Opus — up to 20 images            │
│ Guided by cohesion level                 │
│ + Artist's Guidance (user hints)         │
│ Extracts 9 style attributes              │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│ Phase 3: Hint Generation                 │
│ Claude Sonnet — 200-word hints           │
│ 8 dimensions: perspective, rendering,    │
│ materials, palette, proportions, edges,  │
│ shadow/lighting, detail level            │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│ Stored in profile.json                   │
│ ~$0.14 total per style analysis          │
│ Used in all future generation            │
└──────────────────────────────────────────┘
```

### 📝 6.7 Type Studio

画像にテキストを追加したり、AIデザインのタイポグラフィでスタンドアロンのテキストアセットを生成したりします。

- **2つのモード**：「On Image」はギャラリー画像にテキストを合成し、「Standalone」は透明背景にテキストをレンダリングします。
- **複数行テキストエディタ**、行ごとのフォント選択、位置コントロール、**音声入力**（行ごとのマイクボタン — Nova Sonic文字起こしでテキストを口述）付き。
- **AIデザインレイアウト** — AIが色、サイズ、位置、効果（影、アウトライン、グロー）を提案します。異なるクリエイティブな方向性のために1〜5個のレイアウトオプションをリクエストできます。レイアウトに使用される**LLMモデル**は設定可能です（最高品質にはComplex LLM、より安価にはFast LLM） — レジストリのカテゴリから読み取ります。
- **ライブプレビュー付きフォントピッカー** — スタイルフォント、8つのバンドルフォント（Roboto、Open Sans、Lato、Montserrat、Playfair Display、Oswald、Raleway、Source Code Pro）、システムフォント、**クライアントサイドで検出されたフォント**（Local Font Access APIまたはキャンバスプロービング経由）。
- **前処理/後処理** — 2D Image Studioと同じワークフロー、後処理用の「Apply」ボタン付き。SVG変換はデフォルトでオンです。
- **クリックでズーム** — 結果プレビューをクリックすると、完全なズーム/パン、メタデータ、ダウンロード、画像編集ツールを備えたAssetViewerが開きます。
- 結果は新しいギャラリーアセットとして保存されます（オリジナルが上書きされることは決してありません）。

### 📝 6.8 ギャラリー

- **メイソンリーレイアウト**での、生成済みの全画像と動画の**統合ビュー**（各アセットは本来のアスペクト比 — 縦長、正方形、横長 — で表示され、決して中央でクロップされません）、**メディアフィルター**（All / 2D Artwork / 3D Models / Video）付き。**3D Models**フィルターは、すでに生成済みの3Dモデルを持つアセットのみを表示し、それらのアセットはタイル上に**3Dバッジ**を持ちます。
- すべてのアセット（プロンプト、スタイル、モデル）にわたる即座のフィルタリングのための**検索バー**。
- 一括削除のためのチェックボックス付き**マルチセレクト**（画像と動画の両方のアセットを処理）。削除は**バッチ対応**です — 生き残った兄弟がいくつのバリアントが削除されたかを追跡するため、部分的なバッチをImage Studioで再読み込みすると「X of Y images remaining (Z deleted)」と表示されます。
- アセットは、インメモリのメタデータキャッシュで即座にロードされます。新しい順にソート。
- 大規模コレクション向けのページネーションサポート（limit/offset）。
- ギャラリーは、戻ってきたとき、および任意の編集や動画生成の完了後に自動更新されます。
- **動画カード**は、再生オーバーレイ、VIDEOバッジ、長さインジケーター付きのサムネイルを表示します。クリックすると動画プレイヤーモーダルが開きます。
- アセットタイプに基づく**コンテキストアクションボタン**：画像スタジオで再読み込みする**「2D Studio」**（インディゴ）、Type Studioで開く**「Add Text」**（エメラルド）、テキストアセット用の**「Edit in Type Studio」**（パープル）。
- 任意の画像をクリックすると、次を備えた**AssetViewer**モーダルが開きます：
  - **ズーム/パン** — マウスホイールでズーム、ドラッグでパン、アクティブモードをハイライトするFit/1:1ボタン。
  - **Editタブ** — 画像を直接インペイント、消去、アウトペイント、検索＆置換、リカラーします。モードごとに2種類のエディタが提供されます：**マスクベース**（Stability） — ブラシツールでマスクをペイントし、プロンプトを入力して適用；**マスク不要の指示エディタ**（Qwen-Image-Edit、デプロイ済みの場合） — 変更を言葉で説明するだけ、マスク不要。マスク不要モデルではブラシコントロールが自動的に隠れます。編集モデルを選んで適用します；デフォルトは元の画像を置き換え、「Replace original」のチェックを外すと新しいアセットとして保存されます（すべての編集がバージョン履歴を保持）。
  - **Previous / Next** — 矢印ボタンとキーボードの左右で、ビューアを閉じずにリストを移動します。
  - **完全なメタデータ**：元のプロンプト、AI改善プロンプト、生成プロンプト、ネガティブプロンプト、スタイル、アセットタイプ、画像モデル（分かりやすい名前）、サイズ、シード、バッチID、オプション/バリエーションインデックス、IP宣言ステータス、ファイル名、作成日。
- **スタイルスナップショット**：各アセットは、生成時に使用されたスタイルのスナップショット（名前、説明、ヒント、分析）を保存します。元のスタイルが後で削除されても、アセットは完全なコンテキストを保持します。後方互換 — スナップショットのない古いアセットも通常どおり表示されます。

### 📝 6.9 音声入力

プロンプトエディタの横のマイクボタンをクリックして、プロンプトを口述します。オーディオはNova Sonicに送られて文字起こしされます。

> [!NOTE]
> 音声文字起こしにはNova Sonicの双方向ストリーミングAPIが必要で、これは互換性のあるboto3バージョンとus-east-1で有効化されたモデルアクセスに依存します。ストリーミングAPIが利用できない場合、サービスはプレースホルダーの確認応答を返します。完全なリアルタイム文字起こしは、Nova Sonicストリーミングが適切に設定されている場合に機能します。

### 📝 6.10 ビュー状態の保持

ナビゲーション順序：**Style Library → 2D Image Studio → Type Studio → Video Studio → Gallery**。ビュー間の切り替えは、各ビューのDOM状態を保持します。生成された結果、フォーム入力、スクロール位置は、ナビゲーションを越えて残ります。2D Image StudioとVideo Studioのアンバーのリセットボタンだけが、それらの状態をクリアする唯一の方法です。

### 📝 6.11 モデル管理

すべてのAIモデル設定は`backend/model_registry.json`に集約されています — 信頼できる唯一の情報源です。モデル、リージョン、料金、品質ティア、フォーマットテンプレートはすべてここに保存され、UIまたはAPIを通じて管理されます：

- 任意のスタジオのサイドバーで**「Model Settings」**をクリックすると管理モーダルが開きます — そのスタジオに関連するタブが開きます。
- スタジオ別に整理された**7つのタブ**：
  - **Image Studio** — 画像生成モデル（SD 3.5 Large、Stable Image Ultra、Stable Image Core、さらにセルフホストのFLUX、HunyuanImage、Qwen-Image）、リージョン、品質ティア、プロンプト制限、モデレーション厳格度
  - **Video Studio** — 動画モデル（Nova Reel、Luma Ray）、S3バケット設定、リージョン、料金
  - **Chat Studio** — 検出されたチャット/LLMモデル（16プロバイダーから80以上）、コンテキストウィンドウ、ビジョン機能、1Kトークンあたりの料金
  - **Type Studio** — テキストレイアウト生成用のLLMモデル（Complexまたはfast LLM）
  - **Shared Studio** — スタジオ横断のLLMカテゴリ（Fast LLM、Complex LLM、Fallback LLM、Voice）、後処理モデル（背景削除、アップスケール）
  - **Prompt Templates** — 6つのワークフローセクションに整理された28の編集可能なLLM指示プロンプト（セクション4.4参照）
  - **Registry JSON** — 完全なモデルレジストリ用の生のJSONエディタ
- すべてのセクションは、素早いナビゲーションのための**Show All / Hide All**トグル付きで**折りたたみ可能**です。
- LLMカテゴリと後処理は、**ドロップダウンモデルピッカー**（検出されたモデルから populate）を使用します — 生のテキストフィールドではありません。
- **Sync from AWS**：すべてのBedrockサポート対象AWSリージョン（動的に検出）をスキャンし、新しい画像、動画、**チャットモデル**を自動登録し、リージョンの可用性を更新し、AWS Pricing APIからモデルごとの料金を取得し、利用できなくなったモデルを無効化します。**ライブ進捗オーバーレイ**が、スキャンされる各リージョンをストリーミングします。これはAWS検出APIを呼び出す**唯一の**アクションです — 他のすべての操作はキャッシュされたレジストリから読み取ります。
- **常に最新のClaudeを使用**：各Syncは、あなたの**Fast LLM**をアカウントで利用可能な最新のClaude Sonnetに、**Complex LLM**を最新のClaude Opusに自動的にロールするため、非推奨モデルに取り残されることは決してありません — 手動設定は不要です。カテゴリに特定のモデルを手動で選んだ場合、それは**ピン留め**され、自動ロールはそれに手を付けません（新しいものが登場したときに通知するだけです）。
- **カスタムモデル検出**：Syncは、**ファインチューニング済みカスタムモデル**（`ListCustomModels`）、**インポート済みモデル**（`ListImportedModels`）、**オンデマンドデプロイメント**（`ListCustomModelDeployments`）または**プロビジョンドスループット**（`ListProvisionedModelThroughputs`）を持つモデルも検出します。カスタムモデルは、ベースモデルからフォーマットファミリーを自動的に継承します。
- **自動検出**：新しい基盤モデルは`enabled=true`で登録されます — 管理者が無効化できます。既存のモデルは、`available_regions`とBedrockメタデータ（モダリティ、ライフサイクル、ARN）が自動的に更新されます。
- **スタイル付き確認ダイアログ**：すべての破壊的アクション（Sync、削除、リセット）はカスタムスタイルのモーダルを使用します — ブラウザの`confirm()`ポップアップはありません。
- 変更は、Admin API経由で`model_registry.json`に即座に永続化されます。
- レジストリは後方互換です — 既存のアセットは、生のBedrockモデルIDではなく、モデルキー（例：`sd35_large`）を参照します。

### 📝 6.12 セルフホストモデル（Amazon SageMaker上のカスタムモデル）

ArtSmokerは、あなた自身のAWSアカウントの**Amazon SageMaker**上にオープンソースAIモデルをデプロイでき、Amazon Bedrockが提供する以上に機能を拡張できます。これらはBedrockモデルと並んで実行され、同じスタジオのドロップダウンに表示されます。

**拡張可能なモデルカタログ：** 画像生成、アップスケール、背景除去、深度推定、セグメンテーション、動画にまたがるオープンソースモデルの組み込みカタログを同梱しています。新しいモデルの追加に必要なのはカタログエントリだけです — コード変更は不要です。UI（+ Add Model）からカスタムモデルを追加することもできます。カタログと利用可能なモデルは時間とともに進化します。

**デプロイメントオプション：**
- **Async（scale-to-zero）** — 生成時のみ支払い。アイドル時はゼロにスケール（$0コスト）、新しいリクエストで自動的にスケールアップ。コールドスタート約5〜10分。
- **Always-On** — 即座のレスポンス、～$1.41/時間（ml.g5.xlarge）

**デプロイ方法：** Model Settings → Custom Modelsタブ → Deployをクリック。SageMakerコンテナは起動時にHuggingFaceからモデルの重みを直接取得します — 数GBのローカルダウンロードは不要です。

**CPUオフロード：** 大規模拡散モデルは、より小さなGPUインスタンスに収めるためにインテリジェントなCPUオフロードを使用します。各モデルのカタログエントリが戦略を指定します — `model_cpu_offload`（アクティブなレイヤーをGPUに保持）または`sequential_cpu_offload`（非常に大きなモデル向けの積極的なレイヤーごとのオフロード）。推論ハンドラーによって自動的に適用されます。

**Pending Jobsを伴う非同期生成：** セルフホストモデルは非同期に生成します。**Pending Jobs**パネルが2D Image Studioに表示され、進捗インジケーター付きでアクティブなジョブを表示します。完成した画像は自動的にギャラリーに届きます — ポーリングやページ更新は不要です。

**HuggingFaceトークン管理：** ゲート付きモデルには読み取り専用のHuggingFaceトークンが必要です。トークンは、あなたのアカウントの**AWS Secrets Manager**に暗号化されて保存され、UI経由で管理され（設定/更新/削除）、それを必要とするすべてのモデル間で共有されます。すべてのモデルをteardownすると、トークンは自動的にクリーンアップされます。

**ゲートアクセス事前チェック：** ゲート付きデプロイの前に、ダイアログは、あなたの保存されたトークンを使って、モデルが取得する**すべての**HuggingFaceリポジトリ（自身の重みに加えて任意の依存関係）をプローブし、リポジトリごとに✓/✗と正確な次のステップを表示します — HuggingFaceで*この*リポジトリのライセンスを承諾するか、トークンを追加するか。必要なすべてのリポジトリに到達可能になるまでデプロイはブロックされたままなので、ライセンス承諾の忘れは、コールドスタートの数分後ではなく、ダイアログ内で素早く失敗します。

**セットアップ：** すでにBedrockに使用している**同じIAMロール**に、Amazon SageMakerとSecrets Managerのパーミッションを追加してください — 別のロールや環境変数は不要です。ArtSmokerはEC2/ECS上であなたのロールを自動検出するか、必要に応じて`ArtSmokerSageMakerRole`を自動作成します。

```bash
# Add Amazon SageMaker permissions to your existing ArtSmoker role (one command)
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
```

**Python依存関係：** `huggingface_hub>=0.23`（`pip install huggingface_hub`でインストール）

### 📝 6.13 画像＆動画生成モデル

すべてのモデルは、レジストリから**動的に検出**されます — ハードコードではありません。Image Studioドロップダウンは、ページ読み込み時に`GET /api/admin/models/image-options`から、Video Studioドロップダウンは`GET /api/admin/models/video-options`から populate されます。レジストリに登録され有効化された任意のモデルが、自動的に表示されます。

**Image Model**ドロップダウンが主要な選択です。その下に、アクティブなリージョン、品質ティア、画像あたりのコストを示すスマートサマリー行があります。展開可能な**Advanced**セクションで、次を上書きできます：

- **Quality** — 品質ティア（Standard/Premiumの価格分割）をサポートするモデルはドロップダウンを表示し、ティアのないモデルは「Default」を表示します。ティアは、`quality_options`を通じてレジストリでモデルごとに宣言されます。
- **Region** — 選択したモデルが利用可能なリージョンを、料金付きで安い順にソートして表示します。「Auto」は最も安いリージョンを選択します。

**コスト見積もり**は、すべての選択（モデル×品質×リージョン×オプション×バリエーション）に基づいて動的に更新されます。

**フォーマットファミリー**：モデルは、レジストリ（`format_families`）からリクエストテンプレートを読み取る汎用インボーカー（`invoke_image_model`）を通じて呼び出されます。現在、画像生成（2）、画像編集（8）、後処理（2）、動画生成（2）をカバーする15ファミリー：
- **画像生成**：`stability_text_to_image`（SD 3.5 Large、Stable Image Ultra、Stable Image Core）、さらにFLUX、HunyuanImage、Qwen-Image用のセルフホストファミリー（`sagemaker_*`）
- **画像編集**：`amazon_inpainting`、`amazon_outpainting`、`stability_inpaint`、`stability_outpaint`、`stability_erase`、`stability_search_replace`、`stability_search_recolor`、`stability_control`、`stability_style_transfer`
- **後処理**：`stability_remove_bg`、`stability_upscale`
- **動画**：`nova_reel`、`luma_ray`

新しいBedrock画像モデルの追加にはコード変更が一切不要です — 正しいフォーマットファミリーで、Admin APIまたは自動検出を通じて登録するだけです。

**モデル最適化されたプロンプトエンジニアリング**：プロンプトは、[AWSドキュメント](https://docs.aws.amazon.com/nova/latest/userguide/prompting-image-generation.html)に従って、コマンドではなく説明的なキャプションとして自動的に構造化されます。否定語はメインプロンプトから削除され、除外用語は別の**ネガティブプロンプト**として送信されます。プロンプトは、レジストリの各モデル固有の`prompt_limit`に切り詰められます。

> [!NOTE]
> **モデレーション感度はモデルによって異なり**、レジストリ（`moderation_strictness`）で追跡されます。Amazon Bedrock Stabilityモデル（SD 3.5 Large、Stable Image Ultra、Stable Image Core）はAWSプラットフォームのモデレーションを適用し、「moderate」にチューニングされています；セルフホストモデル（FLUX、HunyuanImage、Qwen-Image）は、プラットフォームによるコンテンツフィルターなしで、あなた自身のアカウントで実行されます。ArtSmokerはブロックを自動的に処理します — プロンプトが拒否されると、システムはリライトを提案する前に、厳格度順に並べた代替モデルを試します。

## 📌 7. 技術スタック

| レイヤー | テクノロジー |
|-------|-----------|
| バックエンド | FastAPI (Python 3.11+)、boto3、Pydantic |
| フロントエンド | Vanilla JS、Tailwind CSS (CDN) |
| AI (LLM) | Claude Sonnet（高速タスク）、Claude Opus（複雑なタスク） |
| AI (画像) | Stable Diffusion 3.5 Large、Stable Image Ultra、Stable Image Core（Amazon Bedrock）；FLUX.2/FLUX.1、HunyuanImage 3.0、Qwen-Image（SageMakerでセルフホスト） |
| AI (後処理) | Stability AI（背景除去、Creative Upscale） |
| AI (チャット) | Bedrock ConverseStream経由で16プロバイダーから80以上のLLM（Claude、Nova、Llama、Mistralなど） |
| AI (動画) | Nova Reel v1.0/v1.1（最大2分）、Luma AI Ray v2（最大9秒） |
| AI (音声) | Nova Sonic（双方向ストリーミング経由の音声テキスト変換） |
| i18n | カスタムt()関数、817キー×6言語、逆引きDOM翻訳 |
| SVG変換 | vtracer（主要）、potrace（フォールバック）、Pillow（最終手段） |
| テキストレンダリング | Pillow（影、アウトライン、グロー効果） |
| ストレージ | ローカルファイルシステム（S3対応インターフェース） |
| 開発 | 静的ファイル用のノーキャッシュミドルウェア；`POST /api/log`経由のクライアントサイドエラーロギング |

フロントエンドにビルドステップは不要です。

## 📌 8. セキュリティモデル

ArtSmokerは**ローカル/信頼されたネットワークの開発ツール**として設計されています — 開発者自身のマシンまたはプライベートEC2インスタンスで動作します。セキュリティモデルはこれを反映しています：

- **認証なし** — すべてのAPIエンドポイントがオープン。ローカル開発とプライベートチームデプロイに適切。
- **ファイルシステムブラウザ** — `GET /api/browse/local`エンドポイントは、サーバープロセスがアクセスできる任意のディレクトリの閲覧を許可します。これは、あなたのマシンからリファレンスアートをインポートするための意図的な設計です。
- **フォント配信** — パストラバーサル保護が、フォントファイルのリクエストが想定されたディレクトリ内に留まることを検証します。
- **S3アクセス** — S3の閲覧とインポートは、サーバーのAWS認証情報を使用します。ユーザーは、IAMロールが許可する任意のS3バケットにアクセスできます。

> [!WARNING]
> 認証とパス制限を追加せずに、信頼されていないネットワークにArtSmokerを公開しないでください。本番環境の強化ガイダンス（フェーズ4でCognito認証を追加）については、[SPEC.mdのデプロイメントロードマップ](SPEC.md#16-deployment--scaling-roadmap)を参照してください。

## 📌 9. API

インタラクティブドキュメントは**http://localhost:8000/docs**（Swagger UI）にあります。

主要エンドポイント：

| エンドポイント | 目的 |
|----------|---------|
| **Generation** | |
| `POST /api/generate/` | SSEストリーミングでアセットを生成（オプション×バリエーション） |
| `POST /api/generate/post-process` | 既存アセットに処理を適用 |
| `POST /api/generate/edit` | 画像編集：インペイント、アウトペイント、消去、検索置換など。ソース画像、マスク、プロンプト、モデルを受け取る。 |
| `POST /api/generate/suggest-edit-prompt` | Editタブ用のAI「Generate Prompt」：画像＋元プロンプトを読み取り、指定モードの編集プロンプトを返す。対象の編集モデル向けにスタイリング（キャプション対指示） |
| `POST /api/generate/analyze-moderation` | モデレーションでブロックされたプロンプトを分析し、安全なリライトを提案 |
| **Styles** | |
| `POST /api/styles/` | スタイルプロファイルを作成 |
| `POST /api/styles/{id}/import` | ローカルフォルダまたはS3 URIからリファレンスを一括インポート |
| `POST /api/styles/{id}/analyze` | AIスタイル分析をトリガー |
| **Prompt** | |
| `POST /api/refine-prompt/` | 精緻化されたプロンプトをプレビュー |
| `POST /api/transcribe/` | 音声テキスト変換（Nova Sonic） |
| **Gallery** | |
| `GET /api/gallery/` | 生成アセットを閲覧（limit/offsetページネーション対応） |
| `GET /api/gallery/batch/{batch_id}` | バッチの完全なオプション×バリエーション構造を再構築 |
| `DELETE /api/gallery/` | アセットを一括削除 |
| **Type Studio** | |
| `POST /api/type-studio/preview` | テキストオーバーレイプレビューをレンダリング |
| `POST /api/type-studio/suggest` | テキストのAIレイアウト提案 |
| `GET /api/type-studio/fonts` | 利用可能なフォントを一覧表示 |
| **Browse** | |
| `GET /api/browse/local?path=~` | ローカルディレクトリの内容を閲覧 |
| `GET /api/browse/s3/buckets` | 利用可能なS3バケットを一覧表示 |
| `GET /api/browse/s3?bucket=name&prefix=path` | S3バケットの内容を閲覧 |
| **Chat** | |
| `POST /api/chat/stream` | SSE経由でLLMレスポンスをストリーミング（Bedrock ConverseStream） |
| `GET /api/chat/models` | 利用可能な全チャットモデルを一覧表示（基盤＋カスタム＋インポート） |
| `POST /api/chat/sessions` | 新しいチャットセッションを作成 |
| `GET /api/chat/sessions` | チャットセッションを一覧表示 |
| `GET /api/chat/sessions/{id}` | 完全なセッション（メッセージ＋メタデータ）をロード |
| `PUT /api/chat/sessions/{id}` | セッションを更新（タイトル、メッセージ、モデル、temperature） |
| `DELETE /api/chat/sessions/{id}` | セッションを削除 |
| `POST /api/chat/sessions/{id}/duplicate` | セッションを複製 |
| `GET /api/chat/sessions/{id}/export` | セッションをMarkdownとしてエクスポート |
| `GET /api/chat/sessions/{id}/search?q=` | セッションのメッセージ内を検索 |
| `POST /api/chat/compact` | LLM要約で古いメッセージを圧縮 |
| `POST /api/chat/generate-title` | 最初のやり取りからセッションタイトルを自動生成 |
| **Video** | |
| `POST /api/video/generate` | 非同期動画生成ジョブを開始 |
| `GET /api/video/status/{job_id}` | 動画生成ジョブのステータスをポーリング |
| `GET /api/video/jobs` | すべての動画生成ジョブを一覧表示 |
| `GET /api/video/{id}/mp4` | 動画MP4ファイルを配信 |
| `GET /api/video/{id}/thumbnail` | 動画サムネイルを配信 |
| `DELETE /api/video/{id}` | 動画を削除 |
| **Admin** | |
| `GET /api/admin/models` | 完全なモデルレジストリを取得（LLM、画像モデル、後処理） |
| `GET /api/admin/models/image-options` | ドロップダウン用の有効化されたテキストから画像へのモデル（料金、品質ティア、リージョン付き）。`?region=`フィルターを受け付ける。 |
| `GET /api/admin/regions` | Bedrockサポート対象AWSリージョンのキャッシュ済みリスト（AWSコールなし） |
| `PATCH /api/admin/models/category/{name}` | LLMカテゴリ設定を更新 |
| `PATCH /api/admin/models/image/{key}` | 画像モデル設定を更新 |
| `POST /api/admin/models/image` | 新しい画像モデルを追加 |
| `POST /api/admin/discover/refresh-all` | 完全更新：リージョン検出＋モデルスキャン＋料金取得＋古いデータの整理。AWS検出APIを呼び出す唯一のエンドポイント。 |
| `POST /api/admin/discover/{region}/auto-register` | 単一リージョンをスキャンしてモデルを検出、新規を登録、既存のリージョンを更新 |
| `GET /api/admin/discover/{region}` | リージョン内の利用可能なBedrockモデルを検出（生のリスト） |
| `GET /api/admin/templates` | 28の編集可能なプロンプトテンプレートをすべて取得 |
| `PATCH /api/admin/templates/{name}` | テンプレートを更新（必須変数を検証） |
| `POST /api/admin/templates/{name}/reset` | テンプレートをデフォルトにリセット |
| `POST /api/admin/templates/{name}/enhance` | テンプレートをAIで強化 |
| **System** | |
| `POST /api/log` | クライアントサイドのエラー/警告ロギング（サーバーコンソールに`[CLIENT]`として記録） |
| `GET /api/health` | ヘルスチェック＋AWS認証情報/Bedrock検証 |

## 📌 10. プロジェクト構造

```
ArtSmoker/
├── backend/
│   ├── main.py              # FastAPI app, startup validation, static mount
│   ├── config.py            # Settings (AWS regions, model IDs, paths, limits)
│   ├── model_registry.json  # Single source of truth: models, regions, pricing, format families, quality tiers
│   ├── requirements.txt
│   ├── prompt_templates.json # Editable LLM directive prompts — runtime source of truth (28 templates)
│   ├── routers/
│   │   ├── generate.py      # Two-level asset generation + SSE streaming
│   │   ├── styles.py        # Style profile CRUD + directory/S3 import + analysis
│   │   ├── gallery.py       # Asset browsing + file serving + bulk delete
│   │   ├── typestudio.py    # Type Studio: text overlay, font serving, AI layout
│   │   ├── video.py         # Video generation (async), job polling, MP4/thumbnail serving
│   │   ├── chat.py          # Chat Studio: LLM streaming, sessions, export, context compaction
│   │   ├── browse.py        # Server-side file/S3 browser for reference import
│   │   ├── refine.py        # Prompt refinement preview + translation preview
│   │   ├── transcribe.py    # Voice transcription
│   │   └── admin.py         # Model registry management + Bedrock discovery + prompt templates
│   ├── services/
│   │   ├── bedrock_client.py     # Shared Bedrock client with connection pooling
│   │   ├── model_registry.py     # Model registry: loads/saves model_registry.json
│   │   ├── prompt_engineer.py    # Claude: prompt refinement + concept generation
│   │   ├── image_generator.py    # Routes to Bedrock (SD 3.5 / Ultra / Core) or SageMaker (FLUX / Hunyuan / Qwen)
│   │   ├── style_analyzer.py     # Two-phase style analysis (cohesion + full)
│   │   ├── post_processor.py     # Stability AI: bg removal, upscale; vtracer: SVG
│   │   ├── transcriber.py        # Nova Sonic: streaming speech-to-text
│   │   ├── import_dedup.py       # Smart deduplication (rotations, animations, folders)
│   │   ├── texture_extractor.py  # glTF/GLB texture extraction
│   │   ├── prompt_translator.py  # Auto-detect language + translate to English
│   │   ├── prompt_templates.py   # Editable LLM directive prompts (load/save/validate)
│   │   ├── video_generator.py   # Video: async Bedrock invoke, S3 download, ffmpeg thumbnails
│   │   ├── cost_tracker.py      # Request-scoped cost accumulator
│   │   ├── custom_models.py    # Self-hosted model catalog (extensible)
│   │   ├── async_jobs.py       # Async generation job queue (Pending Jobs panel)
│   │   ├── sagemaker_deployer.py # Amazon SageMaker endpoint management (direct HF pull for HF models)
│   │   └── sagemaker_invoker.py  # Routes inference to Amazon SageMaker endpoints
│   ├── models/
│   │   ├── style_profile.py       # StyleProfile, AnalyzedStyle, Create/Update
│   │   ├── generation_request.py  # GenerationRequest, AssetType, ImageModel enums
│   │   └── generation_result.py   # GenerationResult, OptionResult, VariantResult
│   └── storage/
│       └── local_store.py         # Local filesystem (S3-compatible interface)
├── frontend/
│   ├── index.html           # SPA entry point
│   ├── css/styles.css       # Dark theme + animations
│   └── js/
│       ├── app.js               # SPA router + DOM caching + navigation + showConfirm()
│       ├── i18n/
│       │   ├── i18n.js          # Core: t() function, language switching, reverse lookup
│       │   ├── en.json          # English (base) — 817 keys
│       │   ├── ja.json          # Japanese
│       │   ├── zh.json          # Simplified Chinese
│       │   ├── ko.json          # Korean
│       │   ├── fr.json          # French
│       │   └── es.json          # Spanish
│       ├── services/api.js      # Backend API client
│       └── components/
│           ├── ImageStudio.js   # 2D Image Studio (options × variations)
│           ├── TypeStudio.js    # Type Studio (text overlay)
│           ├── VideoStudio.js   # Video Studio (text-to-video generation)
│           ├── ChatStudio.js    # Chat Studio (multi-model LLM chat)
│           ├── Gallery.js       # Gallery grid + search + bulk ops
│           ├── StyleLibrary.js  # Style management + file browser
│           ├── AssetViewer.js   # Full-size preview + metadata + download
│           ├── ModelSettings.js # Model registry admin UI (modal)
│           ├── PromptEditor.js  # Two-area prompt editor + compose
│           └── VoiceInput.js    # MediaRecorder + transcription
├── data/
│   ├── styles/              # Style profiles + reference images (symlinked)
│   ├── generated/           # Output assets (PNG + SVG + metadata.json)
│   ├── video/               # Video assets (MP4 + thumbnails + job metadata)
│   └── chat/                # Chat sessions (JSON per session)
├── SPEC.md                  # Full technical specification (rebuild blueprint)
└── README.md                # This file
```

## 📌 11. 設定可能な制限

`backend/config.py`の設定は、環境変数（プレフィックス`ARTSMOKER_`）で上書きできます：

| 設定 | 環境変数 | デフォルト | 目的 |
|---------|-------------|---------|---------|
| `max_reference_images` | `ARTSMOKER_MAX_REFERENCE_IMAGES` | 100 | スタイルごとにインポートされる最大画像数 |
| `max_analysis_images` | `ARTSMOKER_MAX_ANALYSIS_IMAGES` | 20 | 分析コールごとにAIに送られる最大画像数 |
| `aws_region_models` | `ARTSMOKER_AWS_REGION_MODELS` | us-west-2 | Claude＋Stability AIモデルのリージョン |
| `aws_region_images` | `ARTSMOKER_AWS_REGION_IMAGES` | us-east-1 | Amazon（Nova Sonic音声、Nova Reel動画）のリージョン |
| `aws_profile` | `ARTSMOKER_AWS_PROFILE` | None | AWSプロファイル名（未設定の場合はデフォルトチェーンを使用） |
| `auto_update` | `ARTSMOKER_AUTO_UPDATE` | true | 起動時のgit pull＋24時間ごとの定期チェック、更新時の自動再起動 |

`max_analysis_images`を減らすと、分析ごとのAIビジョンコストが減ります。`max_reference_images`を減らすと、ストレージが制限されます。どちらも予算に基づいて調整できます。

## 📌 12. Amazon Bedrock料金＆コスト内訳

> [!IMPORTANT]
> **モデルは急速に非推奨化・変更されます。** 新しいモデルが頻繁に登場し、古いモデルは頻繁に廃止されるため、ドキュメントにハードコードされた特定のモデル名や料金はすぐに古くなります。ArtSmokerはこれを自動的に処理します — **AWSから同期**するたびに、現在のモデルラインナップを再検出し、共有LLMスロットを最新のClaude Sonnet/Opusに自動ロールし、AWS Pricing APIからライブのモデルごとの料金を`model_registry.json`に更新します。**アプリが信頼できる情報源**です — どのモデルが存在し、いくらかかるか（選択したモデル、品質ティア、リージョン、バッチサイズに応じてImage Studioサイドバーにライブ表示）の両方について。以下のモデル名や数値は**あくまで参考例**です — 常にアプリ内または公式の[Amazon Bedrock料金ページ](https://aws.amazon.com/bedrock/pricing/)で現在のモデル/料金を確認してください。

アプリの**デフォルトリージョン**は`us-west-2`（Claude、Stability AI）と`us-east-1`（Amazon Nova Sonic、Nova Reel）です；料金はリージョンによって異なります。コストモデルについては[SPEC.md](SPEC.md#14-amazon-bedrock-pricing--cost-breakdown)も参照してください。

### 📝 12.1 単位あたりの料金

何にコストがかかるか、その課金単位（現在の単価はアプリを参照）：

| サービス | 課金 | 備考 |
|---------|--------|-------|
| **LLMプロンプトエンジニアリング＆チャット**（Claude Sonnet / Opus、Sync時に最新へ自動ロール） | 入力/出力トークンあたり | プロンプト精緻化、コンセプト、チャット、スタイル分析、モデレーション |
| **Bedrock画像生成**（Stable Diffusion 3.5 Large、Stable Image Ultra、Stable Image Core） | 画像あたり | 価格はUltra ≫ SD 3.5 ≫ Core；ライブ数値はアプリ内に表示 |
| **セルフホスト画像 / 3D**（FLUX、HunyuanImage、Qwen-Image、TripoSG、TRELLIS.2） | SageMakerインスタンスのGPU秒あたり | アイドル時はscale-to-zeroで$0；画像単位の課金ではない |
| **後処理**（背景除去、Creative Upscale） | 画像あたり | Stability AIサービス |
| **SVG変換** | 無料 | ローカル（vtracer/potrace）— $0.00 |

> [!NOTE]
> 料金は、2026年3月時点の公式[Amazon Bedrock料金ページ](https://aws.amazon.com/bedrock/pricing/)からのものです。料金は変更される場合があります — 予算を立てる前に、常に公式ソースで確認してください。

### 📝 12.2 追加のLLMコスト（使用ごと）

これらのLLMコールは生成ワークフローに含まれますが、以下のバッチコスト表には個別に項目化されていません：

| コール | モデル | タイミング | 概算コスト |
|------|-------|------|-------------|
| **Prompt Pre-Check** | Claude Sonnet | 生成前（トグルが有効な場合） | ～$0.005 |
| **Moderation Rewrite** | Claude Sonnet | すべてのモデルがプロンプトを拒否した場合のみ | ～$0.005 |
| **Type Studio Layout** | Claude Opus | 各AIレイアウト提案リクエスト | ～$0.02〜$0.05 |

これらは小さいものです — 事前チェックとモデレーションリライトはそれぞれ1セントの数分の1です。Type Studioレイアウトは、単一オプションのプロンプト精緻化に相当します。

### 📝 12.3 スタイル分析コスト（スタイルごとに1回）

スタイルあたり～**$0.14**（Claude Opusに20枚の画像＋Claude Sonnetでの8枚のコヒージョンチェック）。コヒージョンチェックは～$0.01を追加します（8枚の画像でのSonnetは非常に安価です）。

### 📝 12.4 バッチサイズ別の生成コスト

プロンプト精緻化/コンセプト生成＋画像生成を含みます：

| シナリオ | Stable Image Core | Stable Diffusion 3.5 Large | Stable Image Ultra |
|----------|-------------------|-------------|-------------------|
| 1オプション×1バリエーション | ～$0.05 | ～$0.09 | ～$0.15 |
| 1オプション×5バリエーション | ～$0.21 | ～$0.41 | ～$0.71 |
| 5オプション×5バリエーション | ～$1.05 | ～$2.05 | ～$3.55 |

セルフホストのSageMakerモデル（FLUX、HunyuanImage、Qwen-Image）は、画像単位ではなく、あなた自身のインスタンスのGPU時間で課金されます（アイドル時はscale-to-zero） — コンピュートコストモデルについては[SPEC.md](SPEC.md#14-amazon-bedrock-pricing--cost-breakdown)を参照してください。

### 📝 12.5 後処理アドオン（画像あたり）

| アドオン | 画像あたり | 1画像 | 5画像 | 25画像 |
|--------|-----------|---------|----------|-----------|
| 背景除去 | $0.07 | $0.07 | $0.35 | $1.75 |
| Creative Upscale | $0.60 | $0.60 | $3.00 | $15.00 |
| SVGに変換 | $0.00 | $0.00 | $0.00 | $0.00 |

> [!TIP]
> **Creative Upscaleの注意**：JPEG出力フォーマットを内部的に使用し、その後PNGに変換し直すことで、Stability AIの16MBレスポンスペイロード制限を自動的に処理します。APIスロットリング用の指数バックオフによるリトライを含みます。

### 📝 12.6 具体例

| 例 | 構成 | 総コスト |
|---------|-------------|-----------|
| **最安** | 1×1、Stable Image Core、処理なし | ～$0.05 |
| **標準** | 1×5、Stable Diffusion 3.5 Large、背景除去 | ～$0.76 |
| **フル探索** | 5×5、Stable Diffusion 3.5 Large、背景除去＋SVG | ～$3.80 |
| **プレミアム** | 5×5、Stable Image Ultra、背景除去＋アップスケール＋SVG | ～$20.30 |

> [!TIP]
> **重要なポイント**：画像生成自体は安価です（$0.01〜$0.14/画像）。**$0.60/画像のCreative Upscaleが支配的なコスト**です — バッチ全体ではなく、最終的に選んだアセットに選択的に使用してください。$0.07/画像の背景除去は妥当です。SVG変換は無料です（ローカルで実行）。

<a id="disclaimer"></a>

## 📌 13. 免責事項

> [!IMPORTANT]
> **生成コンテンツの品質**：ArtSmokerによって生成されるすべての画像、動画、その他のアセットは、Amazon Bedrockを通じて利用可能なAIモデル（AWSファーストパーティモデルとサードパーティモデルの両方を含む）によって作成されます。生成コンテンツの品質、正確性、適切性は、ユーザーが提供するプロンプト、選択されたモデル、アップロードされたスタイルリファレンスに完全に依存します。ArtSmokerの作者と貢献者は、生成されたコンテンツの品質、適合性、または目的への適性について一切保証しません。
>
> **知的財産**：ユーザーは、プロンプト、リファレンス画像、生成された出力が、著作権、商標、肖像権を含むがこれに限定されない第三者の知的財産権を侵害しないことを確認する全責任を負います。ArtSmokerはツールであり、入力や出力のIPステータスをフィルタリング、検証、評価しません。ツールの作者と貢献者は、本ソフトウェアの使用から生じるいかなるIP侵害についても責任を負いません。
>
> **AIモデルとサービス条件**：生成コンテンツは、Amazon Bedrockを通じてアクセス可能な基盤AIモデルプロバイダーの利用規約と許容使用ポリシーの対象です。ユーザーは、本番環境や商用の文脈で生成アセットを使用する前に、[AWSサービス条件](https://aws.amazon.com/service-terms/)、[Amazon Bedrock SLA](https://aws.amazon.com/bedrock/sla/)、および個々のモデルプロバイダー条件を確認する必要があります。
>
> **モデルのライセンスと商用利用**：ArtSmokerを通じてデプロイされたセルフホストモデルは、その作成者のライセンス条件に準拠し、その条件は**あなた**を直接拘束します。ArtSmokerはデプロイ時に各モデルのライセンスと依存関係の内訳を表示してあなたの承諾を記録しますが、あなたの商用利用の権利を検証・強制・保証するものでは**ありません** — ライセンス条件（収益/ユーザー数のしきい値、地域制限、帰属表示の要件、使用量レポート）の範囲内にとどまることは、すべてあなた自身の責任です。[セクション1.9.3](#-193-using-a-model-commercially--who-to-pay-and-how)の商用ライセンスに関するガイダンスはあくまで参考情報であり、執筆時点のベンダー条件を反映したもので、**法的助言ではありません**。ライセンス条件は頻繁に変わります — 必ずベンダーの最新の条件を確認し、商用ローンチの前に法律の専門家に相談してください。ArtSmokerはいかなるモデルベンダーとも提携しておらず、いかなる対価も受け取っていません。
>
> **コストはあくまで見積もり — ご自身の支出を監視してください**：ArtSmokerに表示されるすべてのコスト（画像・動画・トークン単位、3D計算、デプロイ、セッション/アセット合計）は、AWSの公表価格と想定使用量から算出した**参考のための見積もりに過ぎません**。実際の請求額の**保証ではなく、請求書でもありません**。実際のコストは、AWSアカウントの価格、リージョン、割引、税金、データ転送、エンドポイントの稼働時間（アイドル/ウォームのSageMakerインスタンスを含む）、オートスケーリングの挙動、本ツール外の要因に依存します。**ご自身のAWS支出の監視と管理は、すべてユーザーの責任です** — [AWS請求コンソール](https://console.aws.amazon.com/billing/)、[AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/)、[予算/請求アラーム](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)で実際の料金を追跡・上限設定してください。特にセルフホスト型のSageMakerエンドポイントは、デプロイ中またはウォーム保持中はアイドルでも課金され続けます — 使用後は必ずteardownしてください。作者と貢献者は、本ソフトウェアの使用により発生したAWS料金について一切の責任を負いません。
>
> **無保証**：このソフトウェアは、いかなる種類の保証もなく「現状のまま」提供されます。完全な条件は[LICENSE](LICENSE)を参照してください。

## 📌 14. 完全な仕様書

完全な技術仕様については**[SPEC.md](SPEC.md)**を参照してください — アーキテクチャ、コンポーネント設計、モデル設定、APIリファレンス、セキュリティモデル、料金、デプロイメントロードマップ、およびプロジェクトをゼロから再構築するのに十分な詳細が含まれています。
