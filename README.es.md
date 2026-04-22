> Este documento es una traducción del README en inglés. Para la información más actualizada, consulte el [English README](README.md).

# ArtSmoker
> *¡Pruebas de humo para tu arte!*

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green?logo=fastapi&logoColor=white)
![Amazon Bedrock](https://img.shields.io/badge/Amazon-Bedrock-orange?logo=amazonaws&logoColor=white)
![License](https://img.shields.io/badge/License-MIT--0-yellow)

## 📌 0. Descripción general

Una interfaz sencilla y orientada al artista para los modelos de generación de imágenes y video de Amazon Bedrock. ArtSmoker ayuda a los equipos creativos a usar Bedrock de manera eficiente — sin necesidad de aprender la API, CLI o ingeniería de prompts.

### 📝 El problema

Los equipos creativos y estudios de videojuegos quieren utilizar IA para la generación de recursos, pero enfrentan barreras reales:

- **No hay una interfaz sencilla** — los artistas no deberían necesitar iniciar sesión en la consola de Bedrock ni escribir llamadas API para generar imágenes
- **La ingeniería de prompts es difícil** — componer prompts efectivos con los negativos adecuados, directivas de estilo y formato específico del modelo requiere experiencia que la mayoría de los artistas no tienen
- **Los equipos no construyen/entrenan sus propios modelos** — necesitan acceso a los muchos modelos ya disponibles en Bedrock, a través de algo que puedan usar de verdad
- **La edición de imágenes es inaccesible** — inpainting, outpainting, búsqueda y reemplazo, y transferencia de estilo requieren conocimiento de la API

### 📝 La solución

ArtSmoker es una aplicación web autoalojada que envuelve Amazon Bedrock en una interfaz creativa limpia. Construida específicamente para la producción de recursos de videojuegos, con aplicabilidad en otras industrias creativas como publicidad, comercio electrónico, publicaciones y medios digitales donde el contenido visual generado por IA aporta valor.

- **Los artistas solo describen lo que necesitan** en lenguaje natural — ArtSmoker se encarga de la composición del prompt, extracción de negativos, formato específico del modelo y aplicación de estilo detrás de escena
- **Generación consciente del estilo** — suba el arte existente de su juego y los modelos de visión de ArtSmoker aprenderán su identidad visual. Cada recurso generado coincidirá con la apariencia y estética de su juego
- **Todos los modelos de Bedrock, todas las regiones** — totalmente configurable. Elija sus modelos de texto a imagen, modelos de video y regiones. El sistema descubre los modelos disponibles dinámicamente a través de la API de Bedrock
- **Autodespliegue, autofacturación** — se ejecuta en su propia infraestructura, usa su propia cuenta de AWS. Sin endpoints compartidos, sin acceso de terceros a datos, sin facturas sorpresa de servicios externos

Construido sobre Amazon Bedrock: Claude Sonnet/Opus (ingeniería de prompts y chat), Nova Canvas, Titan Image, Stable Diffusion 3.5 Large, Stable Image Ultra, Stability AI (edición de imágenes), Nova Reel, Luma AI Ray (generación de video), más de 80 LLMs de 16 proveedores para Chat Studio.

**[Comience ahora — saltar a Requisitos previos e instalación ▸](#get-started)**

### Language / 言語 / 语言 / 언어 / Langue / Idioma

ArtSmoker está disponible en 6 idiomas. Cambie el idioma de la interfaz usando los botones de idioma en la barra de navegación superior (EN | JA | ZH | KO | FR | ES). Su selección se guarda automáticamente.

| Idioma | README |
|--------|--------|
| English | [README.md](README.md) |
| 日本語 (Japanese) | [README.ja.md](README.ja.md) |
| 中文 (Chinese) | [README.zh.md](README.zh.md) |
| 한국어 (Korean) | [README.ko.md](README.ko.md) |
| Français (French) | [README.fr.md](README.fr.md) |
| Español | Este documento |

**Soporte multilingüe para prompts:**
- Los prompts en idiomas distintos al inglés (japonés, chino, coreano, francés, español) se detectan automáticamente y se traducen al inglés antes de la generación
- Aparece una vista previa bilingüe en el área de prompts: alterne entre su texto original y la traducción al inglés para ver exactamente lo que recibirá el modelo
- El prompt original, el idioma detectado y la traducción al inglés se conservan en los metadatos del recurso
- Los nombres de archivo se generan a partir del prompt traducido al inglés (por ejemplo: "edificio del hospital" → `hospital-building_opt1_var1.png`)
- Chat Studio pasa los prompts directamente al LLM (sin traducción) — ya que modelos como Claude son nativamente multilingües
- El texto de Type Studio permanece en su idioma (se renderiza en la imagen tal cual)
- Todas las verificaciones previas de moderación y filtrado de contenido operan sobre el prompt traducido al inglés para mantener la consistencia

## 📌 1. Funcionalidades

ArtSmoker funciona en dos modos — **independiente** (sin necesidad de configurar estilo o tema artístico, solo describa y genere) y **guiado por estilo** (suba su arte existente y toda generación coincidirá con su identidad visual). Ambos modos usan los mismos estudios y pipeline de generación.

### 📝 Modo independiente (Inicio rápido)

Sin necesidad de configurar estilo o tema — abra el 2D Image Studio, Video Studio o Type Studio y comience a crear de inmediato.

1. **Describa lo que necesita** — escriba un prompt como "hospital building" o "fire mage character", o use entrada de voz. La IA mejora automáticamente su prompt con directivas de composición adecuadas, prompts negativos y formato específico del modelo.
2. **Elija sus modelos y configuración** — multi-selección de todos los modelos de texto a imagen disponibles (Bedrock + autoalojados), elija dimensiones, nivel de calidad y región. Marque varios modelos para comparación lado a lado, o uno para generación enfocada. La estimación de costos se actualiza en tiempo real.
3. **Obtenga múltiples opciones** — el sistema genera hasta 5 conceptos creativos claramente diferentes, cada uno con hasta 5 variaciones de semilla (25 imágenes en total). Elija el que más le guste.
4. **Edite y refine** — use inpainting, outpainting, borrado, búsqueda y reemplazo, o recoloración directamente en el Asset Viewer. Cada edición crea una nueva versión — el original siempre se conserva.
5. **Descargue archivos listos para el juego** — PNG con fondo transparente + SVG, con nombres descriptivos (ej. `hospital-building_opt2_var3.png`). Los videos se exportan como MP4.

### 📝 Modo guiado por estilo (Coincidir con su estilo artístico y tema)

Para equipos que desean que cada recurso generado coincida con un estilo artístico existente — suba imágenes de referencia y deje que la IA aprenda primero su identidad visual.

1. **Suba el arte de su juego** — importe imágenes de referencia desde directorios locales (escaneo recursivo, enlaces simbólicos para evitar duplicación) o buckets S3 (listado recursivo con paginación). La **deduplicación inteligente** se ejecuta automáticamente — elimina variantes de rotación (barrel_N/E/S/W.png conserva solo barrel_S.png) y cuadros de animación (Idle0-Idle8 conserva solo Idle). Por ejemplo, un paquete isométrico de 747 archivos se deduplica a ~99 objetos únicos. Formatos compatibles: .png, .jpg, .jpeg, .gif, .bmp, .webp, .tiff, .tif, .tga, .ico, .svg, más extracción automática de texturas desde modelos 3D (.glb, .gltf).
2. **La IA aprende su estilo** — análisis de cohesión en dos fases: primero, una verificación rápida determina si su colección es unificada, estructuralmente consistente o diversa. Luego, un análisis profundo del conjunto completo de referencia produce un perfil de estilo rico en metadatos — paletas de colores, grosores de línea, patrones de iluminación, reglas de composición y convenciones de producción. Si proporciona pistas de generación, la IA las recibe como "Orientación del artista" para que el análisis comprenda la intención, no solo lo visible.
3. **Genere con estilo aplicado** — cuando selecciona un estilo en el Image Studio, cada prompt se mejora automáticamente con las directivas visuales de su estilo. Un prompt como "hospital building" se convierte en una instrucción de generación detallada que incluye la paleta de colores de su juego, convenciones de perspectiva y estilo de renderizado.
4. **Todo lo del modo independiente aplica** — múltiples opciones, comparación de modelos, edición, versionado y descargas listas para el juego funcionan igual, ahora guiados por su estilo artístico.

> [!NOTE]
> Todo el contenido generado es producido por modelos de IA y depende de los prompts y referencias que usted proporcione. Consulte la [Exención de responsabilidad](#disclaimer) sobre calidad del contenido, propiedad intelectual y términos de servicio aplicables antes de usar recursos generados en producción.

### 📝 1.1 Resumen de funcionalidades

- 🎨 **Style Library** — Suba arte, la IA aprende su identidad visual
- 🖼️ **2D Image Studio** — Generación de imágenes con flujo guiado de 3 pasos
- 🎨 **Prompt Designer** — La IA descompone tu prompt en componentes visuales editables (sujeto, escena, iluminación, colores) con clasificación inteligente del tipo de asset
- 🎬 **Video Studio** — Texto a video con Nova Reel y Luma Ray, multi-toma, imagen a video
- ✍️ **Type Studio** — Superposiciones de texto diseñadas por IA con selector de fuentes
- 💬 **Chat Studio** — Chat LLM multimodelo con streaming, Markdown, resaltado de código, visión, sesiones, compactación de contexto
- 📁 **Galería unificada** — Explore imágenes + videos, filtro de medios, búsqueda, descarga, eliminación
- ✏️ **Edición de imágenes** — Inpainting, outpainting, borrado, búsqueda y reemplazo, recoloración (en AssetViewer)
- 🔄 **Progreso en tiempo real** — Streaming SSE con visibilidad de reintentos/throttle
- 🛡️ **Moderación inteligente** — Prueba canary, cambio automático de modelo, reescritura asistida por IA
- ⚙️ **Model Registry** — UI de administración organizada por estudio (Image, Video, Chat, Type, Shared), descubrimiento de Bedrock, soporte de modelos personalizados
- 📝 **Prompt Templates** — 19 prompts de directivas LLM editables, refinamiento asistido por IA, validación de variables con corrección automática
- 📦 **Versionado de recursos** — Edición in situ con historial de versiones (v1, v2, ...) y navegación entre versiones
- 💰 **Seguimiento de costos** — Gasto estimado de AWS por solicitud, por sesión, por recurso — enviado a telemetría PulseBoard
- 🌐 **i18n en 6 idiomas** — Traducción completa de la UI (EN, JA, ZH, KO, FR, ES), detección automática de prompts no ingleses, vista previa bilingüe
- 🔍 **Soporte de modelos personalizados** — Descubra automáticamente modelos Bedrock personalizados afinados, importados y desplegados
- 🔧 **Modelos autoalojados** — Despliegue modelos de código abierto (FLUX.2, FLUX.1, etc.) en Amazon SageMaker desde un catálogo extensible. Cuantización BnB NF4 en GPU, caché de modelo S3 para inicio rápido (~4 min), escalado automático a cero ($0 en reposo), cadena de respaldo resiliente (caché → recuantización → HuggingFace), generación asíncrona con panel de trabajos pendientes
- 🔄 **Auto-Update** — Git pull con control de version al inicio, reinicio automatico tras actualizacion, verificacion periodica cada 24h (`ARTSMOKER_AUTO_UPDATE=false` para desactivar)

### 📝 1.2 Capturas de pantalla

**2D Image Studio** — Configuración a la izquierda con desplegable de multi-selección de modelos, flujo de trabajo de prompt en 3 pasos a la derecha, resultados de comparación de modelos abajo. El modo multi-modelo genera con los modelos seleccionados simultáneamente con optimización de prompts por modelo.

![2D Image Studio — Configuración, prompt y resultados generados](docs/images/image-studio-top.png)

![2D Image Studio — Comparación de modelos, opciones de postprocesamiento y vista previa completa](docs/images/image-studio-bottom.png)

**Style Library** — Suba el arte existente de su juego, la IA analiza el estilo visual y produce una guía de prompts rica en metadatos. Las imágenes de referencia se muestran con el análisis completo de IA y perfil de estilo JSON.

![Style Library — Análisis de estilo por IA con imágenes de referencia](docs/images/style-library-top.png)

![Style Library — Imágenes de referencia, opciones de importación y datos de análisis](docs/images/style-library-bottom.png)

**Galería** — Vista unificada de todas las imágenes y videos generados con filtro de tipo de medio, filtro de estilo, búsqueda y ordenamiento. Haga clic en cualquier recurso para abrir el visor completo.

![Galería — Cuadrícula de recursos generados con filtros](docs/images/gallery.png)

**Asset Viewer y edición de imágenes** — Vista previa a tamaño completo con zoom/desplazamiento, pestaña de edición para inpainting (pintura de máscara + prompt), historial de versiones y descarga PNG/SVG.

![Asset Viewer — Edición de imágenes con inpainting](docs/images/asset-viewer-edit.png)

**Video Studio** — Configuración a la izquierda (modelo, modo de generación, duración, región, estimación de costos), prompt a la derecha. Compatible con Nova Reel (toma única, multi-toma automática/manual hasta 2 minutos) y Luma AI Ray (relaciones de aspecto, bucle).

![Video Studio — Configuración y prompt](docs/images/video-studio.png)

![Video Studio — Generación en progreso con prompt mejorado por IA](docs/images/video-studio-generating.png)

![Video Studio — Video completado con miniatura y videos recientes](docs/images/video-studio-completed.png)

**Reproductor de video** — Haga clic en un video para reproducirlo en línea con metadatos completos (prompt original, prompt mejorado por IA, modelo, duración, región).

![Reproductor de video — Reproducción de video generado con metadatos](docs/images/video-player.png)

### 📝 1.3 Generación de dos niveles

Para cada prompt, la IA crea **Opciones** — interpretaciones de diseño fundamentalmente diferentes (ej. para "warrior": berserker vikingo, samurái japonés, guerrero tribal, ciber-soldado, hoplita griego). Para cada opción, el modelo de imagen produce **Variaciones** — diferentes semillas aleatorias que proporcionan diferencias visuales sutiles. Esto ofrece a los artistas una amplia paleta creativa para elegir.

### 📝 1.4 Selección multi-modelo


El menú desplegable de modelos soporta **multi-selección basada en casillas de verificación** — elija cualquier combinación de modelos para una sola generación:

- **Modelo único** — marque un modelo para generación enfocada (más rápido, más económico)
- **Varios modelos** — marque 2-3 modelos específicos para comparación dirigida (ej: solo SD 3.5 + FLUX.2)
- **All Available Models** — el interruptor en la parte inferior selecciona/deselecciona todos los modelos habilitados para una comparación completa lado a lado

Cada modelo se ejecuta de forma independiente: si modelos más estrictos bloquean el prompt, aún obtiene resultados de los modelos que lo aceptaron. La estimación de costos se actualiza en tiempo real al marcar/desmarcar modelos.

El toggle opcional **"Model-optimized prompts"** adapta el prompt a las fortalezas de cada modelo — los prompts se reescriben por modelo (ej: impulsores de calidad para SD 3.5, lenguaje natural para FLUX.2, descripciones concisas para Nova Canvas).

### 📝 1.5 Video Studio

Genere videos y animaciones impulsados por IA a partir de prompts de texto. Compatible con **Amazon Nova Reel** (v1.0, v1.1) y **Luma AI Ray** (v2.0).

| Característica | Nova Reel | Luma Ray v2 |
|----------------|-----------|-------------|
| **Duración máxima** | 120s (2 minutos) | 9 segundos |
| **Resolución** | 1280x720 | 720p / 540p |
| **Relaciones de aspecto** | Solo 16:9 | 7 opciones (1:1, 16:9, 9:16, etc.) |
| **Imagen a video** | Sí (cuadro inicial) | Sí (cuadro inicial + final) |
| **Video en bucle** | No | Sí |
| **Control multi-toma** | Sí (automático + manual) | No |
| **Precio** | ~$0.08/seg | ~$1.50/seg |

**Cómo funciona:**
1. Seleccione un modelo de video y configure duración, relación de aspecto, región
2. Ingrese un prompt — la IA lo mejora con vocabulario cinematográfico, movimientos de cámara y señales de coherencia temporal
3. Haga clic en Generate — el trabajo se ejecuta de forma asíncrona mediante `StartAsyncInvoke`, la salida va a su bucket S3 configurado
4. Se consulta el estado cada 5 segundos — al completarse, se extrae la miniatura (vía ffmpeg) y el MP4 se descarga localmente (o se transmite desde S3)
5. Los videos aparecen tanto en la sección "Recent Videos" del Video Studio como en la Galería unificada

**Se requiere un bucket S3**: La generación de video produce su salida en S3. Puede configurarlo en Video Settings en la UI (explorar buckets existentes o crear uno nuevo), o crear uno vía CLI:

```bash
# Crear un bucket S3 para almacenamiento de video (reemplace REGION y YOUR_ORG)
aws s3api create-bucket --bucket artsmoker-video-YOUR_ORG --region us-east-1

# Para regiones distintas a us-east-1, agregue el LocationConstraint:
aws s3api create-bucket --bucket artsmoker-video-YOUR_ORG --region us-west-2 \
  --create-bucket-configuration LocationConstraint=us-west-2
```

Modo de almacenamiento: descarga local (predeterminado) o streaming desde S3 bajo demanda.

**Mejora de prompts de video**: El LLM agrega movimientos de cámara (paneo, zoom, dolly, seguimiento), detalles de iluminación y señales temporales. Como los modelos de video no soportan prompts negativos, los conceptos a evitar se integran naturalmente en el prompt positivo.

### 📝 1.6 Chat Studio

Una interfaz de chat LLM con funcionalidades completas — como una IA conversacional autoalojada, ejecutándose en su propia cuenta de AWS sin acceso de terceros a datos.

**Más de 80 modelos de 16 proveedores** — Claude (Sonnet, Opus, Haiku), Amazon Nova, Meta Llama, Mistral, Cohere, Qwen, DeepSeek, Google Gemma, NVIDIA Nemotron, y más. Además de cualquier modelo personalizado/importado en su cuenta. Todos descubiertos automáticamente vía Sync from AWS.

**Funcionalidades principales:**
- **Respuestas en streaming** — renderizado token por token en tiempo real vía Bedrock ConverseStream
- **Renderizado Markdown** — encabezados, negrita/cursiva, listas, tablas, citas, líneas horizontales
- **Bloques de código** — resaltado de sintaxis (highlight.js) con insignia de lenguaje + botón de copiar
- **Métricas por mensaje** — tokens de entrada/salida, latencia, costo estimado, modelo utilizado
- **Barra de ventana de contexto** — indicador visual de llenado (verde/ámbar/rojo) con conteo de tokens usados/máximo
- **Cambio de región** — cada modelo muestra todas las regiones disponibles, elija la más cercana o económica

**Gestión de sesiones:**
- Múltiples sesiones simultáneas con autoguardado
- Renombrar en línea, duplicar, eliminar, buscar/filtrar en la barra lateral
- Exportar conversaciones como Markdown
- Totales de sesión: conteo de tokens, costo estimado, conteo de mensajes

**Funcionalidades avanzadas:**
- **Plantillas de prompt de sistema** — General Assistant, Coding Expert, Creative Writer, Game Designer, Data Analyst, Technical Writer
- **Visión/multimodal** — arrastrar y soltar, selector de archivos o Ctrl+V para pegar imágenes con modelos compatibles con visión
- **Compactación de contexto** — la IA resume mensajes antiguos para liberar espacio en la ventana de contexto
- **Regenerar** — re-ejecutar cualquier respuesta de IA con el mismo prompt
- **Editar y reenviar** — modificar cualquier mensaje del usuario y reproducir desde ese punto
- **Bifurcar** — ramificar una conversación desde cualquier mensaje a una nueva sesión

**Transparencia de precios:** el selector de modelos muestra el costo por 1K tokens, la barra de información de precios muestra el costo estimado para conversaciones de 10K y 100K tokens.

### 📝 1.7 Conciencia del tipo de recurso

El **tipo de recurso** seleccionado cambia fundamentalmente cómo la IA interpreta su prompt — no solo el modelo de imagen, sino cada etapa del pipeline. Cuando escribe "hospital" y selecciona diferentes tipos de recurso, obtiene salidas completamente diferentes:

| Tipo | Composición | Encuadre | Enfoque técnico |
|------|-------------|----------|-----------------|
| **Game Asset** | Objeto único aislado sobre fondo transparente. Sin escena, sin texto, sin UI. | Frontal o isométrico, el objeto ocupa el 70-80% del cuadro. | Bordes limpios y definidos para eliminación de fondo, iluminación consistente desde la esquina superior izquierda, sin sombras en el suelo. Diseñado para componer con otros recursos de juego a varias escalas. |
| **Character** | Figura de cuerpo completo o 3/4, aislada sobre fondo limpio. Un solo personaje. | El personaje ocupa el 60-75% vertical, de la cabeza a los pies, ligeramente descentrado. | Silueta fuerte y legible (identificable solo por la silueta), pose expresiva que transmite personalidad, rasgos faciales claros y detalles de vestuario. |
| **Icon** | Símbolo único, audaz y reconocible, centrado con generoso relleno. Máxima simplicidad. | Frontal o ligera inclinación 3/4, espacio de respiro en los bordes. | Debe leerse claramente a 64x64 píxeles. Alto contraste, máximo 3-5 colores, formas audaces, sin líneas finas ni detalles pequeños. |
| **Marketing Banner** | Ilustración escénica completa con composición dramática. Zona limpia segura para texto reservada a un lado — sin texto renderizado ni tipografía. | Sensación cinematográfica amplia, cámara alejada para mostrar la escena. | Colores ricos y saturados, iluminación dramática (luz de borde, rayos volumétricos), profundidad de campo. La IA tiene instrucciones explícitas de NO renderizar texto; la zona segura para texto se mantiene limpia para superposición en postproducción con herramientas de diseño (Figma, Canva, etc.). |
| **Environment** | Paisaje completo con capas de profundidad primer plano/plano medio/fondo, líneas guía. | Plano general amplio, horizonte en el tercio superior o inferior. | Perspectiva atmosférica (objetos distantes más claros/difusos), narrativa ambiental a través de detalles, iluminación que establece el ambiente. |

Esto importa en cada etapa:

- **Botón "Preview Enhanced Prompt"** — Al hacer clic en Compose, la IA usa el tipo de recurso para reformular su descripción breve en un prompt de generación detallado, combinando sus palabras con las guías de estilo y directivas del tipo de recurso. Su intención explícita siempre tiene prioridad sobre los valores predeterminados del estilo. Puede revisar la versión compuesta antes de generar.
- **Generación de conceptos** — Al generar múltiples opciones, la IA crea N interpretaciones de diseño diferentes que respetan las reglas estructurales del tipo de recurso. Una opción de Character siempre tiene una silueta legible; una opción de Marketing Banner siempre tiene una zona segura para texto sin texto renderizado.
- **El resultado** — Dos imágenes del mismo prompt pero con diferentes tipos de recurso se verán completamente distintas. Un Game Asset "warrior" es un sprite de personaje único centrado. Un Marketing Banner "warrior" es una escena de batalla épica con una zona limpia para superposición de título.

<a id="get-started"></a>

## 📌 2. Requisitos previos

- **Python 3.11+** (3.12, 3.13, 3.14 también funcionan)
- **AWS CLI** configurado con credenciales válidas
- **Permisos IAM** para acceso a Bedrock (ver a continuación)

### 📝 2.1 Credenciales de AWS

ArtSmoker usa la [resolución estándar de credenciales de boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials), por lo que cualquiera de los siguientes métodos funciona:

| Método | Ideal para | Cómo |
|--------|-----------|------|
| **Variables de entorno** | CI/CD, contenedores | `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` |
| **Archivo de credenciales compartido** | Desarrollo local | `~/.aws/credentials` vía `aws configure` |
| **Perfil con nombre** | Múltiples cuentas | Establezca `ARTSMOKER_AWS_PROFILE=myprofile` o `AWS_PROFILE` |
| **AWS SSO** | SSO empresarial | `aws configure sso` |
| **IAM Instance Profile** | EC2, ECS, App Runner | Adjunte un rol IAM a la instancia — no se necesitan credenciales en la máquina |
| **ECS Task Role** | Contenedores ECS/Fargate | Asigne un rol de ejecución de tarea con los permisos requeridos |

Verificación rápida de que las credenciales funcionan:

```bash
aws sts get-caller-identity
```

> [!NOTE]
> En EC2 y otros servicios de cómputo de AWS, no necesita configurar credenciales explícitas. Adjunte un [IAM Instance Profile](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2_instance-profiles.html) con los permisos requeridos, y boto3 lo detectará automáticamente a través del servicio de metadatos de la instancia.

Para permisos IAM detallados, instrucciones de instalación, opciones de configuración e información de precios, consulte las secciones 2.1.1–2.4, secciones 3–4 y secciones 11–12 del [README en inglés](README.md).

## 📌 5. Arquitectura

```
┌─────────────────────────────────────────────┐
│  Navegador (SPA)                            │
│  Vanilla JS + Tailwind CSS                  │
└──────────────────────┬──────────────────────┘
                       │ HTTP / SSE
                       ▼
┌─────────────────────────────────────────────┐
│  Backend FastAPI (Python)                   │
│                                             │
│  /api/styles      CRUD de estilos + import  │
│  /api/generate    Generación de dos niveles │
│  /api/type-studio Superposición + fuentes   │
│  /api/video       Generación video + tareas │
│  /api/chat        Chat LLM + sesiones       │
│  /api/gallery     Exploración + exportación │
│  /api/browse      Explorador archivo/S3     │
│  /api/admin       Registro modelos + plant. │
│  /api/refine-prompt Prompt + traducción     │
│  /api/transcribe  Voz a texto              │
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
└──────────────────────┘  └──────────────────────────┘ ... (otras regiones)
             │
             ▼
┌──────────────────────┐
│  Almacenamiento local │
│  data/styles/         │
│  data/generated/      │
│  data/video/          │
│  data/chat/           │
└──────────────────────┘
```

## 📌 7. Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | FastAPI (Python 3.11+), boto3, Pydantic |
| Frontend | Vanilla JS, Tailwind CSS (CDN) |
| IA (LLM) | Claude Sonnet 4.6 (tareas rápidas), Claude Opus 4.6 (tareas complejas) |
| IA (Imagen) | Nova Canvas, Titan Image v2, Stable Diffusion 3.5 Large, Stable Image Ultra |
| IA (Postprocesamiento) | Stability AI (Remove Background, Creative Upscale) |
| IA (Chat) | Más de 80 LLMs de 16 proveedores vía Bedrock ConverseStream |
| IA (Video) | Nova Reel v1.0/v1.1 (hasta 2 min), Luma AI Ray v2 (hasta 9 seg) |
| IA (Voz) | Nova Sonic (voz a texto vía streaming bidireccional) |
| i18n | Función personalizada t(), 817 claves × 6 idiomas, traducción DOM por búsqueda inversa |
| Conversión SVG | vtracer (principal), potrace (respaldo), Pillow (último recurso) |
| Renderizado de texto | Pillow (sombra, contorno, efectos de brillo) |
| Almacenamiento | Sistema de archivos local (interfaz compatible con S3) |
| Desarrollo | Middleware sin caché para archivos estáticos, registro de errores del lado del cliente vía `POST /api/log` |

No se requiere paso de compilación para el frontend.

## 📌 8. Modelo de seguridad

ArtSmoker está diseñado como una **herramienta de desarrollo para red local/confiable** — se ejecuta en la máquina del desarrollador o en una instancia EC2 privada.

- **Sin autenticación** — todos los endpoints de la API están abiertos. Apropiado para desarrollo local y despliegues de equipo privados.
- **Explorador de sistema de archivos** — el endpoint `GET /api/browse/local` permite explorar cualquier directorio al que el proceso del servidor pueda acceder. Esto es intencional para importar arte de referencia.
- **Acceso a S3** — la exploración e importación de S3 usan las credenciales de AWS del servidor.

> [!WARNING]
> No exponga ArtSmoker a redes no confiables sin agregar autenticación y restricciones de ruta. Consulte la [Hoja de ruta de despliegue en SPEC.md](SPEC.md#14-deployment--scaling-roadmap) para orientación sobre fortalecimiento en producción.

## 📌 12. Precios de Amazon Bedrock y desglose de costos

> [!NOTE]
> Las tablas a continuación son **precios de referencia para planificación**. La propia aplicación muestra **precios en vivo por modelo** en la barra lateral del Image Studio — obtenidos de la API de precios de AWS durante la actualización del registro y almacenados en `model_registry.json`.

Todos los precios provienen de la [página de precios de Amazon Bedrock](https://aws.amazon.com/bedrock/pricing/) (regiones de EE.UU.). Para más detalles consulte [SPEC.md](SPEC.md#13-aws-bedrock-pricing--cost-breakdown).

| Servicio | Modelo | Costo | Unidad |
|----------|--------|-------|--------|
| **Claude Sonnet 4.6** | `us.anthropic.claude-sonnet-4-6` | $3.00 entrada / $15.00 salida | por 1M de tokens |
| **Claude Opus 4.6** | `us.anthropic.claude-opus-4-6-v1` | $5.00 entrada / $25.00 salida | por 1M de tokens |
| **Nova Canvas** | `amazon.nova-canvas-v1:0` | $0.06 | por imagen |
| **Titan Image v2** | `amazon.titan-image-generator-v2:0` | $0.01 | por imagen |
| **Stable Diffusion 3.5 Large** | `stability.sd3-5-large-v1:0` | $0.08 | por imagen |
| **Stable Image Ultra** | `stability.stable-image-ultra-v1:1` | $0.14 | por imagen |
| **Remove Background** | Stability AI | $0.07 | por imagen |
| **Creative Upscale** | Stability AI | $0.60 | por imagen |
| **Conversión SVG** | Local (vtracer/potrace) | $0.00 | gratis |

> [!TIP]
> **Punto clave**: La generación de imágenes en sí es económica ($0.01–$0.14/imagen). **Creative Upscale a $0.60/imagen es el mayor factor de costo** — úselo selectivamente en los recursos finales elegidos, no en el lote completo. Remove Background a $0.07/imagen es razonable. La conversión SVG es gratuita (se ejecuta localmente).

<a id="disclaimer"></a>

## 📌 13. Exención de responsabilidad

> [!IMPORTANT]
> **Calidad del contenido generado**: Todas las imágenes, videos y otros recursos generados por ArtSmoker son producidos por modelos de IA disponibles a través de Amazon Bedrock. La calidad, precisión y adecuación del contenido generado dependen completamente de los prompts proporcionados por el usuario, los modelos seleccionados y las referencias de estilo subidas. Los autores y contribuidores de ArtSmoker no ofrecen garantías sobre la calidad, idoneidad o aptitud para un propósito de cualquier contenido generado.
>
> **Propiedad intelectual**: Los usuarios son los únicos responsables de asegurar que sus prompts, imágenes de referencia y salidas generadas no infrinjan derechos de propiedad intelectual de terceros, incluyendo pero no limitado a derechos de autor, marcas registradas y derechos de imagen. ArtSmoker es una herramienta — no filtra, valida ni evalúa el estado de PI de las entradas o salidas.
>
> **Modelos de IA y términos de servicio**: El contenido generado está sujeto a los términos de servicio y políticas de uso aceptable de los proveedores de modelos de IA subyacentes accesibles a través de Amazon Bedrock.
>
> **Sin garantía**: Este software se proporciona "tal cual" sin garantía de ningún tipo. Consulte [LICENSE](LICENSE) para los términos completos.

## 📌 14. Especificación completa

Consulte **[SPEC.md](SPEC.md)** para la especificación técnica completa — arquitectura, diseño de componentes, configuración de modelos, referencia de API, modelo de seguridad, precios, hoja de ruta de despliegue y suficiente detalle para reconstruir el proyecto desde cero.
