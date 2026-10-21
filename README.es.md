# ArtSmoker
> *¡Pruebas de humo para tu arte!*

![Python](https://img.shields.io/badge/Python-3.12--3.14-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green?logo=fastapi&logoColor=white)
![Amazon Bedrock](https://img.shields.io/badge/Amazon-Bedrock-orange?logo=amazonaws&logoColor=white)
![License](https://img.shields.io/badge/License-MIT--0-yellow)

![Recorrido por ArtSmoker — del prompt de texto al arte 2D listo para producción y al modelo 3D totalmente texturizado y adaptado al motor de juego](docs/images/artsmoker-walkthrough.gif)

<a id="quick-start"></a>

## 🚀 Inicio rápido

**De un clon recién hecho a su primer asset generado en pocos minutos — en macOS, Linux o Windows.**

**Necesita:** Python **3.12, 3.13 o 3.14** · Git · credenciales de AWS (`aws configure`, AWS SSO o un rol de instancia) con acceso a Amazon Bedrock. La forma más rápida de configurar los permisos son las políticas administradas `AmazonBedrockFullAccess` + `AmazonBedrockMantleInferenceAccess` — [detalles](#iam-permissions).

> [!TIP]
> 🤖 **¿Prefiere que lo hagan por usted?** Abra este repositorio en **[Kiro](https://kiro.dev)**, el entorno de desarrollo agéntico de AWS, y pídale: *«Configura y ejecuta ArtSmoker siguiendo la sección Inicio rápido de README.es.md.»* El agente de Kiro ejecuta los comandos por usted.

**macOS · Linux**

```bash
git clone https://github.com/niravdd/ArtSmoker.git && cd ArtSmoker
python3 --version                                   # debe ser 3.12, 3.13 o 3.14 (si no, use p. ej. python3.14 más abajo)
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
python -m backend.main
```

**Windows (PowerShell)**

```powershell
git clone https://github.com/niravdd/ArtSmoker.git; cd ArtSmoker
python --version                                    # debe ser 3.12, 3.13 o 3.14 (si no, use p. ej. py -3.14 más abajo)
python -m venv .venv; .venv\Scripts\activate
pip install -r backend\requirements.txt
python -m backend.main
```

Después abra **http://localhost:8000**. En el primer arranque, ArtSmoker comprueba sus credenciales de AWS y realiza un análisis único de los modelos que su cuenta puede usar en todas las regiones de AWS (normalmente unos minutos) — una pantalla **Configurando ArtSmoker** muestra el progreso — y ya está listo para generar.

| ¿Atascado? | Vaya a |
|---|---|
| Su `python3` no es 3.12–3.14 (p. ej., el `python3` del sistema de Amazon Linux 2023 es 3.9; un `python3` de Homebrew recién instalado puede ser 3.15, que una dependencia aún no admite) | [3. Instalación](#installation) |
| PowerShell no permite ejecutar `.venv\Scripts\activate` | [3.3 Windows](#install-windows) |
| Errores de credenciales de AWS, de permisos o del primer uso de Claude | [2. Requisitos previos](#get-started) · [2.2 Permisos IAM](#iam-permissions) |
| Varios usuarios, una máquina EC2 o producción | [4. Ejecución](#running) |

## 📌 0. Descripción general

**ArtSmoker convierte una idea en arte adaptado al motor de juego — en minutos y sin ningún pipeline que usted deba gestionar.** Describa un personaje, un accesorio, un entorno o una pieza de key art en lenguaje sencillo y obtenga arte 2D listo para producción, modelos 3D completamente texturizados y video — todo en consonancia con la identidad visual de su proyecto, todo dentro de su propio entorno. Los modelos de IA más recientes de imagen, edición, 3D y video se sitúan tras una interfaz única, limpia y orientada al artista, con controles creativos reales: ArtSmoker ejecuta todo el pipeline de producción por usted, para que su equipo dirija la apariencia en lugar de lidiar con la maquinaria.

### 📝 El problema

Los equipos creativos de los estudios de videojuegos y medios quieren aprovechar la ventaja de la IA generativa — pero hoy ese poder está encerrado tras herramientas de desarrollo que nunca estuvieron pensadas para que ellos las gestionaran:

- **Está hecho para ingenieros, no para artistas** — los mejores modelos viven tras consolas en la nube, líneas de comandos, SDKs y API REST. Ningún director ni artista conceptual debería necesitar una terminal para crear una pieza de arte.
- **Ideas claras, prompts crípticos** — los artistas saben exactamente lo que quieren, pero los modelos no aceptan instrucciones en lenguaje creativo sencillo; los resultados consistentes y fieles al brief siguen dependiendo de la estructura del prompt, los prompts negativos y la fraseología específica de cada modelo que se interponen entre el brief y el resultado.
- **Los mejores modelos de IA están dispersos y son difíciles de ejecutar** — potentes modelos de IA para imagen, edición, 3D y video se publican constantemente en distintos proveedores y formatos; poner en marcha cada uno (empaquetado, GPUs, cuantización, escalado) es, por sí solo, todo un proyecto de ingeniería.
- **La edición y el 3D son mundos aparte** — inpainting, outpainting, recoloreado, ediciones guiadas por referencia y convertir un concepto 2D en un modelo 3D texturizado normalmente requieren, cada uno, sus propias herramientas, API y especialistas.
- **Mantener la coherencia de marca es manual** — mantener cada recurso fiel a su apariencia establecida suele implicar supervisar cada generación a mano.

### 📝 La solución

ArtSmoker es un estudio creativo autoalojado que pone los mejores modelos generativos de hoy tras una única interfaz orientada al artista — creado específicamente para la producción de recursos de videojuegos, e igual de cómodo en cine, publicidad, comercio electrónico, edición y cualquier equipo que viva del contenido visual original.

- **Descríbalo en lenguaje sencillo** — ArtSmoker se encarga de la descomposición del prompt, la mejora y la optimización específica de cada modelo entre bastidores. Un **Diseñador de prompts** guiado le permite dar forma a cada elemento visual — sujeto, escena, iluminación, color — con controles de bloquear/variar para explorar direcciones genuinamente distintas sin perder lo que ya funciona.
- **Fiel a su marca por defecto** — alimente a ArtSmoker con su arte existente y sus modelos de visión aprenden su identidad visual, de modo que cada recurso sale coincidiendo con la apariencia y estética de su proyecto.
- **2D, editado y en 3D — de extremo a extremo** — genere y luego refine in situ con inpainting, outpainting, recoloreado, búsqueda y reemplazo, y ediciones guiadas por referencia; convierta cualquier recurso 2D en un **modelo 3D completamente texturizado y adaptado al motor de juego** que se integra directamente en Unity, Unreal o Blender — sin modelado manual, desenvolvimiento UV ni pintado de texturas. Además, video cinematográfico y un estudio de chat multimodelo para la ideación.
- **Cada modelo, un clic** — use los últimos modelos alojados en todas las regiones, o despliegue modelos de código abierto curados (p. ej., Qwen-Image, FLUX.2, HunyuanImage, TripoSG, TRELLIS.2) en sus propias GPUs con un solo clic — empaquetado, cuantización, escalado automático y seguimiento de trabajos, todo gestionado, cada modelo validado de extremo a extremo antes de su publicación.
- **Se ejecuta donde usted quiera — y su IP sigue siendo suya** — instálelo en el escritorio de un solo artista o en una instancia compartida para todo el equipo; **sin necesidad de una GPU propia** (el cómputo pesado se ejecuta en servicios gestionados de AWS, o en endpoints con escalado automático que ArtSmoker pone en marcha y reduce de nuevo a cero por usted). Se conecta únicamente a su propia cuenta de AWS — obras, prompts, estilos y recursos generados permanecen en su entorno, nada va hacia servicios de terceros, y usted conserva la propiedad total de su IP creativa.

**Modelos de Amazon Bedrock** — los que **Sincronizar desde AWS** encuentre en su cuenta, p. ej., Claude Sonnet/Opus para ingeniería de prompts y chat, Stable Diffusion 3.5 Large, Stable Image Ultra y Stable Image Core para imágenes, servicios de Stability AI para edición de imágenes, Luma AI Ray para video y una amplia gama de LLMs de chat de numerosos proveedores para el Estudio de Chat. **Modelos autoalojados** — un catálogo curado que se incluye con cada versión y se despliega en Amazon SageMaker, p. ej., Qwen-Image (texto a imagen) y Qwen-Image-Edit (edición guiada por referencia + por instrucciones, Apache-2.0), HunyuanImage 3.0 (BF16/NF4), FLUX.2, FLUX.1, TripoSG y TRELLIS.2 (imagen a 3D) — y es extensible, así que puede agregar los suyos.

<a id="about-model-names"></a>
> [!NOTE]
> **Sobre los nombres de modelos.** ArtSmoker ofrece los modelos que **Sincronizar desde AWS** encuentre en su cuenta y sus Regiones, además del catálogo autoalojado que se incluye con cada versión. Los nombres de modelos de este README son **ejemplos a octubre de 2026** — AWS lanza y retira modelos con frecuencia, y lo que puede usar depende de su cuenta, sus Regiones y su acceso a modelos. La aplicación es la fuente de la verdad sobre lo que está disponible hoy.

**[Comience ahora — salte a Requisitos previos e instalación ▸](#get-started)**

### Language / 言語 / 语言 / 언어 / हिन्दी / Язык / Langue / Idioma

ArtSmoker admite 9 idiomas. Cambie el idioma de la interfaz con los botones de idioma de la barra de navegación superior (EN | 日 | 中 | 한 | हिं | РУ | FR | ES | DE). Su selección se guarda automáticamente.

| Idioma | README |
|--------|--------|
| English | [README.md](README.md) |
| 日本語 (Japanese) | [README.ja.md](README.ja.md) |
| 中文 (Chinese) | [README.zh.md](README.zh.md) |
| 한국어 (Korean) | [README.ko.md](README.ko.md) |
| हिन्दी (Hindi) | [README.hi.md](README.hi.md) |
| Русский (Russian) | [README.ru.md](README.ru.md) |
| Français (French) | [README.fr.md](README.fr.md) |
| Español (Spanish) | Este documento |
| Deutsch (German) | [README.de.md](README.de.md) |

**Soporte multilingüe para prompts:**
- Los prompts en idiomas distintos del inglés se detectan automáticamente (japonés, chino, coreano, hindi, ruso, francés, español y más) y se traducen al inglés antes de la generación
- Aparece una vista previa bilingüe en el área del prompt: alterne entre su texto original y la traducción al inglés para ver exactamente lo que recibirá el modelo
- El prompt original, el idioma detectado y la traducción al inglés se conservan todos en los metadatos del recurso
- Los nombres de archivo se generan a partir del prompt traducido al inglés (de modo que "病院の建物" → `hospital-building_opt1_var1.png`)
- El Estudio de Chat pasa los prompts directamente al LLM (sin traducción), ya que modelos como Claude son nativamente multilingües
- El texto del Estudio de Texto permanece en su idioma (se renderiza en la imagen tal cual)
- Todas las verificaciones previas de moderación y el filtrado de contenido operan sobre el prompt traducido al inglés para mantener la consistencia

## 📌 1. Qué hace

ArtSmoker funciona en dos modos — **independiente** (sin necesidad de configurar estilo ni tema artístico, solo describa y genere) y **guiado por estilo** (suba su arte existente y toda generación coincidirá con su identidad visual). Ambos modos usan los mismos estudios y el mismo pipeline de generación.

### 📝 Modo independiente (Inicio rápido)

Sin necesidad de configurar estilo ni tema — abra el Estudio de Imagen, el Estudio de Video o el Estudio de Texto y comience a crear de inmediato.

1. **Describa lo que necesita** — escriba un prompt como "edificio de hospital" o "personaje mago de fuego", o use la entrada de voz. La IA descompone su idea en componentes visuales, la mejora con optimizaciones específicas del modelo y respeta su intención creativa mediante controles inteligentes de bloquear/variar. Escriba en cualquier idioma — los prompts no ingleses se traducen automáticamente.
2. **Elija sus modelos y configuración** — multiselección entre todos los modelos de texto a imagen disponibles (Amazon Bedrock + autoalojados en SageMaker), elija dimensiones, nivel de calidad y región. Marque varios modelos para una comparación lado a lado, o seleccione uno para una generación enfocada. La estimación de costos se actualiza en tiempo real.
3. **Obtenga opciones genuinamente diferentes** — el sistema genera hasta 5 conceptos creativos claramente distintos (variando vestimenta, estado de ánimo, iluminación, composición — no solo el ángulo de cámara), cada uno con hasta 5 variaciones de semilla (25 imágenes en total). Los detalles especificados por el usuario se bloquean; los detalles inferidos por la IA se varían con audacia. Un control de **Semilla (seed)** visible hace los lotes reproducibles — la misma semilla, con el mismo prompt final y ajustes, regenera las mismas imágenes, y hacer clic en cualquier resultado fija su semilla para cambiar solo una cosa y ramificar desde un favorito.
4. **Edite y refine** — use inpainting, outpainting, borrado, búsqueda y reemplazo, o recoloración directamente en el visor de recursos. Cada edición crea una nueva versión — el original siempre se conserva.
5. **Descargue archivos listos para el juego** — PNG con fondo transparente + SVG, con nombres descriptivos (p. ej. `hospital-building_opt2_var3.png`). Los videos se exportan como MP4.

### 📝 Modo guiado por estilo (Coincidir con su estilo artístico y tema)

Para equipos que desean que cada recurso generado coincida con un estilo artístico existente — suba imágenes de referencia y deje que la IA aprenda primero su identidad visual.

1. **Suba el arte de su juego** — importe imágenes de referencia desde directorios locales (escaneo recursivo, con enlaces simbólicos para evitar duplicación) o buckets de S3 (listado recursivo con paginación). La **deduplicación inteligente** se ejecuta automáticamente — elimina variantes de rotación (barrel_N/E/S/W.png conserva solo barrel_S.png) y cuadros de animación (Idle0-Idle8 conserva solo Idle). Por ejemplo, un paquete de recursos isométricos de 747 archivos se deduplica a ~99 objetos únicos. Formatos compatibles: .png, .jpg, .jpeg, .gif, .bmp, .webp, .tiff, .tif, .tga, .ico, .svg, además de la extracción automática de texturas de modelos 3D (.glb, .gltf).
2. **La IA aprende su estilo** — análisis de cohesión en dos fases: primero, una verificación rápida determina si su colección es unificada, estructuralmente consistente o diversa. Luego, un análisis profundo del conjunto completo de referencias produce un perfil de estilo rico en metadatos — paletas de colores, grosores de línea, patrones de iluminación, reglas de composición y convenciones de producción. Si proporciona pistas de generación, la IA las recibe como "Orientación del artista" para que el análisis comprenda su intención, no solo lo que es visible.
3. **Genere con el estilo aplicado** — cuando selecciona un estilo en el Estudio de Imagen, cada prompt se mejora automáticamente con las directivas visuales de su estilo. Un prompt como "edificio de hospital" se convierte en una instrucción de generación detallada que incluye la paleta de colores de su juego, las convenciones de perspectiva y el estilo de renderizado.
4. **Todo lo del modo independiente aplica** — múltiples opciones, comparación de modelos, edición, versionado y descargas listas para el juego funcionan de la misma manera, ahora guiados por su estilo artístico.

> [!NOTE]
> Todo el contenido generado lo producen modelos de IA y depende de los prompts y las referencias que usted proporcione. Consulte la [Exención de responsabilidad](#disclaimer) sobre calidad del contenido, propiedad intelectual y términos de servicio aplicables antes de usar recursos generados en producción.

### 📝 1.1 Resumen de funcionalidades

- 🎨 **Biblioteca de Estilos** — Suba arte, la IA aprende su identidad visual
- 🖼️ **Estudio de Imagen** — Genere imágenes con opciones × variaciones, flujo guiado de prompt en 3 pasos
- 🎨 **Diseñador de prompts** — La IA descompone su prompt en componentes visuales editables (sujeto, escena, iluminación, colores) con interruptores de bloquear/variar por campo, integración de estilo y clasificación inteligente del tipo de recurso. Imagen fotorrealista, Personaje, Entorno y más
- 🗂️ **Colecciones (generación de conjuntos)** — convierte UN prompt **o una imagen de referencia** en un **conjunto coherente de recursos distintos** («un juego de ajedrez de estilo vikingo», «20 personajes JRPG»). Activa el interruptor **Colección** en el Estudio de Imagen — desde la pestaña **Inspiración de texto** (lo impulsa tu prompt) o la pestaña **Inspiración de imagen** (el *aspecto* de la imagen de referencia impulsa la dirección de arte) — y un **Diseñador de colección** dedicado descompone tu brief en una **dirección de arte** compartida más una **lista** de sujetos distintos en la temática — cada uno es un **lote** con su propio prompt editable e independiente del modelo. Edita la dirección de arte para recomponer todo el conjunto; bloquea, regenera, añade o elimina lotes individuales; luego genéralos todos de una vez (opciones × variaciones cada uno), con una estimación en vivo del diseño y el coste proyectado. **Elige un solo modelo para un conjunto homogéneo, o varios para renderizar cada lote en cada uno** (comparación entre modelos). La cohesión opcional **Anclaje al héroe** / **Anclaje a la referencia** fija el estilo del conjunto a una imagen elegida/proporcionada. Las colecciones aparecen como **una sola tarjeta** en la Galería; el visor de colección permite que cada lote abra el visor de recursos normal (opciones / variaciones / versiones, ediciones, exportaciones y 3D — exactamente como con una imagen suelta, más el **linaje de colección** del lote); puedes **fijar la versión** que representa cada lote, **pasar todo el conjunto a 3D** de una vez (o solo los lotes o imágenes que elijas) y ver llegar cada modelo a la vista **Modelos 3D** propia de la colección, **descargar** todo el conjunto o una selección en un solo zip — los mismos archivos que ofrece una imagen suelta (PNG, SVG y recortes sin fondo) o sus modelos 3D con los mismos presets de motor, LOD, colisiones y empaquetado de texturas — o **recargar toda la colección en el Estudio de Imagen** para revisarla y regenerarla. Los modelos 3D de una colección se quedan dentro de ella: el **filtro 3D** de la Galería muestra la tarjeta de la colección con su insignia «3D n/m». Una colección cargada se muestra **directamente en el área de resultados del Estudio de Imagen** (las mismas tarjetas, vista previa y panel de prompt que una imagen suelta, agrupadas por lote), y al reabrir el Diseñador de colección se ve **el diseño guardado tal cual** (dirección de arte, el prompt de cada lote y los prompts que recibió cada modelo), sin regenerar nada salvo que lo pidas y, **antes de gastar nada**, se comprueba el tipo de recurso frente a tu prompt (un conjunto = Personajes o Recursos de juego), para que nunca pagues un conjunto entero con el encuadre equivocado
- 🎬 **Estudio de Video** — Texto a video con orientación de prompt específica del modelo (p. ej., dirección en lenguaje natural para Luma Ray), imagen a video, bucle
- ✍️ **Estudio de Texto** — Superposiciones de texto diseñadas por IA con selector de fuentes
- 💬 **Estudio de Chat** — Chat LLM multimodelo con streaming, markdown, resaltado de código, visión, sesiones y compactación de contexto
- 📁 **Galería unificada** — Diseño en mosaico (masonry) que muestra cada recurso en su proporción real (vertical, cuadrada, horizontal — nunca recortada). Explore imágenes + videos, filtro de medios (Todos / Arte 2D / Modelos 3D / Video), búsqueda, marcas completas de fecha-hora-zona horaria, descarga, eliminación. Los recursos que ya tienen un modelo 3D generado llevan una **insignia 3D**, y el filtro **Modelos 3D** muestra únicamente esos
- 📥 **Importar imagen** — Lleve una imagen existente (cualquier formato) a la galería como un recurso de primera clase. Se convierte automáticamente a PNG, se etiqueta con un tipo de recurso que usted elija y queda inmediatamente editable y lista para 3D — todo (versionado, edición, imagen a 3D) funciona exactamente igual que con una imagen generada
- ✏️ **Edición de imágenes** — Inpainting, outpainting, borrado, búsqueda y reemplazo, recoloración (en el visor de recursos). Cada modo tiene un botón de IA **Generar prompt**: un modelo de visión lee la imagen + su prompt original y propone un prompt de edición adaptado a ese modo y al modelo de edición seleccionado (p. ej., una descripción para los editores de Stability, una instrucción para Qwen-Image-Edit). Outpaint muestra una vista previa en vivo del marco que crece, con reglas de píxeles, para que vea exactamente cuánto se expandirá el lienzo antes de confirmar. Los editores por instrucciones (p. ej., Qwen-Image-Edit) admiten **los cinco modos sin máscara** — incluida la extensión real del lienzo: ArtSmoker rellena previamente el lienzo, hace que el modelo complete solo la zona nueva y vuelve a fusionar sus píxeles originales intactos. Cada versión editada muestra **ambas etiquetas de modelo** — el generador original y el editor que creó esa versión
- 📤 **Exportar y recortes** — Artefactos de exportación por versión en el visor de recursos: un recorte PNG transparente sin fondo más trazados SVG vectoriales reales (con y sin fondo). La eliminación de fondo se elige en cada ejecución: **gratuita en el dispositivo** (rembg/u2net, sin coste de nube) o el eliminador **de pago de Amazon Bedrock** — la misma elección se ofrece al preparar imágenes para la generación 3D
- 🔄 **Progreso en tiempo real** — Streaming SSE con visibilidad de reintentos y limitaciones de velocidad
- 🛡️ **Moderación inteligente** — Prueba canario, cambio automático de modelo, reescritura asistida por IA
- ⚙️ **Registro de modelos** — UI de administración organizada por estudio (Estudio de Imagen, Estudio de Video, Estudio de Chat, Estudio de Texto, Estudio Compartido), descubrimiento de Bedrock, soporte de modelos personalizados
- 📝 **Plantillas de Prompt** — 28 prompts de directivas LLM editables, refinamiento asistido por IA, validación de variables con corrección automática
- 📦 **Versionado de recursos** — Edición in situ con historial de versiones (v1, v2, ...), navegación entre versiones y borrado por versión: elimine solo una versión (las demás conservan sus números), con el visor cambiando a la versión anterior — borrar la última versión elimina todo el recurso
- 💰 **Seguimiento de costos** — Gasto estimado de AWS por solicitud, por sesión, por recurso, calculado a partir de precios de AWS en vivo por región; los modelos autoalojados muestran la tarifa horaria de ejecución de la instancia GPU + el tiempo típico de generación (no un engañoso precio por imagen)
- 🌐 **i18n en 9 idiomas** — Traducción completa de la UI (EN, JA, ZH, KO, HI, RU, FR, ES, DE), detección automática de prompts no ingleses (la UI en inglés omite la detección por completo), vista previa bilingüe
- 🔍 **Soporte de modelos personalizados** — Descubra automáticamente modelos Bedrock personalizados afinados, importados y desplegados
- 🔧 **Modelos autoalojados — Despliegue en 1 clic** — Explore un catálogo curado de modelos de código abierto preprobados (en esta versión, p. ej., Qwen-Image, Qwen-Image-Edit, HunyuanImage 3.0, FLUX.2, FLUX.1, TripoSG, TRELLIS.2), elija una instancia de GPU y haga clic en Desplegar. ArtSmoker gestiona todo: el empaquetado del manejador de inferencia, la configuración de la cuantización, la selección del kit de herramientas de CUDA correcto, la configuración del escalado automático, el registro de alarmas de CloudWatch y la conexión del seguimiento asíncrono de trabajos. Cada modelo del catálogo se ha validado de extremo a extremo — desde el arranque en frío pasando por la generación hasta la entrega a la galería — para que no tenga que depurar controladores de GPU, desbordamientos de memoria ni compatibilidad de contenedores. Soporta BF16 + FlashInfer para la mejor calidad, NF4 para eficiencia de costos, detección automática multi-GPU, escala a cero automáticamente ($0 en reposo) y el mismo modelo funciona en distintos tipos de instancia sin reconfiguración
- 🧊 **Generación de imagen a 3D** — Convierta cualquier imagen de Recurso de juego o Personaje en una malla 3D texturizada (GLB) con un clic. La síntesis multivista + el horneado de texturas producen recursos adaptados al motor de juego. Visor 3D interactivo con órbita/zoom/panorámica
- 🩹 **Completado inteligente del origen para 3D** — la conversión a 3D solo puede construir lo que es visible, así que un personaje recortado (piernas cortadas) se convierte en una malla sin piernas. Antes de generar, ArtSmoker revisa con visión la imagen de origen y, si está recortada, **ofrece** completarla mediante outpainting (un prompt sugerido por IA, totalmente editable) — muestra una vista previa del antes/después, vuelve a revisar el resultado, permite extender de nuevo o descartar, y lo guarda como una nueva versión de imagen. Opcional y no bloqueante; las imágenes bien encuadradas se generan directamente
- 🔄 **Actualización automática** — Controlado por versión al inicio + una verificación periódica cada 24h; se actualiza mediante `git` (checkout) o una **descarga y reemplazo de tarball** para instalaciones sin git, y luego se reinicia en el mismo lugar (relanzamiento supervisado / recarga de gunicorn) u ofrece un botón de **Reiniciar** con un solo clic — nunca sobrescribe tu `data/` ni tu `.env` (`ARTSMOKER_AUTO_UPDATE=false` para desactivar)

### 📝 1.2 Capturas de pantalla

**Estudio de Imagen** — Configuración a la izquierda con desplegable de multiselección de modelos, tipo de recurso, dimensiones y opciones de postprocesamiento. Flujo de trabajo de prompt en 3 pasos a la derecha con los botones Diseñador de prompts y Generar Prompt Mejorado. Declaración de PI y estimación de costos en la parte inferior.

![Estudio de Imagen — Configuración, flujo de trabajo de prompt y controles de generación](docs/images/image-studio-top.png)

**Estudio de Imagen — Resultados de generación** — El prompt mejorado se muestra arriba, los resultados de comparación multimodelo abajo. Cada modelo genera de forma independiente con optimización de prompt específica por modelo. Los resultados muestran el nombre del modelo, las dimensiones y el costo de generación.

![Estudio de Imagen — Prompt mejorado y resultados de generación](docs/images/image-studio-results.png)

**Estudio de Imagen — Comparación de modelos** — Cuadrícula de comparación lado a lado de todos los modelos seleccionados (8 mostrados — Amazon Bedrock y autoalojados por igual). Cada tarjeta de opción lleva su propia tira de variaciones; para la opción seleccionada se muestra el prompt negativo específico del modelo. Los interruptores de postprocesamiento (Eliminar fondo, Convertir a SVG, Escalar (Creativo)) se aplican a los resultados existentes sin regenerar.

![Estudio de Imagen — Cuadrícula de comparación multimodelo con variaciones](docs/images/image-studio-comparison.png)

**Inspiración de imagen (guiada por referencia)** — Suelta de 1 a 3 imágenes de referencia, di lo que quieres y elige cómo usarlas: **Fiel a la referencia** (edición fiel al píxel en un modelo de edición de imágenes desplegado) o **Inspirado en la referencia** (una IA de visión escribe el prompt mejorado — funciona con cualquier selección de modelos, opciones y variaciones). El prompt derivado se previsualiza y es totalmente editable antes de generar.

![Inspiración de imagen — imágenes de referencia, instrucción y vista previa editable del prompt mejorado](docs/images/image-inspiration.png)

**Inspiración de imagen — Resultados** — La referencia se convierte en una nueva creación (aquí, una caricatura dibujada a partir de la foto de referencia), registrando el prompt exacto enviado al modelo y el coste por imagen.

![Inspiración de imagen — caricaturas generadas a partir de una imagen de referencia](docs/images/image-inspiration-results.png)

**Diseñador de prompts** — La IA descompone su prompt en componentes visuales editables (Sujeto, Escena, Composición, Iluminación, Estilo y Colores). Cada campo se puede editar individualmente con controles de bloquear/variar para opciones creativas genuinamente distintas.

![Diseñador de prompts — Descomposición visual estructurada con campos editables](docs/images/prompt-designer-top.png)

**Diseñador de prompts — Paleta de colores** — Paletas de colores con nombre e indicadores hexadecimales, palabras clave de estilo y controles de nivel de calidad. La IA aprende su identidad visual y la aplica de forma consistente en todas las generaciones.

![Diseñador de prompts — Paleta de colores, palabras clave de estilo y controles de calidad](docs/images/prompt-designer-bottom.png)

**Biblioteca de Estilos** — Suba el arte existente de su juego, la IA analiza el estilo visual y produce una guía de prompts rica en metadatos. Las imágenes de referencia se muestran con el análisis completo de IA y el perfil de estilo JSON.

![Biblioteca de Estilos — Análisis de estilo por IA con imágenes de referencia](docs/images/style-library-top.png)

![Biblioteca de Estilos — Imágenes de referencia, opciones de importación y datos de análisis](docs/images/style-library-bottom.png)

**Galería** — Vista unificada de todas las imágenes y videos generados con filtro de tipo de medio, filtro de estilo, búsqueda y ordenamiento. Haga clic en cualquier recurso para abrir el visor completo. El botón **Importar imagen** lleva una imagen existente a la galería — elija un tipo de recurso (Personaje/Recurso de juego habilitan 3D), y se convierte a PNG y queda editable y lista para 3D al instante.

![Galería — Cuadrícula de recursos generados con filtros](docs/images/gallery.png)

**Visor de recursos** — Vista previa a tamaño completo con interfaz de pestañas (PNG, Editar, Exportar y recortes, Metadatos, Modelo 3D), barra de versiones de la imagen y descarga directa de PNG/SVG. Controles de zoom/ajuste/medición sobre la imagen compuesta en tablero de ajedrez.

![Visor de recursos — Vista previa a tamaño completo con opciones de descarga](docs/images/asset-viewer.png)

**Visor de recursos — Edición de imágenes** — Cinco modos de edición: Inpaint, Borrar, Outpaint, Reemplazar, Recolorear. En la imagen: **Outpaint**, con la regla de medición, los valores en píxeles por lado y el botón ✨ Generar prompt, que lee la imagen y escribe el prompt de edición por ti. El historial de versiones se conserva — los originales nunca se sobrescriben.

![Visor de recursos — Extensión con regla de medición y prompt sugerido por la IA](docs/images/asset-viewer-edit.png)

**Visor de recursos — Exportar y recortes** — Artefactos por versión listos para tu juego, motor o herramienta de diseño: SVG vectorial de la imagen completa, recorte PNG sin fondo y recorte SVG. La eliminación de fondo se ejecuta gratis en tu equipo (un procesado de pago con Amazon Bedrock es opcional).

![Visor de recursos — Exportar y recortes con SVG vectorial y recortes sin fondo](docs/images/asset-viewer-export-cutouts.png)

Tras una ronda de outpainting (v3 abajo), la misma pestaña regenera los tres artefactos para la versión de cuerpo entero mejorada.

![Visor de recursos — Exportar y recortes para la versión de cuerpo entero tras outpainting](docs/images/asset-viewer-export-cutouts-outpainted.png)

**Visor de recursos — Metadatos** — El linaje completo del prompt (tu prompt → descomposición del Diseñador de prompts → prompt recompuesto → prompt refinado adaptado al modelo), detalles de generación, desglose de costes y el historial completo de versiones.

![Visor de recursos — Metadatos con linaje completo del prompt e historial de versiones](docs/images/asset-viewer-metadata.png)

*Las capturas del pipeline 3D — generación, revisión de la fuente, exportación adaptada al motor de juego y variantes — se muestran más abajo, en la sección 1.9 (Generación de modelo 3D), junto a las funciones que ilustran.*

**Estudio de Video** — Configuración a la izquierda (modelo, modo de generación, duración, región, estimación de costos), prompt a la derecha. Ofrece los modelos de video que **Sincronizar desde AWS** descubre en su cuenta — p. ej., Luma AI Ray (relaciones de aspecto, bucle).

![Estudio de Video — Configuración y prompt](docs/images/video-studio.png)

![Estudio de Video — Generación en progreso con prompt mejorado por IA](docs/images/video-studio-generating.png)

![Estudio de Video — Video completado con miniatura y videos recientes](docs/images/video-studio-completed.png)

**Reproductor de video** — Haga clic en un video para reproducirlo en línea con metadatos completos (prompt original, prompt mejorado por IA, modelo, duración, región).

![Reproductor de video — Reproducción de un video generado con metadatos](docs/images/video-player.png)

### 📝 1.3 Generación de dos niveles

Para cada prompt, la IA crea **Opciones** — interpretaciones de diseño fundamentalmente diferentes (p. ej. para "un guerrero": berserker vikingo, samurái japonés, guerrero tribal, ciber-soldado, hoplita griego). Para cada opción, el modelo de imagen produce **Variaciones** — diferentes semillas aleatorias que aportan diferencias visuales sutiles. Esto ofrece a los artistas una amplia paleta creativa para elegir.

### 📝 1.4 Selección multimodelo

El menú desplegable de modelos admite **multiselección basada en casillas de verificación** — elija cualquier combinación de modelos para una sola ejecución de generación:

- **Modelo único** — marque un modelo para una generación enfocada (más rápida, más económica)
- **Varios modelos** — marque 2-3 modelos específicos para una comparación dirigida (p. ej. solo SD 3.5 + FLUX.2)
- **Todos los modelos disponibles** — el interruptor de la parte inferior selecciona/deselecciona todos los modelos habilitados para una comparación completa lado a lado

Cada modelo se ejecuta de forma independiente: si modelos más estrictos bloquean el prompt, aún obtiene resultados de los modelos que lo aceptaron, con etiquetas de estado claras (correcto, bloqueado por moderación o fallido) en cada tarjeta de opción. La estimación de costos se actualiza en tiempo real a medida que marca/desmarca modelos.

Un interruptor opcional **"Prompts optimizados por modelo"** adapta el prompt a las fortalezas de cada modelo — los prompts se reescriben por modelo (p. ej. potenciadores de calidad para SD 3.5, lenguaje natural para FLUX.2, señales de renderizado de texto de primera clase para Qwen-Image).

### 📝 1.5 Generación guiada por referencia

Más allá de escribir un prompt desde cero, puede generar **a partir de 1-3 imágenes de referencia más una instrucción** — elija el modo con el control segmentado en la parte superior del área de prompt del Estudio de Imagen:

- **Fiel a la referencia** — conserve el sujeto, producto o personaje de su referencia y cambie el resto (tema, fondo, vestuario, iluminación) exactamente como diga su instrucción. Ideal para personajes consistentes o tomas de producto a través de escenas. Este modo se ejecuta en un editor por instrucciones autoalojado (en esta versión, Qwen-Image-Edit) y aparece **una vez desplegado** — si no lo está, ArtSmoker le indica directamente cómo desplegarlo desde Modelos Personalizados (un clic, el mismo flujo que los pipelines 3D). Seguro para uso comercial (Apache-2.0).
- **Inspirado en la referencia** — la IA de visión de ArtSmoker lee sus referencias y su instrucción, escribe un prompt mejorado (que se le muestra primero) y luego genera con sus modelos normales de texto a imagen. **Siempre disponible** — sin necesidad de despliegue. Excelente para tomar prestado un aspecto, una paleta o una composición sin copiar el sujeto.

- **Remezclar la referencia** — el clásico imagen a imagen basado en fuerza: los *píxeles* de su referencia van directamente a un modelo de Bedrock que el registro marca como capaz (p. ej., Stable Diffusion 3.5 Large, Stable Image Ultra), con un **dial de fuerza**: sutil conserva casi intactos la composición, la paleta y el ambiente; atrevido la trata como inspiración libre. Con más de una Opción se convierte en una **escalera de fuerzas** — una tarjeta por fuerza, de sutil a atrevida, lado a lado. *Conserva el diseño, no la identidad* (caras y productos derivan — use Fiel a la referencia para trabajo exacto). El tamaño de salida sigue a la imagen de referencia. **Siempre disponible** — sin despliegue y sin llamada de análisis visual.

Los tres modos requieren una instrucción para que usted mantenga el control de *para qué* sirve la referencia. La generación guiada por referencia es independiente de la Biblioteca de Estilos (que analiza muchas imágenes en un perfil de estilo reutilizable) — úsela para generaciones puntuales impulsadas por imágenes.

### 📝 1.6 Estudio de Video

Genere videos y animaciones impulsados por IA a partir de prompts de texto. El Estudio de Video ofrece los modelos de video que **Sincronizar desde AWS** descubre en su cuenta (consulte [Sobre los nombres de modelos](#about-model-names)). Por ejemplo, **Luma AI Ray v2**:

| Característica | Luma Ray v2 |
|---------|-------------|
| **Duración máxima** | 9 segundos |
| **Resolución** | 720p / 540p |
| **Relaciones de aspecto** | 7 opciones (1:1, 16:9, 9:16, etc.) |
| **Imagen a video** | Sí (cuadro inicial + final) |
| **Video en bucle** | Sí |
| **Precio** | ~$1.50/seg |

**Cómo funciona:**
1. Seleccione un modelo de video y configure la duración, la relación de aspecto y la región
2. Ingrese un prompt — la IA lo mejora con vocabulario cinematográfico, movimientos de cámara y señales de coherencia temporal
3. Haga clic en Generar — el trabajo se ejecuta de forma asíncrona mediante `StartAsyncInvoke`, la salida va a su bucket de S3 configurado
4. Se consulta el estado cada 5 segundos — al completarse, se extrae la miniatura (vía ffmpeg) y el MP4 se descarga localmente (o se transmite desde S3)
5. Los videos aparecen tanto en la sección "Videos recientes" del Estudio de Video como en la Galería unificada

**Se requiere un bucket de S3**: la generación de video produce su salida en S3. Puede configurarlo desde Configuración de video en la UI (explorar buckets existentes o crear uno nuevo), o crear uno vía CLI:

```bash
# Crear un bucket de S3 para almacenar video (sustituya REGION y YOUR_ORG)
aws s3api create-bucket --bucket artsmoker-video-YOUR_ORG --region us-east-1

# Para regiones distintas de us-east-1, añada LocationConstraint:
aws s3api create-bucket --bucket artsmoker-video-YOUR_ORG --region us-west-2 \
  --create-bucket-configuration LocationConstraint=us-west-2
```

Modo de almacenamiento: descarga local (predeterminado) o streaming desde S3 bajo demanda.

**Mejora de prompts de video**: el LLM añade movimientos de cámara (paneo, zoom, dolly, seguimiento), detalles de iluminación y señales temporales. Como los modelos de video no admiten prompts negativos, los conceptos a evitar se integran de forma natural en el prompt positivo.

### 📝 1.7 Estudio de Chat

Una interfaz de chat LLM con todas las funcionalidades — como una IA conversacional autoalojada, ejecutándose en su propia cuenta de AWS sin acceso de terceros a los datos.

**Cada modelo de chat que Sincronizar desde AWS encuentre en su cuenta** (consulte [Sobre los nombres de modelos](#about-model-names)) — p. ej., Claude (Sonnet, Opus, Haiku), Amazon Nova, Meta Llama, Mistral, Cohere, Qwen, DeepSeek, Google Gemma y NVIDIA Nemotron — además de cualquier modelo personalizado/importado de su cuenta.

**Funcionalidades principales:**
- **Respuestas en streaming** — renderizado token por token en tiempo real vía Bedrock ConverseStream
- **Renderizado Markdown** — encabezados, negrita/cursiva, listas, tablas, citas, líneas horizontales
- **Bloques de código** — resaltado de sintaxis (highlight.js) con insignia de lenguaje + botón de copiar
- **Métricas por mensaje** — tokens de entrada/salida, latencia, costo estimado, modelo utilizado
- **Barra de ventana de contexto** — indicador visual de llenado (verde/ámbar/rojo) con recuento de tokens usados/máximo
- **Cambio de región** — cada modelo muestra todas las regiones disponibles, elija la más cercana o la más económica

**Gestión de sesiones:**
- Múltiples sesiones simultáneas con autoguardado
- Renombrar en línea, duplicar, eliminar, buscar/filtrar en la barra lateral
- Exportar conversaciones como Markdown
- Totales de sesión: recuento de tokens, costo estimado, recuento de mensajes

**Funcionalidades avanzadas:**
- **Plantillas de prompt de sistema** — Asistente general, Experto en programación, Escritor creativo, Diseñador de juegos, Analista de datos, Redactor técnico
- **Visión/multimodal** — arrastrar y soltar, selector de archivos o Ctrl+V para pegar imágenes con modelos compatibles con visión
- **Compactación de contexto** — la IA resume los mensajes más antiguos para liberar espacio en la ventana de contexto
- **Regenerar** — vuelva a ejecutar cualquier respuesta de IA con el mismo prompt
- **Editar y reenviar** — modifique cualquier mensaje del usuario y reproduzca desde ese punto
- **Bifurcar** — ramifique una conversación desde cualquier mensaje a una nueva sesión

**Transparencia de precios:** el selector de modelos muestra el costo por cada 1K tokens, y la barra de información de precios muestra el costo estimado para conversaciones de 10K y 100K tokens.

### 📝 1.8 Conciencia del tipo de recurso

El **Tipo de recurso** seleccionado cambia fundamentalmente cómo la IA interpreta su prompt — no solo el modelo de imagen, sino cada etapa del pipeline. Cuando escribe "hospital" y selecciona distintos tipos de recurso, obtiene salidas completamente diferentes:

| Tipo | Composición | Encuadre | Enfoque técnico |
|------|-------------|----------|-----------------|
| **Imagen fotorrealista** *(predeterminado)* | Encuadre natural, de tipo fotográfico — el sujeto en un entorno real acorde al contexto. | Perspectiva de cámara real: a la altura de los ojos, poca profundidad de campo para retratos, gran angular para paisajes. | Dirigido en lenguaje fotográfico (hora dorada, softbox de estudio, sensación de distancia focal) con imperfecciones naturales — textura de la piel, arrugas de la tela, desgaste. Nunca vocabulario de ilustración ni jerga de motores de render. |
| **Recurso de juego** | Objeto único aislado sobre fondo transparente. Sin escena, sin texto, sin UI. | Frontal o isométrico, el objeto ocupa el 70-80% del cuadro. | Bordes limpios y definidos para la eliminación de fondo, iluminación consistente desde la esquina superior izquierda, sin sombras en el suelo. Diseñado para componerse con otros recursos de juego a varias escalas. |
| **Personaje** | Figura de cuerpo completo o de 3/4, aislada sobre un fondo limpio. Un solo personaje. | El personaje ocupa el 60-75% vertical, de la cabeza a los pies, ligeramente descentrado. | Silueta fuerte y legible (identificable solo por la silueta), pose expresiva que transmite personalidad, rasgos faciales claros y detalles de vestuario. |
| **Icono** | Símbolo único, audaz y reconocible, centrado con generoso relleno. Máxima simplicidad. | Frontal o con ligera inclinación de 3/4, con espacio de respiro en los bordes. | Debe leerse claramente a 64x64 píxeles. Alto contraste, máximo 3-5 colores, formas audaces, sin líneas finas ni detalles minuciosos. |
| **Banner publicitario** | Ilustración escénica completa con composición dramática. Zona limpia y segura para texto reservada a un lado — sin texto ni tipografía renderizados. | Sensación cinematográfica amplia, cámara alejada para mostrar una escena. | Colores ricos y saturados, iluminación dramática (luz de borde, rayos volumétricos), profundidad de campo. La IA tiene instrucciones explícitas de NO renderizar texto; la zona segura para texto se mantiene limpia para la superposición en postproducción con herramientas de diseño (Figma, Canva, etc.). |
| **Entorno** | Paisaje completo con capas de profundidad de primer plano/plano medio/fondo, líneas guía. | Plano general amplio, horizonte en el tercio superior o inferior. | Perspectiva atmosférica (objetos distantes más claros/difusos), narrativa ambiental a través de los detalles, iluminación que establece el ambiente. |

Esto importa en cada etapa:

- **Botón "Generar Prompt Mejorado"** — Al hacer clic en él, la IA usa el tipo de recurso para reformular su descripción breve en un prompt de generación detallado, combinando sus palabras con las guías de estilo y las directivas del tipo de recurso. Su intención explícita siempre tiene prioridad sobre los valores predeterminados del estilo. Puede revisar la versión compuesta antes de generar.
- **Generación de conceptos** — Al generar múltiples opciones, la IA crea N interpretaciones de diseño diferentes que respetan todas las reglas estructurales del tipo de recurso. Una opción de Personaje siempre tiene una silueta legible; una opción de Banner publicitario siempre tiene una zona segura para texto sin texto renderizado.
- **El resultado** — Dos imágenes del mismo prompt pero con distintos tipos de recurso no se parecerán en nada. Un Recurso de juego "guerrero" es un sprite de personaje único y centrado. Un Banner publicitario "guerrero" es una escena de batalla épica con una zona limpia para la superposición del titular.

### 📝 1.9 Generación de modelos 3D (Imagen a 3D)

Genere mallas 3D completamente texturizadas a partir de cualquier imagen 2D — directamente en el visor de recursos. Seleccione una imagen de **Recurso de juego** o **Personaje**, abra la pestaña **Modelo 3D** y haga clic en Generar. El resultado es un GLB adaptado al motor de juego que puede orbitar, ampliar y descargar — sin modelado manual, desenvolvimiento UV ni pintado de texturas.

**El resultado final, primero:** un personaje generado por ArtSmoker, exportado como FBX adaptado al motor de juego y abierto en un Blender estándar — la cadena de LOD (LOD0–LOD3) intacta en el Outliner, texturas vinculadas, sin re-rigging ni arreglos manuales. Todo lo que sigue muestra cómo llegar hasta aquí desde un prompt de texto.

![FBX de ArtSmoker abierto en Blender — jerarquía del grupo LOD intacta con texturas vinculadas](docs/images/fbx-in-blender.png)

**El modelo generado — orbite, inspeccione, descargue:**

![Generación de modelo 3D — la malla del soldado generada vista desde múltiples ángulos en el visor 3D interactivo](docs/images/3d-model-result.png)

Una sola imagen 2D de personaje (a la izquierda, en la pestaña PNG) se convierte en una malla 3D completamente texturizada que puede rotar libremente en el navegador. La pestaña **Modelo 3D** ahora también lista los **modelos y herramientas** exactos usados para producir cada recurso (modelo de geometría, backend de texturizado, tipo de salida, instancia y parámetros de generación) — persistidos en los metadatos del recurso para una trazabilidad completa.

**Generando** — La pestaña Modelo 3D del visor de recursos: elige el endpoint del pipeline desplegado, el nivel de calidad (con tiempo y coste estimados) y los parámetros avanzados. El panel de licencia muestra las condiciones de cada pipeline, e **Mejorar la fuente** revisa visualmente la imagen antes de gastar tiempo de GPU.

![Generación de modelo 3D — Configuración y generación en el visor de recursos](docs/images/3d-model-generation.png)

**Mejorar la fuente** — Antes de generar, ArtSmoker mide la silueta del sujeto y señala los recortes (aquí: cortado en el borde inferior), sugiriendo los valores de extensión y un prompt de outpainting escrito por la IA — extiende, rellena o usa la imagen tal cual.

![Revisión de la fuente 3D — detección automática de recorte con extensión sugerida](docs/images/3d-source-review.png)

**Dos pipelines — usted elige.** ArtSmoker ofrece dos formas de convertir una imagen en un modelo 3D texturizado. Despliegue cualquiera de ellos (o ambos) desde Modelos Personalizados; cuando ambos están activos, usted elige por generación en el visor de recursos — cada uno muestra su costo est., tiempo y licencia para que decida con conocimiento de causa:

| Pipeline | Cómo funciona | Licencia | Uso comercial | Ideal para |
|----------|--------------|---------|----------------|------------|
| **TripoSG + backend de textura** | TripoSG construye la malla; un backend de texturizado elegido (TRELLIS.2 / Hunyuan3D-Paint) la pinta | según el backend (abajo) | según el backend | Combinar geometría + un texturizador específico |
| **TRELLIS.2 (canalización completa)** | Un solo modelo genera **tanto** la geometría como la textura PBR (SLAT) | modelo + pesos MIT | ⚠️ **Horneado no comercial** — la exportación de la malla importa de forma rígida `nvdiffrast` (NVIDIA 1-Way Commercial); revise antes de un uso comercial | El camino más simple; prototipos y trabajo no comercial |

> **Uso comercial:** la ruta **TripoSG + backend de textura** es la vía segura para uso comercial — su horneado usa **Kaolin (Apache-2.0)**. El pipeline **completo de TRELLIS.2** es MIT en cuanto al modelo en sí, pero su horneado de malla `o_voxel` importa de forma rígida `nvdiffrast` (NVIDIA Source Code License, no comercial para usuarios generales) y no puede sustituirse sin parchear el código original — así que trate la salida del pipeline completo como no comercial a menos que haya resuelto esa dependencia. La licencia + cada dependencia se muestran en el diálogo de despliegue y de nuevo en el momento de generar.

**Variantes 3D** — Conserva varios resultados 3D por versión de imagen (aquí TripoSG frente al pipeline completo TRELLIS.2), cambia entre ellos o fija el predeterminado en cualquier momento; cada variante registra los modelos y herramientas exactos que la produjeron.

![Variantes 3D — TripoSG y TRELLIS.2 lado a lado con procedencia completa](docs/images/3d-model-variants.png)

**Cómo funciona el pipeline de TripoSG:**

1. **Extracción de geometría** — un transformador de flujo rectificado (TripoSG, 1.500 millones de parámetros, licencia MIT) convierte una sola imagen 2D en una malla 3D de alta fidelidad usando una representación de campo de distancia con signo (SDF). La densidad de la malla escala con el preajuste de calidad (hasta ~1M de caras en la resolución de octree más alta) para un detalle nítido en rostros y equipamiento.
2. **Texturizado** — la malla la pinta un **backend de texturizado que usted elige al desplegar** (predeterminado **TRELLIS.2**, Microsoft, MIT — un texturizador condicionado por SLAT/vóxeles que produce materiales PBR completos en un atlas de 4096²).
3. **Salida PBR** — exportado como un GLB con mapas PBR integrados, listo para renderizado basado en física en cualquier motor moderno.

El pipeline **TRELLIS.2 (canalización completa)** hace lo mismo de extremo a extremo en un solo modelo — sin un paso de texturizado por separado.

**La licencia a la vista — al desplegar Y al generar.** Cada opción desplegable muestra su **licencia completa y el desglose de dependencias** en el diálogo de despliegue — cada modelo que descarga, la licencia de ese modelo y si es apto para uso comercial o está restringido — y usted lo lee y lo acepta antes de desplegar. Al generar, el visor de recursos vuelve a mostrar la licencia y confirma *"aceptada al desplegar el `<fecha>`"* (sin necesidad de un segundo clic):

| Backend de texturizado | Licencia | Uso comercial | Ideal para |
|---------|---------|----------------|------------|
| **TRELLIS.2** *(predeterminado)* | MIT | ✅ Sí — requiere una atribución "Built with DINOv3" en su producto | Producción, recursos comerciales, máxima calidad |
| **Hunyuan3D-Paint** | Tencent Community | ❌ No comercial | Investigación / no comercial, rostros excepcionales |

La eliminación de fondo (el paso de recorte) usa **BiRefNet (MIT)** de forma predeterminada — totalmente limpio para uso comercial — con una alternativa no comercial (RMBG) disponible como opción explícita divulgada. ArtSmoker nunca descarga silenciosamente una dependencia restringida: cualquier cosa restringida o no comercial se nombra, se etiqueta y queda condicionada a una aceptación explícita.

**Salida:** GLB estándar con texturas PBR integradas — se importa directamente en Unity, Unreal Engine, Blender y otros motores de juego. El visor 3D interactivo admite órbita, zoom y panorámica para una inspección inmediata, y la pestaña **Modelo 3D** lista los modelos y herramientas exactos usados (modelo de geometría, backend de texturizado, dependencias, instancia, parámetros) para una trazabilidad completa.

**Infraestructura:** ambos pipelines se despliegan mediante el mismo flujo de Modelos Personalizados en 1 clic, con el selector en tiempo de despliegue mostrando la licencia, la tabla de dependencias, la instancia base y el costo/tiempo est. de cada opción. La instancia base correctamente dimensionada del pipeline completo de TRELLIS.2 es **`ml.g5.2xlarge`** (~$1.52/h; una ejecución en vivo midió un pico de ~4.78 GB de VRAM en los 24 GB de la A10G y se completó sin problemas — elegida frente a la `g6e.xlarge` con L40S, enormemente sobredimensionada para esta carga de trabajo y a un costo mayor). Los tamaños `g6e` mayores siguen disponibles como mejoras opcionales para mayor margen. Los endpoints escalan a cero en reposo — $0 de costo entre trabajos. El primer arranque en frío compila las extensiones de CUDA una vez (luego se almacenan en caché en S3 para reinicios rápidos). Antes de desplegar un modelo restringido, el diálogo **verifica previamente el acceso a HuggingFace para cada repositorio que descarga** y muestra un ✓/✗ por repositorio con el siguiente paso exacto — así nunca descubre una aceptación de licencia faltante minutos después de un arranque en frío.

> **Visualización del GLB:** las texturas se codifican como WebP (`EXT_texture_webp`) para mantener los archivos compactos — se renderiza perfectamente en el visor integrado, Blender 4.x, three.js y los importadores modernos de Unity/Unreal. macOS Preview/QuickLook no admite WebP-en-glTF y mostrará el modelo en negro; use el visor integrado o cualquier herramienta glTF moderna.

| Métrica | Valor |
|--------|-------|
| Calidad de malla | Hasta ~1M de caras, normales de vértice completas |
| Resolución de textura | Atlas PBR de 4096² (color base + metálico-rugosidad + alfa) |
| Licenciamiento | Seguro para uso comercial por defecto (TRELLIS.2 MIT + BiRefNet MIT); backends no comerciales ofrecidos con divulgación completa |
| Tipos de recurso soportados | Recurso de juego, Personaje |

### 📝 1.9.1 Exportaciones listas para el motor (GLB · FBX · USD)

![Visor 3D con herramientas por variante y opciones de exportación FBX/USD adaptadas al motor de juego](docs/images/3d-model-viewer-export.png)

Todo modelo 3D generado puede exportarse **preparado para su motor de juego**, directamente desde la pestaña 3D del visor de recursos:

- **Motor de destino** — elija Genérico (glTF, Y hacia arriba), Unreal Engine (eje Z arriba), Unity, Godot, Maya o 3ds Max. Las exportaciones FBX y USD se orientan con los ejes arriba/adelante correctos para ese motor, de modo que los modelos se importan de pie — sin correcciones manuales de rotación.
- **Preparación opcional, usted decide** (cada una en un menú desplegable independiente — nada es obligatorio):
  - **Empaquetado de texturas** — conjuntos de texturas por motor: **ORM** de Unreal (AO/Rugosidad/Metálico), **Metálico + Suavidad-en-alfa** de Unity, **Mask Map HDRP** de Unity. Cuando se selecciona, la exportación se convierte en un ZIP con el modelo más una carpeta `textures/`.
  - **LOD** — una cadena decimada **LOD0–LOD3** (100/50/20/5%) con un grupo LOD de FBX real que Unreal importa automáticamente; la nomenclatura `_LOD0…_LOD3` sirve a la vez como la convención de Unity.
  - **Colisión** — un casco convexo o una **descomposición convexa CoACD**, nombrada según la convención de cada motor (`UCX_*` para la importación automática de Unreal, sufijos `-convcolonly` para Godot).
  - **UV2 de lightmap** — un segundo canal UV con proyección inteligente para iluminación precalculada.
- **Flujo en dos pasos** — los botones dicen **Generar FBX/USD/GLB** para una combinación que aún no existe; al hacer clic se convierte en el servidor (una línea de estado le mantiene informado — los modelos grandes pueden tardar uno o dos minutos). Una vez generada, el botón cambia a **Descargar** con un ✓ y la entrega al instante. Cada combinación distinta se guarda en caché — nada se regenera jamás.
- **Chips de listo para descargar** — la pestaña 3D lista todas las combinaciones que ya haya generado para la versión actual, con un solo clic para volver a descargar cualquiera de ellas.
- **El GLB original es sagrado** — "Descargar GLB (original)" siempre devuelve la salida intacta, byte a byte, del pipeline de generación. Las exportaciones procesadas (incluido un GLB procesado con LOD/colisión incorporados) son archivos con nombre propio junto a él.
- **Cero configuración** — las conversiones se ejecutan en el servidor mediante un Blender sin interfaz gestionado: si existe una instalación, se reutiliza; de lo contrario, una copia portátil se descarga automáticamente en el primer uso (vea la pestaña Configuración del modelo → Mantenimiento para la versión y las actualizaciones). Los usuarios finales no instalan nada.

### 📝 1.9.2 Qué esperar del 3D generado por IA — Una guía honesta

La conversión de imagen a 3D es una tecnología joven, y conviene saber qué ofrecen genuinamente los mejores modelos actuales (incluidos los que ejecuta ArtSmoker) — y qué no. La salida es una **malla densa, al estilo de un objeto escaneado**: hasta ~1M de triángulos sin estructura con texturas PBR horneadas. De cerca notará una característica superficie irregular, y los detalles finos (mechones de pelo, correas, flecos de tela) son el punto más débil de la geometría por IA. **No hay topología de quads limpia, ni bucles de aristas aptos para animación, ni rig** — ese es el estado del arte en toda la industria, no una limitación exclusiva de una herramienta.

**Dónde brillan estos recursos — y dónde necesitan un artista:**

| Caso de uso | ¿Listo para usar? |
|----------|---------------|
| Accesorios, decorado de entorno, ambientación de escena | ✅ Sí — utilizable tal cual |
| Personajes de fondo / media distancia, multitudes | ✅ Sí — a distancia el ruido de la superficie desaparece; use la cadena de LOD |
| Prototipado, maquetas de volumen, previsualización, demos de presentación | ✅ Sí — posiblemente el caso de uso más fuerte |
| Juegos móviles / estilizados | ✅ A menudo — los LOD decimados ayudan |
| Personajes protagonistas, primeros planos, personajes animados | ⚠️ Un punto de partida — cuente con retopología, limpieza y rigging por parte de un artista |

Lo que ArtSmoker añade sobre la malla en bruto es que todo llega **correctamente empaquetado para su motor** — el eje arriba correcto por destino, cadena de LOD, proxies de colisión, empaquetado de texturas específico del motor — de modo que el trabajo restante es creativo, no de fontanería.

**¿Inspecciona las exportaciones en Blender (u otra herramienta DCC)? Dos cosas le parecerán extrañas — ambas son correctas:**

- **¿Generado con LOD?** El archivo contiene **4 copias apiladas** del modelo (LOD0–3). Vistas juntas parpadean (z-fighting) y se ven ruidosas — oculte LOD1–3 en el Outliner y juzgue la calidad solo con LOD0. Los motores de juego muestran exactamente un LOD a la vez, así que esto nunca ocurre dentro del motor.
- **¿Generado con colisión?** Una carcasa blanca y angulosa de mallas `UCX_*` **envuelve el modelo** — es el proxy de física, no su recurso. Oculte esos objetos para ver el modelo texturizado en su interior. Los motores los importan automáticamente como colisión invisible.

### 📝 1.9.3 Uso comercial de un modelo — A quién pagar y cómo

Si le encanta la salida de un modelo y quiere usarla comercialmente, el camino depende de **cómo monetiza su creador**. ArtSmoker muestra la licencia de cada modelo en el momento del despliegue; esta es la guía complementaria de "¿y ahora qué hago?". *(Verificado contra los sitios de los proveedores y los archivos de licencia de HuggingFace en agosto de 2026 — las licencias cambian rápido, así que confirme siempre los términos vigentes del proveedor. Solo con fines informativos — consulte la [Exención de responsabilidad](#disclaimer).)*

Los cuatro patrones que encontrará:

1. **Ya es suyo (Apache-2.0 / MIT)** — el uso comercial está incluido, gratis. No hay ningún producto de licencia que comprar; el creador monetiza a través de su propia API alojada. Su única obligación es cumplir con los avisos y la atribución.
2. **Gratis hasta que sea grande (licencias comunitarias)** — el uso comercial está incluido **por debajo de un umbral** (ingresos o usuarios activos mensuales). Por encima de él, la propia licencia le indica que solicite una concesión empresarial al proveedor — una conversación comercial, no una tienda.
3. **Compre la licencia, conserve los pesos** — los pesos de HuggingFace son no comerciales, pero el creador vende por separado una **licencia comercial de autoalojamiento**. Una vez que la posee, los *mismos pesos que ya desplegó* pasan a ser legales para uso comercial — técnicamente nada cambia en ArtSmoker.
4. **La puerta de acceso es el muro de pago** — el propio repositorio de HuggingFace está restringido (gated); un acuerdo comercial con el proveedor desbloquea el acceso de su cuenta de HF. El flujo existente de ArtSmoker de token de HuggingFace + comprobación previa de repositorios restringidos funciona entonces tal cual.

| Creador / modelos | Patrón | Su siguiente paso para el autoalojamiento comercial |
|---|---|---|
| **Alibaba** — Qwen-Image, Qwen-Image-Edit | 1 | Nada que comprar (Apache-2.0). Conserve los avisos de licencia. |
| **Microsoft** — TRELLIS.2 · **VAST** — TripoSG | 1 | Nada que comprar (MIT). Nota: las dependencias de origen (p. ej. Meta DINOv3) tienen sus propias restricciones y términos. |
| **Black Forest Labs** — FLUX.2 [klein] 4B | 1 | Nada que comprar — Apache-2.0, uso comercial gratuito. |
| **Stability AI** — SD 3.5 (autoalojado) | 2 | Gratis, incl. uso comercial, por debajo de **$1M de ingresos anuales totales** (la aceptación de la puerta de HF *es* la licencia). Por encima, la licencia **se termina automáticamente** — solicite una licencia Enterprise en stability.ai/enterprise. **La atribución "Powered by Stability AI" es obligatoria en todos los niveles.** |
| **Tencent** — HunyuanImage 3.0 / Hunyuan3D | 2 | Gratis, incl. uso comercial, por debajo del umbral — **ojo: es por modelo**: HunyuanImage 3.0 = 100M de MAU; **Hunyuan3D-2.1 = solo 1M de MAU** (por encima: escriba a hunyuan3d@tencent.com). **No hay concesión alguna en la UE, el Reino Unido o Corea del Sur**, sin importar el tamaño. |
| **Black Forest Labs** — FLUX.1/.2 [dev], Kontext | 3 | Compre una **FLUX Commercial Weights License** (autoservicio en dashboard.bfl.ai/licensing; los niveles son suscripciones con tope de volumen de imágenes). Sigue usando los mismos pesos de HF. Atención a las obligaciones: informes de uso, filtrado de salidas, **prohibido exponer el modelo como API o revenderlo**; las nuevas versiones del modelo **no** quedan cubiertas automáticamente fuera de Enterprise. |
| **Bria** — FIBO, RMBG-2.0 | 4 | La puerta de HF concede acceso **no comercial** de inmediato; el autoalojamiento comercial requiere un **acuerdo de pago con Bria** (formulario de compra enlazado desde cada ficha de modelo / bria.ai). No existe ningún umbral comercial gratuito. Una vez concedido el acceso, despliegue a través de ArtSmoker exactamente igual que antes. |

**Cómo encaja esto con ArtSmoker:** la contratación casi nunca cambia nada técnico. Para los patrones 1–3, los pesos que despliega son idénticos antes y después — lo que cambia es el contrato que usted posee (guarde su registro de licencia; el diálogo de despliegue de ArtSmoker registra su aceptación de la licencia de los *pesos*, pero las concesiones comerciales le vinculan directamente con el proveedor). Para el patrón 4, una vez que el proveedor aprueba su cuenta de HuggingFace, la comprobación de acceso a repositorios restringidos de ArtSmoker se pone en verde y el despliegue procede con normalidad. Cuando un proveedor publica una nueva versión de un modelo, vuelva a comprobar si su concesión la cubre (la de Stability sí, automáticamente; la de BFL en general no, fuera de Enterprise; Tencent emite un texto de licencia nuevo por cada versión).

<a id="get-started"></a>

## 📌 2. Requisitos previos

- **Python 3.12, 3.13 o 3.14** — el SDK de voz de Nova Sonic (`aws_sdk_bedrock_runtime`) requiere 3.12 o posterior, y `numba` (usado por la eliminación de fondo local mediante `rembg`) aún no admite 3.15
- **AWS CLI** configurado con credenciales válidas
- **Permisos IAM** para el acceso a Bedrock (ver a continuación)

### 📝 2.1 Credenciales de AWS

ArtSmoker usa la [resolución estándar de credenciales de boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials), por lo que cualquiera de los siguientes métodos funciona:

| Método | Ideal para | Cómo |
|--------|----------|-----|
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

### 📝 2.1.1 Verificar el acceso a Bedrock

Confirmar que las credenciales funcionan (`sts:GetCallerIdentity`) solo verifica la identidad — no confirma que tenga permisos de Bedrock. ArtSmoker usa varias API de Bedrock, por lo que una simple prueba de listado no es suficiente. La verificación más fiable:

```bash
# Prueba 1: ¿Puede listar modelos? (requiere bedrock:ListFoundationModels)
aws bedrock list-foundation-models --region us-east-1 --query "modelSummaries[0].modelId" --output text

# Prueba 2: ¿Puede invocar un modelo de imagen? (requiere bedrock:InvokeModel)
# (p. ej., Stable Diffusion 3.5 Large — sustitúyalo por cualquier ID de modelo de imagen
#  de la lista de la Prueba 1 si este no se ofrece en su cuenta o Región.)
aws bedrock-runtime invoke-model --region us-west-2 \
  --model-id stability.sd3-5-large-v1:0 \
  --content-type application/json --accept application/json \
  --body '{"prompt":"test","aspect_ratio":"1:1"}' \
  /dev/null 2>&1 && echo "InvokeModel: OK" || echo "InvokeModel: FAILED"

# Prueba 3: ¿Puede usar la API Converse? (se autoriza mediante bedrock:InvokeModel)
# (Sustitúyalo por cualquier ID de modelo Claude al que tenga acceso — p. ej., el perfil
#  de inferencia de Sonnet actual de la lista de la Prueba 1; la versión exacta cambia con el tiempo.)
aws bedrock-runtime converse --region us-west-2 \
  --model-id us.anthropic.claude-sonnet-5 \
  --messages '[{"role":"user","content":[{"text":"hi"}]}]' \
  --inference-config '{"maxTokens":1}' \
  --query "output.message.content[0].text" --output text 2>&1 && echo "Converse: OK" || echo "Converse: FAILED"

# Prueba 4: ¿Puede listar modelos personalizados? (requiere bedrock:ListCustomModels)
aws bedrock list-custom-models --region us-east-1 \
  --query "modelSummaries[0].modelName" --output text 2>&1 && echo "ListCustomModels: OK" || echo "ListCustomModels: no custom models (or permission denied)"
```

Si las pruebas 1-3 pasan, sus permisos principales están configurados. La prueba 4 solo se necesita para el descubrimiento de modelos personalizados. Si la prueba 1 pasa pero las pruebas 2-3 fallan, su política IAM permite listar pero no invocar — actualícela usando la tabla de permisos de abajo.

<a id="iam-permissions"></a>

### 📝 2.2 Permisos IAM

Su usuario, rol o instance profile IAM necesita estos permisos:

| Permiso | Se usa para |
|------------|----------|
| `bedrock:InvokeModel` | Generación de imágenes, edición de imágenes, postprocesamiento (todos los modelos de imagen) |
| `bedrock:InvokeModelWithResponseStream` | Respuestas LLM en streaming (Estudio de Chat) — la API ConverseStream se autoriza mediante esta acción. La API Converse sin streaming (refinamiento de prompts, análisis de estilo, generación de conceptos) se autoriza mediante `bedrock:InvokeModel` — no existe una acción `bedrock:Converse` separada |
| `bedrock:InvokeModelWithBidirectionalStream` | Transcripción de voz (opcional — la app funciona sin ello) |
| `bedrock:StartAsyncInvoke` | Generación de video (invocación asíncrona; la operación en sí se autoriza mediante `bedrock:InvokeModel`, que también se concede) |
| `bedrock:GetAsyncInvoke` | Consultar el estado del trabajo de generación de video |
| `bedrock:ListAsyncInvokes` | Listar trabajos de generación de video |
| `bedrock:ListFoundationModels` | Descubrimiento de modelos fundacionales (Sincronizar desde AWS) |
| `bedrock:ListCustomModels` | Descubrir modelos personalizados afinados en su cuenta |
| `bedrock:ListImportedModels` | Descubrir modelos importados en su cuenta |
| `bedrock:GetCustomModel` | Leer detalles del modelo personalizado (modelo base, estado) |
| `bedrock:GetImportedModel` | Leer detalles del modelo importado (arquitectura, estado) |
| `bedrock:ListProvisionedModelThroughputs` | Encontrar modelos personalizados invocables con provisioned throughput |
| `bedrock:ListCustomModelDeployments` | Encontrar modelos personalizados con despliegues bajo demanda |
| `bedrock:CreateInference` *(o la política `AmazonBedrockMantleInferenceAccess`)* | **Amazon Bedrock Mantle** — modelos de frontera accesibles solo a través del endpoint de Mantle (p. ej., OpenAI GPT‑5.x, Claude Mythos, GLM, Grok, Qwen, Gemma). Su ausencia afecta solo a esos modelos; Claude vía Converse sigue funcionando. |
| `account:ListRegions` | Escanear solo las regiones **habilitadas** de su cuenta durante la sincronización (rápido, sin errores en regiones opt‑in). Opcional — recurre a escanear todas las regiones. |
| `account:GetRegionOptStatus` | Leer el estado de opt‑in por región (complemento de `account:ListRegions`). Opcional. |
| `s3:CreateBucket` | Crear un bucket de S3 para almacenamiento de video (opcional, vía UI) |
| `s3:PutObject` / `s3:GetObject` / `s3:DeleteObject` / `s3:ListBucket` | Almacenamiento y recuperación de la salida de video; entradas/salidas de trabajos asíncronos y artefactos 3D para Modelos Personalizados |
| `s3:ListAllMyBuckets` | El explorador de buckets S3 en Configuración de video / importación de estilos (opcional) |
| `s3:GetLifecycleConfiguration` / `s3:PutLifecycleConfiguration` | Reglas de caducidad automática para los archivos temporales de trabajos asíncronos en el bucket de despliegue (Modelos Personalizados) |
| `aws-marketplace:Subscribe` | Suscripción automática en el primer uso de modelos de terceros (incl. modelos de Mantle de terceros) |
| `aws-marketplace:ViewSubscriptions` | Comprobar las suscripciones de modelos existentes |
| `sts:GetCallerIdentity` | Validación de credenciales al inicio; también sustenta el token bearer de Mantle firmado localmente |
| `pricing:GetProducts` | Obtener los precios de los modelos al ejecutar Sincronizar desde AWS (opcional) |
| `sagemaker:*` | Modelos personalizados autoalojados en Amazon SageMaker (opcional — solo si usa Modelos Personalizados) |
| `application-autoscaling:*` (registrar/anular el registro de objetivos, crear/eliminar/describir políticas) | Escalado a cero + desde cero para los endpoints de Modelos Personalizados (opcional — solo para Modelos Personalizados) |
| `cloudwatch:PutMetricAlarm` / `DeleteAlarms` / `DescribeAlarms` | La alarma de trabajos en cola (backlog) para el escalado desde cero de los endpoints de Modelos Personalizados (opcional) |
| `logs:DescribeLogStreams` / `FilterLogEvents` / `GetLogEvents` / `PutRetentionPolicy` | Detección de disponibilidad del endpoint + retención de logs para Modelos Personalizados (opcional) |
| `servicequotas:GetServiceQuota` / `RequestServiceQuotaIncrease` | Comprobación de la cuota de instancias GPU / solicitud de aumento con un clic en el diálogo de despliegue (opcional) |
| `ecr:DescribeRepositories` | Resolver la imagen de SageMaker Deep Learning Container al desplegar (opcional) |
| `iam:CreateServiceLinkedRole` (acotado a `sagemaker.application-autoscaling.amazonaws.com`) | El primer autoescalado de endpoints en la cuenta crea automáticamente `AWSServiceRoleForApplicationAutoScaling_SageMakerEndpoint` (opcional — omítalo si ese rol ya existe) |
| `iam:PassRole` | Permitir que Amazon SageMaker use su rol (opcional — solo para Modelos Personalizados) |
| `iam:CreateRole` / `iam:AttachRolePolicy` / `iam:PutRolePolicy` | Autocrear el rol de ejecución de Amazon SageMaker en el primer despliegue (opcional — solo para Modelos Personalizados) |
| `iam:GetRole` / `iam:UpdateAssumeRolePolicy` | Autoconfigurar un rol existente para la confianza de Amazon SageMaker (opcional) |
| `secretsmanager:CreateSecret` / `UpdateSecret` / `GetSecretValue` / `DescribeSecret` / `DeleteSecret` | Almacenamiento cifrado de tokens de HuggingFace en modelos restringidos (opcional — se limpia automáticamente al desmantelar) |

**Configuración más rápida** (políticas administradas — el acceso más amplio):

```bash
# Opción A: adjunte políticas administradas a su usuario IAM (lo más sencillo para el desarrollo local)
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

# Endpoint de Amazon Bedrock Mantle — necesario para los modelos de frontera (p. ej., OpenAI GPT-5.x,
# Claude Mythos, GLM, Grok). Omítalo solo si no va a usar modelos exclusivos de Mantle.
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockMantleInferenceAccess

# Añada acceso a S3 para el almacenamiento de video
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

**Configuración acotada** (permisos más ajustados — recomendado para producción):

```bash
# Cree una política IAM acotada con solo los permisos que necesita ArtSmoker
aws iam create-policy --policy-name ArtSmokerAccess --policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Bedrock",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
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
        "bedrock:ListCustomModelDeployments"
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
      "Action": ["s3:CreateBucket", "s3:PutObject", "s3:GetObject", "s3:ListBucket", "s3:DeleteObject", "s3:HeadBucket", "s3:GetLifecycleConfiguration", "s3:PutLifecycleConfiguration"],
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
      "Action": ["sts:GetCallerIdentity", "pricing:GetProducts", "s3:ListAllMyBuckets"],
      "Resource": "*"
    },
    {
      "Sid": "SageMakerCustomModels",
      "Effect": "Allow",
      "Action": [
        "sagemaker:CreateModel", "sagemaker:CreateEndpointConfig", "sagemaker:CreateEndpoint",
        "sagemaker:UpdateEndpoint", "sagemaker:DeleteModel", "sagemaker:DeleteEndpointConfig",
        "sagemaker:DeleteEndpoint", "sagemaker:DescribeEndpoint", "sagemaker:DescribeEndpointConfig",
        "sagemaker:InvokeEndpoint", "sagemaker:InvokeEndpointAsync"
      ],
      "Resource": "arn:aws:sagemaker:*:*:*artsmoker*"
    },
    {
      "Sid": "SageMakerList",
      "Effect": "Allow",
      "Action": ["sagemaker:ListModels", "sagemaker:ListEndpointConfigs"],
      "Resource": "*"
    },
    {
      "Sid": "CustomModelsRuntime",
      "Effect": "Allow",
      "Action": [
        "application-autoscaling:RegisterScalableTarget", "application-autoscaling:DeregisterScalableTarget",
        "application-autoscaling:DescribeScalableTargets", "application-autoscaling:PutScalingPolicy",
        "application-autoscaling:DeleteScalingPolicy", "application-autoscaling:DescribeScalingPolicies",
        "cloudwatch:PutMetricAlarm", "cloudwatch:DeleteAlarms", "cloudwatch:DescribeAlarms",
        "logs:DescribeLogStreams", "logs:FilterLogEvents", "logs:GetLogEvents", "logs:PutRetentionPolicy",
        "servicequotas:GetServiceQuota", "servicequotas:RequestServiceQuotaIncrease",
        "ecr:DescribeRepositories"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AutoScalingServiceLinkedRole",
      "Effect": "Allow",
      "Action": "iam:CreateServiceLinkedRole",
      "Resource": "arn:aws:iam::*:role/aws-service-role/sagemaker.application-autoscaling.amazonaws.com/AWSServiceRoleForApplicationAutoScaling_SageMakerEndpoint",
      "Condition": {"StringLike": {"iam:AWSServiceName": "sagemaker.application-autoscaling.amazonaws.com"}}
    },
    {
      "Sid": "SageMakerRoleManagement",
      "Effect": "Allow",
      "Action": ["iam:CreateRole", "iam:AttachRolePolicy", "iam:PutRolePolicy", "iam:GetRole", "iam:UpdateAssumeRolePolicy", "iam:PassRole"],
      "Resource": ["arn:aws:iam::*:role/ArtSmoker*"]
    },
    {
      "Sid": "SecretsManagerHFTokens",
      "Effect": "Allow",
      "Action": ["secretsmanager:CreateSecret", "secretsmanager:UpdateSecret", "secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret", "secretsmanager:DeleteSecret"],
      "Resource": "arn:aws:secretsmanager:*:*:secret:artsmoker/*"
    }
  ]
}'

# Adjúntela a su usuario IAM (sustituya YOUR_ACCOUNT_ID y YOUR_USERNAME)
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/ArtSmokerAccess
```

> [!NOTE]
> **Dos cosas que ajustar para tu cuenta:** (1) La declaración de S3 está acotada a buckets llamados `artsmoker-*` — si apuntas ArtSmoker a un bucket con otro nombre (Configuración de video permite elegir cualquier bucket existente), amplía ese `Resource` al ARN de tu bucket. (2) Los recursos de SageMaker que crea ArtSmoker se llaman `artsmoker-*`, así que el `Resource` acotado funciona tal cual; las acciones `sagemaker:List*` no admiten acotación por recurso y van en una declaración aparte.
>
> **¿Falta un permiso en tiempo de ejecución?** ArtSmoker supervisa cada llamada a AWS: si una es denegada, registra el `service:Operation` exacto que falló y muestra una notificación persistente en la aplicación indicando la acción que hay que añadir — una carencia de permisos nunca falla en silencio.

> [!TIP]
> **Para EC2/ECS/App Runner** — cree un rol IAM en lugar de adjuntarlo a un usuario. Consulte la sección [Despliegue en EC2](#43-ec2--cloud-deployment) para ver los comandos completos de creación del rol. No se necesitan claves de acceso — boto3 detecta automáticamente el rol desde el servicio de metadatos de la instancia.

> [!NOTE]
> Los modelos de Bedrock están disponibles por defecto en todas las regiones comerciales de AWS — no se necesita ningún paso manual de habilitación. En la primera invocación de un modelo de terceros (Anthropic, Stability AI), AWS inicia automáticamente una suscripción de marketplace en segundo plano (requiere los permisos `aws-marketplace` de arriba). Los modelos de Anthropic requieren completar una única vez el [formulario de primer uso (First Time Use)](https://console.aws.amazon.com/bedrock/home#/modelaccess).

### 📝 2.3 Opcional: herramientas de conversión SVG

La conversión SVG usa herramientas CLI externas (no paquetes de Python). Sin ellas, la salida SVG recurre a un envoltorio ráster-en-SVG basado en Pillow — funcional pero no una salida vectorial real.

| Herramienta | Propósito | macOS | Linux (Debian/Ubuntu) | Windows |
|------|---------|-------|-----------------------|---------|
| **vtracer** | SVG principal (trazado vectorial en color) | `pip install vtracer` o `cargo install vtracer` | `pip install vtracer` o `cargo install vtracer` | `pip install vtracer` o `cargo install vtracer` o [binarios precompilados](https://github.com/visioncortex/vtracer/releases) |
| **potrace** | SVG de respaldo (trazado monocromo) | `brew install potrace` | `sudo apt install potrace` | Descargar desde [potrace.sourceforge.net](http://potrace.sourceforge.net/#downloading) |

Verifique la instalación:

```bash
# Comprobar las herramientas de conversión SVG
which vtracer && echo "vtracer: OK" || echo "vtracer: not installed (optional)"
which potrace && echo "potrace: OK" || echo "potrace: not installed (optional)"
```

### 📝 2.4 Opcional: herramientas de miniaturas y metadatos de video

El Estudio de Video genera videos MP4 vía los modelos de video de Amazon Bedrock (p. ej., Luma AI Ray). Para extraer miniaturas (el primer cuadro como JPEG) y los metadatos del video (duración, resolución, FPS), **ffmpeg** y **ffprobe** deben estar instalados en la máquina que ejecuta el backend de ArtSmoker.

Sin ffmpeg:
- Los videos se siguen generando y reproduciendo correctamente (transmitidos desde S3 o descargados como MP4)
- Faltarán las miniaturas — la Galería y el Estudio de Video muestran un marcador de posición negro en lugar de una imagen de vista previa
- Los metadatos del video (duración, resolución) no se mostrarán

| Herramienta | Propósito | macOS | Linux (Debian/Ubuntu) | Windows |
|------|---------|-------|-----------------------|---------|
| **ffmpeg** | Extracción de miniaturas + metadatos de video | `brew install ffmpeg` | `sudo apt install ffmpeg` | Descargar desde [ffmpeg.org/download](https://ffmpeg.org/download.html) o `winget install ffmpeg` |

> [!NOTE]
> `ffprobe` viene incluido con ffmpeg — no se necesita una instalación aparte. ArtSmoker comprueba la presencia de ffmpeg en tiempo de ejecución y recurre a una alternativa con elegancia si no lo encuentra — la generación de video funciona de todos modos, simplemente no obtendrá miniaturas.

Verifique la instalación:

```bash
ffmpeg -version 2>&1 | head -1 && echo "ffmpeg: OK" || echo "ffmpeg: not installed (optional)"
ffprobe -version 2>&1 | head -1 && echo "ffprobe: OK" || echo "ffprobe: not installed (optional)"
```

<a id="installation"></a>

## 📌 3. Instalación

### 📝 3.1 macOS

```bash
git clone https://github.com/niravdd/ArtSmoker.git && cd ArtSmoker

# Opción A: con entorno virtual (recomendado)
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Opción B: sin entorno virtual (instalación en todo el sistema)
pip3 install -r backend/requirements.txt
```

> [!NOTE]
> En macOS, instale Python desde [python.org](https://www.python.org/downloads/) o mediante Homebrew. El `python3` predeterminado de Homebrew puede ser más reciente que 3.14 (p. ej., 3.15, que aún no es compatible) — si `python3 --version` muestra esa versión, ejecute `brew install python@3.14` y cree el venv con `python3.14 -m venv .venv`. El `python3` de las herramientas de línea de comandos de Xcode es demasiado antiguo.

### 📝 3.2 Linux (Debian/Ubuntu)

```bash
# Instale Python si es necesario
sudo apt update && sudo apt install python3 python3-pip python3-venv

git clone https://github.com/niravdd/ArtSmoker.git && cd ArtSmoker

# Opción A: con entorno virtual (recomendado)
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Opción B: sin entorno virtual
pip3 install --user -r backend/requirements.txt
```

> [!NOTE]
> En algunas distribuciones de Linux, `pip install` fuera de un venv requiere el flag `--user` o `--break-system-packages` (PEP 668). Usar un venv evita esto por completo.

> [!IMPORTANT]
> ArtSmoker necesita **Python 3.12, 3.13 o 3.14** — compruébelo con `python3 --version`. Si el `python3` de su distribución está fuera de ese rango (Ubuntu 24.04 incluye 3.12; Ubuntu 22.04 incluye 3.10, que es demasiado antiguo), instale una versión compatible junto a él y cree el venv con esa versión. En **Amazon Linux 2023**, el `python3` del sistema se mantiene en 3.9, pero hay versiones más recientes empaquetadas: `sudo dnf install -y python3.12` y luego `python3.12 -m venv .venv`.

<a id="install-windows"></a>

### 📝 3.3 Windows

```powershell
git clone https://github.com/niravdd/ArtSmoker.git
cd ArtSmoker

# Opción A: con entorno virtual (recomendado)
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt

# Opción B: sin entorno virtual
pip install -r backend\requirements.txt
```

> [!NOTE]
> En Windows, use `python` (no `python3`). Instale Python 3.12, 3.13 o 3.14 desde [python.org](https://www.python.org/downloads/) — marque "Add to PATH" durante la instalación. Si tiene varias versiones instaladas, elija una con el lanzador: `py -3.14 -m venv .venv`. Si PowerShell se niega a ejecutar `.venv\Scripts\activate` ("running scripts is disabled"), permítalo una vez con `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, o use `.venv\Scripts\activate.bat` desde cmd. El selector de fuentes del Estudio de Texto detecta fuentes desde `C:\Windows\Fonts` (la detección de fuentes del sistema es actualmente solo para macOS/Linux — los usuarios de Windows pueden usar fuentes personalizadas globales o específicas del estilo).

<a id="running"></a>

## 📌 4. Ejecución

### 📝 4.1 Desarrollo en solitario (todas las plataformas)

Un solo proceso con recarga automática al cambiar archivos — ideal para un desarrollador trabajando localmente:

```bash
# Con venv (actívelo primero)
source .venv/bin/activate          # macOS / Linux
.venv\Scripts\activate             # Windows

uvicorn backend.main:app --reload
```

```bash
# Sin venv (si se instaló en todo el sistema)
uvicorn backend.main:app --reload

# O si uvicorn no está en el PATH
python3 -m uvicorn backend.main:app --reload     # macOS / Linux
python -m uvicorn backend.main:app --reload       # Windows
```

Abra **http://localhost:8000** — el frontend lo sirve FastAPI, no se necesita un servidor web aparte.

Al iniciar, la consola muestra los resultados de la validación de credenciales de AWS. Si algo va mal, verá un recuadro de error claro. También puede consultar `http://localhost:8000/api/health` para ver el estado.

**Registros.** Además de la consola, ArtSmoker escribe un registro completo y **de solo anexado (append-only)** en `logs/artsmoker.log` **de forma predeterminada**, para que pueda revisar una sesión pasada después de que la app se haya cerrado. Cada ejecución se enmarca con un banner de sesión (hora de arranque, versión, pid, host) y se cierra con un banner de apagado (hora de detención, duración). Para cambiar la ruta o desactivarlo:

```bash
ARTSMOKER_LOG_FILE=/var/log/artsmoker/app.log uvicorn backend.main:app   # ruta personalizada
ARTSMOKER_LOG_TO_FILE=false uvicorn backend.main:app                      # desactivar el registro en archivo
```

(O establezca `log_to_file` / `log_file` en un `.env` local. Con varios workers, cada worker anexa al mismo archivo.)

**Auto-reinicio (opcional, todas las plataformas).** Todos los comandos anteriores funcionan tal cual. Para permitir además que ArtSmoker **se reinicie a sí mismo en el mismo lugar** — de modo que una auto-actualización, o el botón **Reiniciar ahora** dentro de la app, recargue el código nuevo sin que tengas que relanzarlo — inícialo bajo el supervisor multiplataforma integrado:

```bash
python -m backend.main            # añade --host / --port según sea necesario; Ctrl-C lo detiene limpiamente
```

Esto funciona en **cualquier sistema operativo, incluido Windows**. El supervisor ejecuta la app en un proceso hijo y lo vuelve a lanzar ante una solicitud de reinicio. (Ejecutarlo bajo gunicorn o un gestor de servicios como systemd ofrece el mismo reinicio en el mismo lugar — consulta §4.2 y §6.)

### 📝 4.2 Multiusuario / máquina de pruebas compartida / producción (macOS / Linux)

Para cualquier entorno con más de un usuario simultáneo — ya sea una máquina de desarrollo/pruebas compartida, preproducción o producción — use **gunicorn** con varios workers:

```bash
# Instale gunicorn (una sola vez, además de requirements.txt)
pip install gunicorn

# Ejecute con gunicorn (varios workers, admite usuarios simultáneos)
gunicorn backend.main:app \
  -w 2 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 300
```

| Opción | Propósito |
|------|---------|
| `-w 2` | 2 procesos worker (auméntelo para cargas más pesadas) |
| `-k uvicorn.workers.UvicornWorker` | Usar la clase de worker asíncrono de uvicorn |
| `--bind 0.0.0.0:8000` | Escuchar en todas las interfaces (no solo localhost) |
| `--timeout 300` | Timeout de 5 minutos para generaciones por lotes grandes con reintentos |

> [!TIP]
> **gunicorn** es solo para Linux/macOS. En Windows, use `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2` para el servicio con varios workers.

> [!NOTE]
> **Seguro para usuarios simultáneos.** Todas las escrituras del servidor — metadatos de imagen/versión y los registros de modelos y prompts — se escriben de forma atómica y serializada **entre procesos worker** (bloqueos de archivo POSIX), de modo que las ediciones simultáneas de varios colaboradores en una máquina compartida nunca corrompen un archivo ni pierden una actualización. El registro en archivo funciona igual entre workers — cada uno anexa al único `logs/artsmoker.log`.

<a id="43-ec2--cloud-deployment"></a>

### 📝 4.3 Despliegue en EC2 / la nube

Recomendado: **t3.small** (~$15/mes) para 1-2 usuarios simultáneos.

**Paso 1: Cree un rol IAM para la instancia EC2** (ejecute desde su máquina local):

```bash
# Cree el rol IAM con la política de confianza de EC2
aws iam create-role --role-name ArtSmokerEC2Role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Adjunte la política de ArtSmoker (use la política acotada de la sección 2.2 o la política administrada)
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# Cree un perfil de instancia y adjúntele el rol
aws iam create-instance-profile --instance-profile-name ArtSmokerEC2Profile
aws iam add-role-to-instance-profile \
  --instance-profile-name ArtSmokerEC2Profile \
  --role-name ArtSmokerEC2Role
```

**Paso 2: Lance una instancia EC2** (o adjunte el profile a una existente):

```bash
# Adjúntelo a una instancia existente en ejecución
aws ec2 associate-iam-instance-profile \
  --instance-id i-YOUR_INSTANCE_ID \
  --iam-instance-profile Name=ArtSmokerEC2Profile
```

**Paso 3: Instale y ejecute en la instancia** (conéctese por SSH a la instancia):

```bash
# Instalación (una sola vez)
sudo yum install -y python3 python3-pip git   # Amazon Linux
# sudo apt install -y python3 python3-pip python3-venv git   # Ubuntu

git clone https://github.com/niravdd/ArtSmoker.git && cd ArtSmoker
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install gunicorn

# Opcional: instale ffmpeg para las miniaturas de video
sudo yum install -y ffmpeg   # Amazon Linux
# sudo apt install -y ffmpeg   # Ubuntu
```

**Paso 4: Ejecute como un servicio systemd** (persistente, se reinicia automáticamente):

```bash
# Cree el archivo del servicio
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

# Habilite e inicie el servicio
sudo systemctl daemon-reload
sudo systemctl enable artsmoker
sudo systemctl start artsmoker

# Verifique que está en ejecución
sudo systemctl status artsmoker

# Ver los registros
sudo journalctl -u artsmoker -f
```

Abra **http://YOUR_INSTANCE_IP:8000** — asegúrese de que el grupo de seguridad de su EC2 permita tráfico entrante TCP 8000.

Si accede a ArtSmoker mediante un nombre DNS en lugar de una dirección IP (p. ej., `artsmoker.example.com`), añada ese nombre: `ARTSMOKER_ALLOWED_HOSTS=artsmoker.example.com`. ArtSmoker rechaza los nombres de host desconocidos, lo que lo protege contra el DNS rebinding.

### 📝 4.4 Primeros pasos tras la configuración

Después de que ArtSmoker esté en ejecución, complete estos pasos para obtener los mejores resultados:

**1. Sincronice modelos desde AWS** — Abra **Configuración del modelo** (icono de engranaje en cualquier estudio) → haga clic en **Sincronizar desde AWS**. Esto descubre todos los modelos de imagen, video y chat disponibles en todas las regiones de Bedrock. Tarda 30-60 segundos. Solo se necesita una vez, o cuando AWS añade nuevos modelos.

**2. Revise y personalice las plantillas de prompt** — Esta es la configuración de mayor impacto que puede realizar. Abra la pestaña **Configuración del modelo → Plantillas de Prompt**. ArtSmoker usa 28 prompts de directivas editables que controlan cómo se comporta la IA:

| Plantilla | Qué controla |
|----------|-----------------|
| Refinamiento del prompt | Cómo sus descripciones de texto se convierten en prompts detallados de generación de imágenes |
| Opciones creativas | Cómo se generan múltiples opciones creativas a partir de una sola idea |
| Análisis de estilo | Cómo se analizan las imágenes de referencia para aprender su estilo artístico |
| Preevaluación / Reescritura | Qué tan estricto es el sistema de verificación previa y reescritura |
| Mejora del prompt de video | Cómo se enriquecen los prompts de video con movimientos de cámara e iluminación |
| Estudio de Texto: diseño del texto | Cómo el Estudio de Texto diseña la posición del texto en las imágenes |

Cada plantilla puede:
- **Editarse directamente** — modifique las instrucciones para adaptarlas a las necesidades de su equipo
- **Mejorarse con IA** — seleccione cualquier modelo LLM, opcionalmente añada instrucciones (p. ej. "optimizar para pixel art") y haga clic en "Mejorar con IA". Revise la sugerencia, luego Aceptar o Descartar
- **Restablecerse al valor predeterminado** — restaure el original en cualquier momento

Las plantillas están organizadas por estudio (Estudio de Imagen, Biblioteca de Estilos, Seguridad de contenido, Estudio de Video, Estudio de Texto, Estudio de Chat, Traducción) con descripciones amigables de lo que controla cada una.

**Seguridad de variables:** las plantillas usan variables entre `{llaves}` (p. ej. `{user_prompt}`, `{model_name}`) que se sustituyen en tiempo de ejecución. Si por accidente elimina una variable requerida, ArtSmoker:
1. Bloqueará el guardado y mostrará qué variables faltan
2. Ofrecerá **"Corregir y guardar"** — un LLM inserta automáticamente las variables faltantes de vuelta en su texto editado en los lugares correctos
3. Verificará la corrección antes de guardar

Las plantillas se cargan desde `backend/prompt_templates.json` — la fuente de la verdad en tiempo de ejecución. Sus ediciones se guardan en `backend/prompt_templates.user.json` (ignorado por git) y se superponen encima, de modo que una actualización o un `git pull` nunca sobrescribe sus personalizaciones. Si el JSON falta o está corrupto, o si llega una nueva plantilla en el código, se autorregenera: la semilla incorporada en el código regenera/rellena solo las entradas faltantes, sin sobrescribir nunca las existentes.

> [!TIP]
> Empiece revisando las plantillas **Refinamiento del prompt** y **Opciones creativas**. Son las que más impacto tienen en la calidad de la salida. Si su equipo se especializa en un estilo artístico particular (p. ej. pixel art, acuarela, isométrico), añada esas preferencias directamente en las plantillas para que cada generación se beneficie.

**3. Configure un perfil de estilo** (opcional) — Vaya a **Biblioteca de Estilos**, cree un nuevo estilo, suba imágenes de referencia y haga clic en **Analizar estilo**. Esto le enseña a ArtSmoker su identidad visual.

**4. Elija su idioma** — Haga clic en un botón de idioma en la barra de navegación (EN | 日 | 中 | 한 | हिं | РУ | FR | ES | DE) si prefiere una interfaz que no esté en inglés.

## 📌 5. Arquitectura

```
┌─────────────────────────────────────────────────────┐
│  Navegador (SPA)                                    │
│  Vanilla JS + Tailwind CSS                          │
└──────────────────────────┬──────────────────────────┘
                           │ HTTP / SSE
                           ▼
┌─────────────────────────────────────────────────────┐
│  Backend FastAPI (Python)                           │
│                                                     │
│  /api/styles       CRUD de estilos + importación    │
│  /api/generate     Generación de dos niveles        │
│  /api/type-studio  Superposición + fuentes          │
│  /api/video        Generación de video + trabajos   │
│  /api/chat         Chat LLM + sesiones              │
│  /api/gallery      Exploración + exportación        │
│  /api/browse       Explorador de archivos/S3        │
│  /api/admin        Registro de modelos + plantillas │
│  /api/refine-prompt Prompt + traducción             │
│  /api/transcribe   Voz a texto                      │
└─────────────┬─────────────────────────────┬─────────┘
              │                             │
              ▼                             ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│  us-west-2               │  │  us-east-1               │
│                          │  │                          │
│  LLMs (p. ej., Claude)   │  │  Transcripción de voz    │
│  Generación de imágenes  │  │  (Nova Sonic)            │
│  Edición de imágenes     │  │                          │
│    p. ej., Stability AI  │  │                          │
│  Video (p. ej., Luma)    │  │                          │
└─────────────┬────────────┘  └──────────────────────────┘ ... (otras regiones)
              │
              ▼
┌──────────────────────────┐
│  Almacenamiento local    │
│  data/styles/            │
│  data/images/            │
│  data/video/             │
│  data/chat/              │
└──────────────────────────┘
```

Las Regiones mostradas son las predeterminadas; la sincronización fija cada modelo en una Región donde AWS lo ofrece. Los nombres de modelos son ejemplos — consulte [Sobre los nombres de modelos](#about-model-names).

## 📌 6. Uso

### 📝 6.1 Descripción general del flujo de trabajo

```
                            ┌─────────────────┐
                            │   ArtSmoker     │
                            └────────┬────────┘
                                     │
        ┌──────────────┼─────────────┼─────────────┼─────────────┐
        │              │             │             │             │
        ▼              ▼             ▼             ▼             ▼
  ┌────────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
  │ Biblioteca │ │  Estudio  │ │  Estudio  │ │  Estudio  │ │  Estudio  │
  │ de Estilos │ │ de Imagen │ │ de Video  │ │ de Texto  │ │  de Chat  │
  │            │ │           │ │           │ │           │ │           │
  │ Subir      │ │ Generar   │ │ Generar   │ │ Añadir    │ │ Chat LLM  │
  │ Analizar   │ │ imágenes  │ │ videos    │ │ texto a   │ │ multi-    │
  │ Definir    │ │           │ │           │ │ imágenes  │ │ modelo    │
  │ fuentes    │ │           │ │           │ │           │ │           │
  └──────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └───────────┘
         │             │             │             │
         │    ┌────────┴─────────────┴────────┐    │
         │    │  ¿Estilo elegido? (opcional)  │    │
         └───►│  Mejora el resultado          │◄───┘
              └────────────────┬──────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       Galería       │
                    │                     │
                    │ Explorar todo       │
                    │ Buscar/filtrar      │
                    │ Elegir y borrar     │
                    └──────────┬──────────┘
                               │
               ┌───────────────┼────────────────┐
               │               │                │
               ▼               ▼                ▼
        ┌─────────────┐ ┌─────────────┐ ┌───────────────┐
        │ Descargar   │ │ Recargar en │ │ Agregar texto │
        │ PNG / SVG   │ │ Estudio de  │ │ en Estudio de │
        │             │ │ Imagen      │ │ Texto         │
        │             │ │ (refinar y  │ │ (superponer   │
        │             │ │  regenerar) │ │  texto)       │
        └─────────────┘ └─────────────┘ └───────────────┘
```

**Tres puntos de entrada, una galería unificada:**

- **Empiece con un estilo** — suba arte de referencia en la Biblioteca de Estilos, deje que la IA lo analice y luego genere en cualquier estudio. El estilo guía toda la salida.
- **Empiece sin un estilo** — vaya directamente al Estudio de Imagen, al Estudio de Video o al Estudio de Texto. La IA usa su mejor criterio.
- **Empiece desde la Galería** — elija cualquier recurso generado previamente y recárguelo en el estudio apropiado para refinarlo, añádale texto, reproduzca un video o descárguelo como PNG/SVG/MP4.

Todos los recursos generados (imágenes, videos, superposiciones de texto, texto independiente) van a parar a la Galería unificada. Nada se sobrescribe — cada generación crea nuevos recursos.

### 📝 6.2 Pipeline de generación

```
Prompt del usuario: "edificio de hospital"
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 1. Composición del prompt        LLM rápido (1 opción) │
│    (botón opcional "Generar       o LLM complejo (2-5) │
│    Prompt Mejorado") + estilo + tipo de recurso        │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 2. Prueba canario                                      │
│    Una sola imagen prueba la moderación                │
│    ¿Pasa? ──► Lote completo                            │
│    ¿Falla? ──► Cambio de modelo                        │
│                o sugerencia de reescritura             │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 3. Generación paralela de imágenes                     │
│    Hasta 5 opciones × 5 variaciones = 25 imágenes      │
│    ThreadPool (3-5 hilos)                              │
│    Reintento con backoff exponencial (3 intentos)      │
│    Progreso transmitido por SSE al navegador           │
│    Cancelación cooperativa si la moderación bloquea    │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 4. Posprocesamiento (por imagen, opcional)             │
│    Eliminar fondo ──► Stability AI ($0.07/img)         │
│    Escalar ──► Stability AI Creative Upscale ($0.60)   │
│    SVG ──► vtracer / potrace / Pillow (gratis, local)  │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 5. Almacenamiento                                      │
│    data/images/{asset_id}/                             │
│    ├── asset.png (fondo transparente)                  │
│    ├── asset.svg (opcional)                            │
│    └── metadata.json (linaje completo del prompt)      │
│    Nombres inteligentes: prompt-slug_opt1_var2.png     │
└────────────────────────────────────────────────────────┘
```

### 📝 6.3 Flujo de moderación de contenido

```
El usuario hace clic en Generar
         │
         ▼
┌─────────────────────────┐
│ ¿Verificación previa    │
│ activada? (interruptor  │
│ «Verificación previa    │
│ del prompt», activado   │
│ por defecto)            │
└───┬────────────────┬────┘
   Sí               No
    │                │
    ▼                │
┌─────────────┐      │
│ LLM rápido  │      │
│ revisa el   │      │
│ prompt:     │      │
│ ¿problemas? │      │
└───┬──────┬──┘      │
   Sí      No        │
    │      └────────►│
    ▼                │
┌──────────────────┐ │
│ Diálogo índigo:  │ │
│ • Cambiar modelo │ │
│ • Reescribir     │ │
│ • Continuar      │ │
│ • Cancelar       │ │
└──┬───────────────┘ │
   │◄────────────────┘
   ▼
┌──────────────────────────────┐
│ Prueba canario               │
│ (1 imagen al modelo)         │
└───┬──────────────────────┬───┘
Bloqueado                Pasa
    │                      │
    ▼                      ▼
┌──────────────────┐ ┌────────────┐
│ Probar otros     │ │ Se ejecuta │
│ modelos:         │ │ el lote    │
│ ¿funciona?       │ │ completo   │
└───┬───────────┬──┘ └────────────┘
   Sí           No
    │           │
    ▼           ▼
Diálogo        Diálogo ámbar
esmeralda      (reescritura →
(cambiar o      área del
 reescribir)    prompt mejorado)
```

### 📝 6.4 Estudio de Imagen (Generar recursos)

El Estudio de Imagen usa un flujo de trabajo guiado de 3 pasos:

**Paso 1 — Describa su idea**: Escriba un prompt en el área de texto. El texto de marcador de posición muestra un ejemplo realista que cambia según el Tipo de recurso seleccionado (p. ej. "Una joven guerrera con una armadura plateada ornamentada, el largo cabello oscuro trenzado, empuñando una espada brillante, de pie al borde de un acantilado al atardecer..." para Personaje, o "Un jardín japonés brumoso al amanecer, linternas de piedra a lo largo de un sendero sinuoso entre rocas cubiertas de musgo, pétalos de cerezo flotando en el aire quieto..." para Entorno). Use la entrada de voz (botón de micrófono) para dictar en lugar de escribir.

**Paso 2 — Diseñador de prompts** *(opcional)*: Haga clic en **🎨 Diseñador de prompts** para descomponer su prompt en componentes visuales estructurados. La IA analiza su prompt y lo divide en secciones editables:

- **Sujeto** — descripción del personaje, ropa, accesorios, pose, expresión
- **Escena** — entorno, fondo, props, hora del día
- **Composición** — ángulo de cámara, encuadre, profundidad de campo
- **Iluminación** — luz principal, luz de relleno/borde, ambiente
- **Estilo y Colores** — estilo artístico, nivel de calidad y una paleta de colores con nombre e indicadores hexadecimales

Cada campo se puede editar individualmente. **Generar Prompt Mejorado** recompone sus ediciones en un prompt recompuesto plano (mostrado como solo lectura en el Paso 2) y luego genera automáticamente el prompt mejorado del Paso 3.

Antes de que se abra el Diseñador de prompts, se ejecuta una **clasificación del tipo de recurso por IA** — si su prompt describe una escena pero seleccionó "Recurso de juego", un diálogo sugiere cambiar a "Entorno" o "Personaje". Esto garantiza que el Diseñador de prompts descomponga con el contexto correcto.

**Paso 3 — Vista previa del prompt mejorado** *(opcional)*: Haga clic en **Generar Prompt Mejorado** para ver el prompt optimizado para el modelo antes de generar. La IA toma el prompt recompuesto del Paso 2 y lo mejora con orientación específica del modelo (anatomía, materiales, iluminación, estructura del prompt). Puede editar el prompt mejorado antes de generar. Si usó el Diseñador de prompts en el Paso 2, este se rellena automáticamente.

**Pipeline de prompt**: Prompt del usuario → Descomponer → Recomponer (`recomposed_prompt`) → Mejorar con orientación del modelo (`enhanced_prompt`) → Modelo de imagen. Para múltiples opciones, el paso de mejora genera N interpretaciones distintas a partir de la misma base recompuesta. Los tres niveles se almacenan en los metadatos.

**Generar**: Haga clic en Generar en cualquier momento — los Pasos 2 y 3 son opcionales. Si los omite, Generar descompone, recompone y mejora su prompt automáticamente antes de continuar. **Verificación previa del prompt** (activado por defecto) verifica el prompt en busca de problemas de moderación antes de la generación.

**Controles adicionales:**
- **Tipo de recurso** — seleccione en la barra lateral. Cambia el marcador de posición del prompt y afecta a cómo la IA interpreta su prompt. El sistema sugiere cambiar si detecta una discrepancia.
- **Estilo artístico** — seleccione un perfil de estilo para guiar la generación con su identidad visual.
- **Dimensiones, Opciones, Variaciones** — configure el tamaño de salida y cuántos conceptos creativos generar.
- **Posprocesamiento** — Eliminar fondo, Escalar (Creativo), conversión SVG (aplicados tras la generación).
- **Declaración de PI** — afirme la propiedad o la licencia para la compatibilidad con modelos estrictos.
- **Configuración del modelo** — ver/editar la configuración de modelos, descubrir los modelos de Amazon Bedrock disponibles.

El progreso de la generación se transmite en tiempo real vía SSE — la UI muestra qué imagen se está generando (p. ej. "Generando imágenes... 12/25"), el tiempo transcurrido y la etapa actual del pipeline. Si la API está limitada, verá "API limitada — esperando para reintentar..." con el retraso, luego "Reintentando... (intento 2/3)" — cada imagen se reintenta hasta 3 veces con backoff exponencial para que los lotes grandes no pierdan variantes por limitaciones transitorias de velocidad.

Los resultados generados sobreviven a la navegación — cambiar de pestaña y volver conserva el estado del DOM del Estudio de Imagen. Solo el botón de reinicio lo borra.

**Moderación inteligente de contenido**: Cuando su prompt es bloqueado por los filtros de moderación de contenido de un modelo, ArtSmoker lo maneja progresivamente a través de tres diálogos codificados por color:

- **Índigo (Verificación previa)** — antes de la generación, una IA verifica previamente su prompt contra la sensibilidad conocida del modelo seleccionado. Si se detectan problemas, ve las preocupaciones específicas y puede: cambiar a un modelo recomendado, **reescribir el prompt** para el modelo actual, continuar de todos modos o cancelar.
- **Esmeralda (Cambio de modelo)** — tras un bloqueo de generación, si un modelo alternativo acepta su prompt tal cual, ArtSmoker muestra qué modelo funciona y por qué. Un clic para cambiar. Registro completo de intentos disponible ("Ver N pruebas de modelo").
- **Ámbar (Reescritura)** — cuando todos los modelos rechazan, se ofrece una reescritura generada por IA en un área de texto editable con los problemas específicos listados. Una insignia de verificado/no verificado indica si la reescritura pasó la prueba canario.

**Comportamiento de la reescritura de prompts**: En los tres diálogos, elegir «Reescribir» nunca sobrescribe su prompt original. La versión reescrita aparece en el **área del prompt mejorado** debajo de su texto original, con una advertencia ámbar persistente: *"Esta reescritura es un intento de hacer el prompt compatible — sigue estando sujeto a la propia moderación del modelo y puede ser rechazado."* Usted revisa y edita el prompt mejorado, luego hace clic en Generar cuando esté satisfecho. Su prompt original siempre se conserva en el historial y los metadatos.

Los disparadores comunes incluyen nombres de IP con derechos de autor y referencias a personajes, lenguaje de violencia/armas y referencias a contenido para adultos. Consejo: el botón **"Generar Prompt Mejorado"** a menudo produce prompts que pasan la moderación de forma natural, ya que la IA reformula en términos descriptivos.

**Prueba canario inteligente**: Antes de generar el lote completo, ArtSmoker envía una única solicitud de imagen «canario» para probar el prompt contra los filtros de moderación del modelo. Si la imagen canario es bloqueada, el lote se detiene de inmediato (1 llamada a la API desperdiciada en lugar de N×M×3). Si la imagen canario pasa, los trabajos restantes se ejecutan en paralelo con cancelación cooperativa — si algún trabajo encuentra un bloqueo de moderación, el resto omite sus llamadas a la API automáticamente.

### 📝 6.5 Usar un perfil de estilo

1. Vaya a la pestaña **Biblioteca de Estilos**.
2. Haga clic en **Crear nuevo estilo** — introduzca un nombre y, opcionalmente, añada pistas de generación. En el modal de creación, use la sección **"Importar referencias desde"** con los botones de exploración **Local** y **S3** para seleccionar un directorio o ruta de bucket de origen. La exploración abre un modal de explorador de archivos/directorios del lado del servidor (un clic selecciona un elemento, doble clic navega dentro de los directorios). Las referencias importadas se analizan automáticamente al crearse.
3. Las importaciones de directorios locales escanean **recursivamente** todos los subdirectorios en busca de imágenes (.png, .jpg, .jpeg, .gif, .bmp, .webp, .tiff, .tif, .tga, .ico, .svg) y modelos 3D (.glb, .gltf). Los archivos de imagen se enlazan con **enlaces simbólicos relativos** (sin duplicación, portables entre máquinas). A los archivos de modelo 3D (.glb/.gltf) se les **extraen automáticamente** sus texturas incrustadas — se manejan URIs de datos base64, fragmentos de búfer binario y referencias de texturas externas. Las texturas extraídas se guardan como copias (con el nombre del modelo como prefijo para evitar colisiones). Las importaciones de S3 se listan recursivamente con paginación y **descargan** los archivos localmente. Se importan hasta **100 imágenes de referencia** por estilo. Las extensiones compatibles están centralizadas en `backend/config.py` (`IMAGE_EXTENSIONS` y `MODEL_EXTENSIONS_WITH_TEXTURES`).
4. **Análisis de cohesión en dos fases**: La Fase 1 envía 8 imágenes al LLM rápido para determinar el nivel de cohesión (alto/medio/bajo) — alto significa estilo unificado, medio significa estructura compartida con temas diferentes, bajo significa estilos diversos. La Fase 2 alimenta la evaluación de cohesión al LLM complejo junto con las imágenes de referencia, guiándolo para analizar de forma apropiada según el tipo de colección. Cuando un estilo tiene más de 20 referencias, el analizador selecciona un subconjunto representativo y diverso de 20 para la llamada de visión de Opus — garantizando cobertura entre grupos de nombres de archivo y diversidad de tamaños de archivo. Se le indica a la IA cuántas imágenes totales existen frente a cuántas está viendo. El prompt de análisis está diseñado específicamente para recursos de juego sobre fondos transparentes — pide detalles de renderizado específicos del material, sistema de proporciones y especificidades de sombra/iluminación. Extrae 9 atributos de estilo, incluyendo `materials` (cómo se renderizan piedra, madera, metal) y `detail_level` (qué detalles de superficie son visibles frente a simplificados). Las pistas de generación se expanden a 200 palabras que cubren 8 dimensiones: perspectiva, renderizado, materiales, paleta de colores, proporciones, tratamiento de bordes, sombra/iluminación, nivel de detalle y fondo — lo bastante específicas como para que los recursos generados se fundan visualmente con las referencias existentes.
5. En la vista de detalle del estilo, use **"Importar y analizar"** para añadir más referencias y disparar el análisis en un solo paso. También se admite la carga por arrastrar y soltar, y **se vuelve a analizar automáticamente** cuando se añaden nuevas imágenes.
6. **"Reanalizar estilo"** aparece tras el análisis inicial, permitiéndole volver a ejecutar el análisis manualmente en cualquier momento.
7. **Las pistas de generación** forman parte del contexto de análisis — la IA recibe tanto las imágenes de referencia como sus pistas como "Orientación del artista" al analizar, de modo que el perfil de estilo comprende la intención, no solo la apariencia visual. Editar las pistas de generación también dispara un **reanálisis automático**.
8. De vuelta en el **Estudio de Imagen**, seleccione su estilo del desplegable — todos los recursos generados coincidirán con su identidad visual (paleta, perspectiva, estilo de renderizado, ambiente).

### 📝 6.6 Flujo de análisis de estilo

```
┌───────────────────────────────────────────────────┐
│ Crear / importar estilo                           │
│ (imágenes de referencia subidas o importadas)     │
└─────────────────────────┬─────────────────────────┘
                          │
                          ▼
┌───────────────────────────────────────────────────┐
│ Fase 1: Comprobación de cohesión                  │
│ LLM rápido — 8 imágenes — ~$0.01                  │
│ Determina: alta / media / baja                    │
│   alta  = estilo unificado                        │
│   media = estructura compartida, temas distintos  │
│   baja  = colección diversa                       │
└─────────────────────────┬─────────────────────────┘
                          │
                          ▼
┌───────────────────────────────────────────────────┐
│ Fase 2: Análisis completo                         │
│ LLM complejo — hasta 20 imágenes                  │
│ Guiado por el nivel de cohesión                   │
│ + Orientación del artista (pistas del usuario)    │
│ Extrae 9 atributos de estilo                      │
└─────────────────────────┬─────────────────────────┘
                          │
                          ▼
┌───────────────────────────────────────────────────┐
│ Fase 3: Generación de pistas                      │
│ LLM rápido — pistas de 200 palabras               │
│ 8 dimensiones: perspectiva, renderizado,          │
│ materiales, paleta, proporciones, bordes,         │
│ sombra/iluminación, nivel de detalle              │
└─────────────────────────┬─────────────────────────┘
                          │
                          ▼
┌───────────────────────────────────────────────────┐
│ Guardado en profile.json                          │
│ ~$0.14 en total por análisis de estilo            │
│ Se usa en todas las generaciones futuras          │
└───────────────────────────────────────────────────┘
```

### 📝 6.7 Estudio de Texto

Añada texto a imágenes o genere recursos de texto independientes con tipografía diseñada por IA.

- **Dos modos**: "Sobre imagen" compone texto sobre una imagen de la galería; "Independiente" renderiza texto sobre un fondo transparente.
- **Editor de texto multilínea** con selección de fuente por línea, controles de posicionamiento y **entrada de voz** (botón de micrófono por línea — dicte texto vía la transcripción de Nova Sonic).
- **Diseños diseñados por IA** — la IA sugiere colores, tamaños, posiciones y efectos (sombra, contorno, resplandor). Solicite de 1 a 5 opciones de diseño para diferentes direcciones creativas. El **modelo LLM** usado para el diseño es configurable (LLM complejo para la mejor calidad, LLM rápido para mayor economía) — se lee de las categorías del registro.
- **Selector de fuentes con vista previa en vivo** — fuentes de estilo, 8 fuentes incluidas (Roboto, Open Sans, Lato, Montserrat, Playfair Display, Oswald, Raleway, Source Code Pro), fuentes del sistema y **fuentes detectadas del lado del cliente** (vía la Local Font Access API o el sondeo de canvas).
- **Preprocesamiento / Posprocesamiento** — el mismo flujo de trabajo que el Estudio de Imagen, con un botón "Aplicar" para el postprocesamiento. La conversión SVG está activada por defecto.
- **Clic para hacer zoom** — al hacer clic en la vista previa del resultado se abre el visor de recursos con zoom/panorámica completos, metadatos, descarga y herramientas de edición de imágenes.
- Los resultados se guardan como nuevos recursos de la galería (los originales nunca se sobrescriben).

### 📝 6.8 Galería

- **Vista unificada** de todas las imágenes y videos generados en un **diseño en mosaico (masonry)** (cada recurso mostrado en su proporción real — vertical, cuadrada u horizontal — nunca recortado al centro), con un **filtro Medio** (Todos / Arte 2D / Modelos 3D / Video). El filtro **Modelos 3D** muestra solo los recursos que ya tienen un modelo 3D generado, y esos recursos llevan una **insignia 3D** en su tarjeta.
- **Barra de búsqueda** para un filtrado instantáneo en todos los recursos (prompts, estilos, modelos).
- **Multiselección** con casillas de verificación para eliminación masiva (maneja recursos tanto de imagen como de video). Las eliminaciones tienen **conciencia de lote** — los hermanos supervivientes registran cuántas variantes se eliminaron, de modo que al recargar un lote parcial en el Estudio de Imagen se muestra "X de Y imágenes restantes (Z eliminadas de la galería)".
- Los recursos se cargan de inmediato con una caché de metadatos en memoria. Ordenados por más recientes primero.
- Soporte de paginación (limit/offset) para colecciones grandes.
- La Galería se actualiza automáticamente cuando vuelve a ella, y después de que se complete cualquier edición o generación de video.
- **Las tarjetas de video** muestran una miniatura con una superposición de reproducción, una insignia VIDEO y un indicador de duración. Haga clic para abrir el modal del reproductor de video.
- **Botones de acción contextuales** por recurso según el tipo: **"Estudio de Imagen"** (índigo) para recargar en el Estudio de Imagen, **"Agregar texto"** (esmeralda) para abrir en el Estudio de Texto, **"Editar en Estudio de Texto"** (morado) para recursos de texto.
- Haga clic en cualquier imagen para abrir el modal del **visor de recursos** con:
  - **Zoom/panorámica** — rueda del ratón para hacer zoom, arrastrar para desplazar, botones Ajustar/1:1 con resaltado del modo activo.
  - **Pestaña Editar** — inpaint, borrar, outpaint, búsqueda y reemplazo, o recolorear la imagen directamente. Se ofrecen dos tipos de editor por modo: **basado en máscara** (p. ej., Stability) — pinte una máscara con la herramienta de pincel, introduzca un prompt y aplique; y **editores por instrucciones sin máscara** (p. ej., Qwen-Image-Edit, cuando está desplegado) — simplemente describa el cambio con palabras, sin necesidad de máscara. Los controles del pincel se ocultan automáticamente para un modelo sin máscara. Elija el modelo de edición y aplique — cada edición crea una nueva versión, y todas las versiones anteriores se conservan y pueden consultarse.
  - **Anterior / Siguiente** — botones de flecha y teclas izquierda/derecha para navegar por la lista sin cerrar el visor.
  - **Metadatos completos**: prompt original, prompt mejorado por IA, prompt de generación, prompt negativo, estilo, tipo de recurso, modelo de imagen (nombres amigables), dimensiones, semilla, ID de lote, índice de opción/variación, estado de la declaración de PI, nombre de archivo y fecha de creación.
- **Instantánea de estilo**: Cada recurso almacena una instantánea del estilo usado en el momento de la generación (nombre, descripción, pistas, análisis). Si el estilo original se elimina posteriormente, el recurso conserva todo el contexto. Compatible hacia atrás — los recursos más antiguos sin instantáneas se muestran con normalidad.

### 📝 6.9 Entrada de voz

Haga clic en el botón de micrófono junto al editor de prompt para dictar su prompt. El audio se envía a Nova Sonic para su transcripción.

> [!NOTE]
> La transcripción de voz requiere la API de streaming bidireccional de Nova Sonic, que depende de una versión compatible de boto3 y del acceso al modelo habilitado en us-east-1. Si la API de streaming no está disponible, el servicio devuelve un acuse de recibo de marcador de posición. La transcripción completa en tiempo real funciona cuando el streaming de Nova Sonic está correctamente configurado.

### 📝 6.10 Preservación del estado de las vistas

Orden de navegación: **Biblioteca de Estilos → Estudio de Imagen → Estudio de Texto → Estudio de Video → Galería**. Cambiar entre vistas preserva el estado del DOM de cada vista. Los resultados generados, las entradas de formulario y las posiciones de desplazamiento sobreviven a la navegación. El botón ámbar de reinicio en el Estudio de Imagen y el Estudio de Video es la única forma de borrar su estado.

### 📝 6.11 Gestión de modelos

Toda la configuración de modelos de IA está centralizada en `backend/model_registry.json` — la única fuente de la verdad. Modelos, regiones, precios, niveles de calidad y plantillas de formato se almacenan todos aquí y se gestionan a través de la UI o la API:

- Haga clic en **"Configuración del modelo"** en la barra lateral de cualquier estudio para abrir el modal de administración — se abre en la pestaña relevante para ese estudio.
- **9 pestañas** organizadas por estudio:
  - **Estudio de Imagen** — Modelos de generación de imágenes (p. ej., SD 3.5 Large, Stable Image Ultra, Stable Image Core, además de FLUX, HunyuanImage, Qwen-Image autoalojados), regiones, niveles de calidad, límites de prompt, estrictez de moderación
  - **Estudio de Video** — Modelos de video (p. ej., Luma Ray), configuración del bucket de S3, regiones, precios
  - **Estudio de Chat** — Modelos de chat/LLM descubiertos, ventanas de contexto, capacidad de visión, precio por cada 1K tokens
  - **Estudio de Texto** — Modelo LLM para la generación de disposición de texto (LLM complejo o rápido)
  - **Estudio Compartido** — Categorías LLM entre estudios (LLM rápido, LLM complejo, LLM de respaldo, Transcripción de voz), modelos de postprocesamiento (Eliminar fondo, Escalar)
  - **Modelos Personalizados** — el catálogo de modelos autoalojados: desplegar, monitorizar y desmantelar endpoints de SageMaker (ver sección 6.12)
  - **Plantillas de Prompt** — 28 prompts de directivas LLM editables organizados en 6 secciones de flujo de trabajo (ver sección 4.4)
  - **JSON del registro** — Editor JSON en crudo para el registro completo de modelos
  - **Mantenimiento** — estado de las herramientas gestionadas (p. ej. el Blender sin interfaz usado para exportar FBX/USD: ruta, versión, actualización bajo demanda)
- Todas las secciones son **plegables** con interruptores **Mostrar todo / Ocultar todo** para una navegación rápida.
- Las categorías LLM y el postprocesamiento usan **selectores de modelo desplegables** (poblados a partir de los modelos descubiertos) — no campos de texto en crudo.
- **Sincronizar desde AWS**: Escanea todas las regiones de AWS compatibles con Bedrock (descubiertas dinámicamente), autorregistra nuevos modelos de imagen, video y **chat**, actualiza la disponibilidad regional, obtiene los precios por modelo de la AWS Pricing API y deshabilita los modelos que ya no están disponibles. Una **superposición de progreso en vivo** transmite cada región a medida que se escanea. Esta es la **única** acción que llama a las API de descubrimiento de AWS — todas las demás operaciones leen del registro en caché.
- **Siempre en el Claude más nuevo**: Cada sincronización rota automáticamente su **LLM rápido** al Claude Sonnet más nuevo y su **LLM complejo** al Claude Opus más nuevo disponible en su cuenta, de modo que nunca se queda varado en un modelo obsoleto — sin necesidad de configuración manual. Si elige manualmente un modelo específico para una categoría, queda **fijado** y la rotación automática lo deja en paz (solo le notifica cuando aparece uno más nuevo).
- **Descubrimiento de modelos personalizados**: la sincronización también descubre **modelos personalizados afinados** (`ListCustomModels`), **modelos importados** (`ListImportedModels`) y modelos con **despliegues bajo demanda** (`ListCustomModelDeployments`) o **provisioned throughput** (`ListProvisionedModelThroughputs`). Los modelos personalizados heredan automáticamente su familia de formato del modelo base.
- **Autodescubrimiento**: Los nuevos modelos fundacionales se registran con `enabled=true` — el administrador puede deshabilitarlos. Los modelos existentes obtienen sus `available_regions` y sus metadatos de Bedrock (modalidades, ciclo de vida, ARN) actualizados automáticamente.
- **Diálogos de confirmación con estilo**: Todas las acciones destructivas (sincronizar, eliminar, restablecer) usan modales personalizados con estilo — sin ventanas emergentes `confirm()` del navegador.
- Los cambios se persisten de inmediato en `model_registry.json` vía la API de administración.
- El registro es compatible hacia atrás — los recursos existentes referencian claves de modelo (p. ej. `sd35_large`), no los IDs de modelo de Bedrock en crudo.

### 📝 6.12 Modelos autoalojados (Modelos Personalizados en Amazon SageMaker)

ArtSmoker puede desplegar modelos de IA de código abierto en **Amazon SageMaker** en su propia cuenta de AWS, ampliando sus capacidades más allá de lo que ofrece Amazon Bedrock. Estos se ejecutan junto a los modelos de Bedrock y aparecen en los mismos desplegables de los estudios.

**Catálogo de modelos extensible:** Viene con un catálogo incorporado de modelos de código abierto que abarcan generación de imágenes, upscaling, eliminación de fondo, estimación de profundidad, segmentación y video. Añadir un nuevo modelo solo requiere una entrada de catálogo — sin cambios de código. También puede añadir modelos personalizados vía la UI (+ Agregar Modelo). El catálogo y los modelos disponibles evolucionan con el tiempo.

**Opciones de despliegue:**
- **Asíncrono (escala a cero)** — pague solo cuando genera. Escala a cero cuando está inactivo ($0 de costo), escala hacia arriba automáticamente ante una nueva solicitud. Arranque en frío ~5-10 min.
- **Siempre activo** — respuestas instantáneas, ~$1.41/h (ml.g5.xlarge)

**Cómo desplegar:** Configuración del modelo → pestaña Modelos Personalizados → haga clic en Desplegar. El contenedor de SageMaker descarga los pesos del modelo directamente desde HuggingFace al inicio — no se requiere una descarga local de varios GB.

**Descarga a CPU (CPU offloading):** Los grandes modelos de difusión usan una descarga inteligente a CPU para caber en instancias de GPU más pequeñas. La entrada de catálogo de cada modelo especifica la estrategia — `model_cpu_offload` (mantiene las capas activas en la GPU) o `sequential_cpu_offload` (descarga agresiva por capa para modelos muy grandes). Aplicada automáticamente por el manejador de inferencia.

**Generación asíncrona con Trabajos pendientes:** Los modelos autoalojados generan de forma asíncrona. Un panel de **Trabajos pendientes** aparece en el Estudio de Imagen mostrando los trabajos activos con indicadores de progreso. Las imágenes completadas llegan a la Galería automáticamente — sin necesidad de sondeos ni de recargar la página.

**Gestión de tokens de HuggingFace:** Los modelos restringidos requieren un token de HuggingFace de solo lectura. El token se almacena cifrado en **AWS Secrets Manager** en su cuenta, se gestiona vía la UI (establecer/actualizar/eliminar) y se comparte entre todos los modelos que lo necesitan. Los tokens se limpian automáticamente cuando desmantela todos los modelos.

**Verificación previa de acceso restringido:** Antes de un despliegue restringido, el diálogo sondea **cada** repositorio de HuggingFace que el modelo descarga (sus propios pesos más cualquier dependencia) usando su token almacenado, y muestra un ✓/✗ por repositorio con el siguiente paso exacto — acepte la licencia de *este* repositorio en HuggingFace, o añada un token. El despliegue permanece bloqueado hasta que todos los repositorios requeridos sean accesibles, de modo que una aceptación de licencia olvidada falla rápido en el diálogo en lugar de minutos después de un arranque en frío.

**Configuración:** Añada permisos de Amazon SageMaker y Secrets Manager al **mismo rol IAM** que ya usa para Bedrock — no se necesita un rol o una variable de entorno aparte. ArtSmoker autodescubre su rol en EC2/ECS, o autocrea un `ArtSmokerSageMakerRole` si es necesario.

```bash
# Añada permisos de Amazon SageMaker a su rol existente de ArtSmoker (un solo comando)
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
```

**Dependencia de Python:** `huggingface_hub>=0.23` (instale con `pip install huggingface_hub`)

### 📝 6.13 Modelos de generación de imágenes y video

Todos los modelos se **descubren dinámicamente** del registro — no están codificados a fuego. El desplegable del Estudio de Imagen se puebla desde `GET /api/admin/models/image-options` y el del Estudio de Video desde `GET /api/admin/models/video-options` al cargar la página. Cualquier modelo registrado y habilitado en el registro aparece automáticamente.

El desplegable **Modelo de imagen** es la selección principal. Debajo de él, una línea de resumen inteligente muestra la región activa, el nivel de calidad y el costo por imagen. Una sección **Avanzado** expandible le permite anular:

- **Calidad** — los modelos que admiten niveles de calidad (una división de precio Standard/Premium) muestran un desplegable; los modelos sin niveles muestran "Predeterminado". Los niveles se declaran por modelo en el registro vía `quality_options`.
- **Región** — muestra las regiones donde el modelo seleccionado está disponible, ordenadas de más barata a más cara con precios. "Automático" selecciona la región más barata.

Una **estimación de costos** se actualiza dinámicamente según todas las selecciones (modelo × calidad × región × opciones × variaciones).

**Familias de formato**: Los modelos se invocan a través de un invocador genérico que lee las plantillas de solicitud del registro (`format_families`) — generación, edición, postprocesamiento y video son completamente dirigidos por plantillas. Añadir un nuevo modelo de imagen de Bedrock no requiere **ningún cambio de código**: simplemente regístrelo (vía autodescubrimiento o la API de administración) con la familia de formato correcta. El catálogo completo de familias está en [SPEC.md](SPEC.md).

**Ingeniería de prompts optimizada por modelo**: Los prompts se estructuran automáticamente como descripciones (no comandos) siguiendo la [documentación de AWS](https://docs.aws.amazon.com/nova/latest/userguide/prompting-image-generation.html). Las palabras de negación se eliminan del prompt principal y los términos de exclusión se envían como un **prompt negativo** separado. El prompt se trunca al `prompt_limit` específico de cada modelo del registro.

> [!NOTE]
> **La sensibilidad de la moderación varía según el modelo** y se rastrea en el registro (`moderation_strictness`). Los modelos Stability de Amazon Bedrock (p. ej., SD 3.5 Large, Stable Image Ultra, Stable Image Core) aplican la moderación de la plataforma de AWS y están ajustados en "moderada"; los modelos autoalojados (p. ej., FLUX, HunyuanImage, Qwen-Image) se ejecutan en su propia cuenta sin ningún filtro de contenido impuesto por la plataforma. ArtSmoker maneja los bloqueos automáticamente — cuando un prompt es rechazado, el sistema prueba modelos alternativos ordenados por estrictez antes de sugerir una reescritura.

## 📌 7. Stack tecnológico

| Capa | Tecnología |
|-------|-----------|
| Backend | FastAPI (Python 3.12–3.14), boto3, Pydantic |
| Frontend | Vanilla JS, Tailwind CSS (CDN) |
| IA (LLM) | LLM rápido y LLM complejo — rotados automáticamente en cada sincronización a los Claude Sonnet y Opus más recientes |
| IA (Imagen) | Modelos de imagen de Amazon Bedrock que encuentra la sincronización (p. ej., Stable Diffusion 3.5 Large, Stable Image Ultra, Stable Image Core); catálogo autoalojado en SageMaker (p. ej., FLUX.2/FLUX.1, HunyuanImage 3.0, Qwen-Image) |
| IA (Postprocesamiento) | Modelos de edición de Amazon Bedrock (p. ej., Stability AI Remove Background, Creative Upscale) |
| IA (Chat) | Cada LLM de chat que encuentra la sincronización, vía Bedrock ConverseStream o Mantle (p. ej., Claude, Nova, Llama, Mistral) |
| IA (Video) | Modelos de video de Amazon Bedrock que encuentra la sincronización (p. ej., Luma AI Ray v2, hasta 9s) |
| IA (Voz) | Amazon Nova Sonic, la versión activa más reciente (voz a texto vía streaming bidireccional) |
| i18n | Función personalizada t(), 9 idiomas, traducción del DOM por búsqueda inversa |
| Conversión SVG | vtracer (principal), potrace (respaldo), Pillow (último recurso) |
| Renderizado de texto | Pillow (efectos de sombra, contorno, resplandor) |
| Almacenamiento | Sistema de archivos local (interfaz compatible con S3) |
| Desarrollo | Middleware sin caché para archivos estáticos; registro de errores del lado del cliente vía `POST /api/log` |

No se requiere paso de compilación para el frontend.

## 📌 8. Modelo de seguridad

ArtSmoker está diseñado como una **herramienta de desarrollo para red local/confiable** — se ejecuta en la propia máquina del desarrollador o en una instancia EC2 privada. El modelo de seguridad refleja esto:

- **Sin autenticación** — todos los endpoints de la API están abiertos. Apropiado para el desarrollo local y despliegues de equipo privados.
- **Otros sitios web no pueden usar su navegador para llegar a ArtSmoker** — ArtSmoker rechaza las solicitudes que otro sitio web hace a través de su navegador (solicitudes entre sitios y nombres de host desconocidos, es decir, DNS rebinding), de modo que una página que visite no puede leer sus recursos ni iniciar trabajos en su cuenta. ¿Accede a él mediante un nombre DNS? Añada el nombre a `ARTSMOKER_ALLOWED_HOSTS` (consulte [Límites configurables](#-11-límites-configurables)).
- **Explorador de sistema de archivos** — el endpoint `GET /api/browse/local` permite explorar cualquier directorio al que el proceso del servidor pueda acceder. Esto es intencional para importar arte de referencia desde su máquina.
- **Servicio de fuentes** — la protección contra el recorrido de rutas (path traversal) valida que las solicitudes de archivos de fuente permanezcan dentro de los directorios esperados.
- **Acceso a S3** — la exploración e importación de S3 usan las credenciales de AWS del servidor. El usuario puede acceder a cualquier bucket de S3 que su rol IAM permita.

> [!WARNING]
> No exponga ArtSmoker a redes no confiables sin añadir autenticación y restricciones de ruta. Consulte la [Hoja de ruta de despliegue en SPEC.md](SPEC.md#16-deployment--scaling-roadmap) para orientación sobre el fortalecimiento en producción (la Fase 4 añade autenticación con Cognito).

## 📌 9. API

Documentación interactiva en **http://localhost:8000/docs** (Swagger UI).

Endpoints clave:

| Endpoint | Propósito |
|----------|---------|
| **Generación** | |
| `POST /api/generate/` | Generar recursos (opciones × variaciones) con streaming SSE |
| `POST /api/generate/post-process` | Aplicar procesamiento a recursos existentes |
| `POST /api/generate/edit` | Edición de imágenes: inpaint, outpaint, erase, search-replace, etc. Acepta imagen de origen, máscara, prompt, modelo. |
| `POST /api/generate/suggest-edit-prompt` | IA "Generar prompt" para la pestaña Editar: lee la imagen + el prompt original y devuelve un prompt de edición para un modo dado, con estilo para el modelo de edición objetivo (descripción vs. instrucción) |
| `POST /api/generate/analyze-moderation` | Analizar un prompt bloqueado por moderación y sugerir una reescritura segura |
| **Estilos** | |
| `POST /api/styles/` | Crear un perfil de estilo |
| `POST /api/styles/{id}/import` | Importación masiva de referencias desde una carpeta local o una URI de S3 |
| `POST /api/styles/{id}/analyze` | Disparar el análisis de estilo por IA |
| **Prompt** | |
| `POST /api/refine-prompt/` | Vista previa de un prompt refinado |
| `POST /api/transcribe/` | Voz a texto (Nova Sonic) |
| **Galería** | |
| `GET /api/gallery/` | Explorar recursos generados (admite paginación limit/offset) |
| `GET /api/gallery/batch/{batch_id}` | Reconstruir la estructura completa de opciones × variaciones de un lote |
| `DELETE /api/gallery/` | Eliminación masiva de recursos |
| **Estudio de Texto** | |
| `POST /api/type-studio/preview` | Renderizar la vista previa de la superposición de texto |
| `POST /api/type-studio/suggest` | Sugerencia de diseño por IA para el texto |
| `GET /api/type-studio/fonts` | Listar las fuentes disponibles |
| **Explorar** | |
| `GET /api/browse/local?path=~` | Explorar el contenido de un directorio local |
| `GET /api/browse/s3/buckets` | Listar los buckets de S3 disponibles |
| `GET /api/browse/s3?bucket=name&prefix=path` | Explorar el contenido de un bucket de S3 |
| **Chat** | |
| `POST /api/chat/stream` | Transmitir la respuesta del LLM vía SSE (Bedrock ConverseStream) |
| `GET /api/chat/models` | Listar todos los modelos de chat disponibles (fundacionales + personalizados + importados) |
| `POST /api/chat/sessions` | Crear una nueva sesión de chat |
| `GET /api/chat/sessions` | Listar sesiones de chat |
| `GET /api/chat/sessions/{id}` | Cargar una sesión completa (mensajes + metadatos) |
| `PUT /api/chat/sessions/{id}` | Actualizar la sesión (título, mensajes, modelo, temperatura) |
| `DELETE /api/chat/sessions/{id}` | Eliminar una sesión |
| `POST /api/chat/sessions/{id}/duplicate` | Duplicar una sesión |
| `GET /api/chat/sessions/{id}/export` | Exportar la sesión como Markdown |
| `GET /api/chat/sessions/{id}/search?q=` | Buscar dentro de los mensajes de una sesión |
| `POST /api/chat/compact` | Compactar mensajes antiguos mediante resumen por LLM |
| `POST /api/chat/generate-title` | Autogenerar un título de sesión a partir del primer intercambio |
| **Video** | |
| `POST /api/video/generate` | Iniciar un trabajo asíncrono de generación de video |
| `GET /api/video/status/{job_id}` | Consultar el estado del trabajo de generación de video |
| `GET /api/video/jobs` | Listar todos los trabajos de generación de video |
| `GET /api/video/{id}/mp4` | Servir el archivo MP4 del video |
| `GET /api/video/{id}/thumbnail` | Servir la miniatura del video |
| `DELETE /api/video/{id}` | Eliminar un video |
| **Administración** | |
| `GET /api/admin/models` | Obtener el registro completo de modelos (LLMs, modelos de imagen, postprocesamiento) |
| `GET /api/admin/models/image-options` | Modelos de texto a imagen habilitados para el desplegable (con precios, niveles de calidad, regiones). Acepta el filtro `?region=`. |
| `GET /api/admin/regions` | Lista en caché de las regiones de AWS compatibles con Bedrock (sin llamadas a AWS) |
| `PATCH /api/admin/models/category/{name}` | Actualizar la configuración de una categoría LLM |
| `PATCH /api/admin/models/image/{key}` | Actualizar la configuración de un modelo de imagen |
| `POST /api/admin/models/image` | Añadir un nuevo modelo de imagen |
| `POST /api/admin/discover/refresh-all` | Actualización completa: descubrir regiones + escanear modelos + obtener precios + podar datos obsoletos. El ÚNICO endpoint que llama a las API de descubrimiento de AWS. |
| `POST /api/admin/discover/{region}/auto-register` | Escanear una sola región en busca de modelos, registrar los nuevos, actualizar las regiones de los existentes |
| `GET /api/admin/discover/{region}` | Descubrir los modelos de Bedrock disponibles en una región (listado en crudo) |
| `GET /api/admin/templates` | Obtener las 28 plantillas de prompt editables |
| `PATCH /api/admin/templates/{name}` | Actualizar una plantilla (valida las variables requeridas) |
| `POST /api/admin/templates/{name}/reset` | Restablecer una plantilla al valor predeterminado |
| `POST /api/admin/templates/{name}/enhance` | Mejorar una plantilla con IA |
| **Sistema** | |
| `POST /api/log` | Registro de errores/advertencias del lado del cliente (registrado como `[CLIENT]` en la consola del servidor) |
| `GET /api/health` | Comprobación de salud + validación de credenciales de AWS/Bedrock |

## 📌 10. Estructura del proyecto

```
ArtSmoker/
├── backend/
│   ├── main.py              # App FastAPI, validación al inicio, montaje de estáticos
│   ├── config.py            # Ajustes (regiones de AWS, IDs de modelo, rutas, límites)
│   ├── model_registry.json  # Única fuente de la verdad: modelos, regiones, precios, familias de formato, niveles de calidad
│   ├── requirements.txt
│   ├── prompt_templates.json # Prompts de directivas LLM editables — fuente de la verdad en ejecución (28 plantillas)
│   ├── routers/
│   │   ├── generate.py      # Generación de recursos en dos niveles + streaming SSE + guiada por referencia
│   │   ├── generate_3d.py   # Imagen a 3D: generación, revisión de la fuente, variantes, trabajos asíncronos
│   │   ├── custom_deploy.py # Despliegue/desmantelamiento de modelos autoalojados (Amazon SageMaker)
│   │   ├── styles.py        # CRUD de perfiles de estilo + importación de directorio/S3 + análisis
│   │   ├── gallery.py       # Exploración de recursos + servicio de archivos + exportaciones para motores + borrado masivo
│   │   ├── typestudio.py    # Estudio de Texto: superposición de texto, servicio de fuentes, diseño por IA
│   │   ├── video.py         # Generación de video (asíncrona), sondeo de trabajos, servicio de MP4/miniaturas
│   │   ├── chat.py          # Estudio de Chat: streaming LLM, sesiones, exportación, compactación de contexto
│   │   ├── browse.py        # Explorador de archivos/S3 del servidor para importar referencias
│   │   ├── refine.py        # Vista previa del refinamiento del prompt + vista previa de la traducción
│   │   ├── transcribe.py    # Transcripción de voz
│   │   └── admin.py         # Gestión del registro de modelos + descubrimiento de Bedrock + plantillas de prompt
│   ├── services/
│   │   ├── bedrock_client.py     # Cliente de Bedrock compartido con pool de conexiones
│   │   ├── model_registry.py     # Registro de modelos: carga/guarda model_registry.json
│   │   ├── prompt_engineer.py    # Claude: refinamiento de prompts + generación de conceptos
│   │   ├── image_generator.py    # Enruta a Bedrock (SD 3.5 / Ultra / Core) o a SageMaker (FLUX / Hunyuan / Qwen)
│   │   ├── style_analyzer.py     # Análisis de estilo en dos fases (cohesión + completo)
│   │   ├── post_processor.py     # Stability AI: eliminación de fondo, escalado; vtracer: SVG
│   │   ├── transcriber.py        # Nova Sonic: voz a texto en streaming
│   │   ├── import_dedup.py       # Deduplicación inteligente (rotaciones, animaciones, carpetas)
│   │   ├── texture_extractor.py  # Extracción de texturas glTF/GLB
│   │   ├── prompt_translator.py  # Detección automática del idioma + traducción al inglés
│   │   ├── prompt_templates.py   # Prompts de directivas LLM editables (cargar/guardar/validar)
│   │   ├── video_generator.py   # Video: invocación asíncrona de Bedrock, descarga de S3, miniaturas con ffmpeg
│   │   ├── cost_tracker.py      # Acumulador de costos por solicitud
│   │   ├── custom_models.py    # Catálogo de modelos autoalojados (extensible)
│   │   ├── async_jobs.py       # Cola de trabajos de generación asíncrona (panel Trabajos pendientes)
│   │   ├── reference_analyzer.py # Análisis de visión de «Inspirado en la referencia»
│   │   ├── mesh_export.py      # Exportaciones 3D listas para el motor mediante un Blender sin interfaz gestionado
│   │   ├── sagemaker_deployer.py # Gestión de endpoints de Amazon SageMaker (descarga directa desde HF para modelos de HF)
│   │   └── sagemaker_invoker.py  # Enruta la inferencia a endpoints de Amazon SageMaker
│   ├── models/
│   │   ├── style_profile.py       # StyleProfile, AnalyzedStyle, Create/Update
│   │   ├── generation_request.py  # Enums GenerationRequest, AssetType, ImageModel
│   │   └── generation_result.py   # GenerationResult, OptionResult, VariantResult
│   └── storage/
│       └── local_store.py         # Sistema de archivos local (interfaz compatible con S3)
├── frontend/
│   ├── index.html           # Punto de entrada de la SPA
│   ├── css/styles.css       # Tema oscuro + animaciones
│   └── js/
│       ├── app.js               # Enrutador de la SPA + caché del DOM + navegación + showConfirm()
│       ├── i18n/
│       │   ├── i18n.js          # Núcleo: función t(), cambio de idioma, búsqueda inversa
│       │   ├── en.json          # Inglés (base) — ~1.500 claves
│       │   └── ja/zh/ko/hi/ru/fr/es/de.json   # 8 traducciones
│       ├── services/api.js      # Cliente de la API del backend
│       └── components/
│           ├── ImageStudio.js   # Estudio de Imagen (opciones × variaciones, multimodelo)
│           ├── TypeStudio.js    # Estudio de Texto (superposición de texto)
│           ├── VideoStudio.js   # Estudio de Video (generación de texto a video)
│           ├── ChatStudio.js    # Estudio de Chat (chat LLM multimodelo)
│           ├── Gallery.js       # Cuadrícula de la Galería + búsqueda + operaciones masivas
│           ├── StyleLibrary.js  # Gestión de estilos + explorador de archivos
│           ├── AssetViewer.js   # Vista previa a tamaño completo, edición, 3D, exportaciones, metadatos
│           ├── ModelSettings.js # UI de administración del registro de modelos (modal)
│           ├── PromptEditor.js  # Editor de prompt de dos áreas + composición
│           ├── PromptDesigner.js # Descomposición estructurada del prompt (campos de bloquear/variar)
│           ├── ReferenceStudio.js # Pestaña Inspiración de imagen (generación guiada por referencia)
│           └── VoiceInput.js    # MediaRecorder + transcripción
├── data/
│   ├── styles/              # Perfiles de estilo + imágenes de referencia (enlaces simbólicos)
│   ├── images/              # Recursos generados (PNG + SVG + metadata.json)
│   ├── video/               # Recursos de video (MP4 + miniaturas + metadatos de trabajos)
│   └── chat/                # Sesiones de chat (un JSON por sesión)
├── tools/                   # Blender portátil gestionado (descarga automática; ignorado por git)
├── SPEC.md                  # Especificación técnica completa (plano de reconstrucción)
└── README.md                # Versión en inglés de este archivo
```

## 📌 11. Límites configurables

Los ajustes en `backend/config.py` se pueden anular mediante variables de entorno (prefijo `ARTSMOKER_`):

| Ajuste | Variable de entorno | Predeterminado | Propósito |
|---------|-------------|---------|---------|
| `max_reference_images` | `ARTSMOKER_MAX_REFERENCE_IMAGES` | 100 | Máximo de imágenes importadas por estilo |
| `max_analysis_images` | `ARTSMOKER_MAX_ANALYSIS_IMAGES` | 20 | Máximo de imágenes enviadas a la IA por llamada de análisis |
| `aws_region_models` | `ARTSMOKER_AWS_REGION_MODELS` | us-west-2 | Región para los modelos Claude + Stability AI |
| `aws_region_images` | `ARTSMOKER_AWS_REGION_IMAGES` | us-east-1 | Región para Amazon (voz Nova Sonic) |
| `aws_profile` | `ARTSMOKER_AWS_PROFILE` | None | Nombre del perfil de AWS (usa la cadena predeterminada si no se establece) |
| `allowed_hosts` | `ARTSMOKER_ALLOWED_HOSTS` | *(vacío)* | Nombres de host adicionales a los que responde el servidor, separados por comas (`.example.com` admite subdominios; `*` desactiva la comprobación). Siempre se permiten: localhost, cualquier dirección IP y el nombre de host de esta máquina |
| `cors_origins` | `ARTSMOKER_CORS_ORIGINS` | *(vacío)* | Otros orígenes web autorizados a llamar a la API desde un navegador, separados por comas. No hace falta ninguno: ArtSmoker sirve su propia UI |
| `auto_update` | `ARTSMOKER_AUTO_UPDATE` | true | Actualización controlada por versión al inicio + verificación periódica cada 24h (git o tarball), luego reinicio en el mismo lugar |

Reducir `max_analysis_images` reduce los costos de visión de IA por análisis. Reducir `max_reference_images` limita el almacenamiento. Ambos se pueden ajustar según el presupuesto.

## 📌 12. Precios de Amazon Bedrock y desglose de costos

> [!IMPORTANT]
> **Los modelos se descontinúan y cambian rápido.** Salen nuevos modelos y se retiran los antiguos con frecuencia, por lo que cualquier nombre de modelo o precio fijado a fuego en la documentación queda obsoleto rápidamente. ArtSmoker maneja esto automáticamente — cada ejecución de **Sincronizar desde AWS** vuelve a descubrir la línea de modelos actual, rota automáticamente las ranuras LLM compartidas a los Claude Sonnet/Opus más recientes y actualiza los precios en vivo por modelo desde la AWS Pricing API en `model_registry.json`. **La aplicación es la fuente de la verdad** — tanto de qué modelos existen como de cuánto cuestan (mostrado en vivo en la barra lateral del Estudio de Imagen según el modelo seleccionado, el nivel de calidad, la región y el tamaño del lote). Los nombres de modelos y cualquier cifra a continuación son **solo ejemplos ilustrativos** (consulte [Sobre los nombres de modelos](#about-model-names)) — confirme siempre los modelos/precios actuales en la aplicación o en la [página oficial de precios de Amazon Bedrock](https://aws.amazon.com/bedrock/pricing/).

Las **regiones base predeterminadas** de la app son `us-west-2` (p. ej., Claude, Stability AI) y `us-east-1` (p. ej., Amazon Nova Sonic); la sincronización fija cada modelo en una Región donde AWS lo ofrece, y los precios difieren según la región. Consulte también [SPEC.md](SPEC.md#14-amazon-bedrock-pricing--cost-breakdown) para el modelo de costos.

### 📝 12.1 Precios por unidad

Qué genera costo y su unidad de facturación (consulte la app para el precio unitario actual):

| Servicio | Facturado | Notas |
|---------|--------|-------|
| **Ingeniería de prompts LLM y chat** (LLM rápido / complejo — p. ej., Claude Sonnet / Opus, rotados automáticamente a los más recientes al Sincronizar) | por token de entrada / salida | Refinamiento de prompts, conceptos, chat, análisis de estilo, moderación |
| **Generación de imágenes en Bedrock** (p. ej., Stable Diffusion 3.5 Large, Stable Image Ultra, Stable Image Core) | por imagen | Ultra ≫ SD 3.5 ≫ Core en precio; cifra en vivo mostrada en la app |
| **Imagen / 3D autoalojados** (p. ej., FLUX, HunyuanImage, Qwen-Image, TripoSG, TRELLIS.2) | por segundo-GPU de su instancia de SageMaker | Escala a cero cuando está inactivo ($0); no se factura por imagen |
| **Postprocesamiento** (Remove Background, Creative Upscale) | por imagen | Servicios de Stability AI |
| **Conversión SVG** | gratis | Local (vtracer/potrace) — $0.00 |

> [!NOTE]
> Precios de la [página oficial de precios de Amazon Bedrock](https://aws.amazon.com/bedrock/pricing/) a marzo de 2026. Los precios pueden cambiar — verifique siempre contra la fuente oficial antes de presupuestar.

### 📝 12.2 Costos adicionales de LLM (por uso)

Estas llamadas a LLM están incluidas en el flujo de trabajo de generación pero no se detallan por separado en las tablas de costos por lote de abajo:

| Llamada | Modelo | Cuándo | Costo aprox. |
|------|-------|------|-------------|
| **Verificación previa del prompt** | LLM rápido (p. ej., Claude Sonnet) | Antes de la generación (si el interruptor está activado) | ~$0.005 |
| **Reescritura de moderación** | LLM rápido (p. ej., Claude Sonnet) | Solo cuando todos los modelos rechazan un prompt | ~$0.005 |
| **Diseño del Estudio de Texto** | LLM complejo (p. ej., Claude Opus) | Cada solicitud de sugerencia de diseño por IA | ~$0.02–$0.05 |

Estos son pequeños — la verificación previa y la reescritura de moderación cuestan una fracción de centavo cada una. El diseño del Estudio de Texto es comparable a un refinamiento de prompt de una sola opción.

### 📝 12.3 Costo del análisis de estilo (una vez por estilo)

~**$0.14** por estilo (20 imágenes enviadas al LLM complejo, p. ej., Claude Opus, + una verificación de cohesión de 8 imágenes en el LLM rápido, p. ej., Claude Sonnet). La verificación de cohesión añade ~$0.01.

### 📝 12.4 Costo de generación por tamaño de lote

Incluye el refinamiento de prompt/generación de conceptos + la generación de imágenes:

| Escenario | Stable Image Core | Stable Diffusion 3.5 Large | Stable Image Ultra |
|----------|-------------------|-------------|-------------------|
| 1 opción × 1 variación | ~$0.05 | ~$0.09 | ~$0.15 |
| 1 opción × 5 variaciones | ~$0.21 | ~$0.41 | ~$0.71 |
| 5 opciones × 5 variaciones | ~$1.05 | ~$2.05 | ~$3.55 |

Los modelos autoalojados de SageMaker (p. ej., FLUX, HunyuanImage, Qwen-Image) facturan por tiempo de GPU en su propia instancia (escala a cero cuando está inactivo), no por imagen — consulte [SPEC.md](SPEC.md#14-amazon-bedrock-pricing--cost-breakdown) para el modelo de costo de cómputo.

### 📝 12.5 Complementos de postprocesamiento (por imagen)

| Complemento | Por imagen | 1 imagen | 5 imágenes | 25 imágenes |
|--------|-----------|---------|----------|-----------|
| Eliminar fondo | $0.07 | $0.07 | $0.35 | $1.75 |
| Creative Upscale | $0.60 | $0.60 | $3.00 | $15.00 |
| Convertir a SVG | $0.00 | $0.00 | $0.00 | $0.00 |

> [!TIP]
> **Nota sobre Creative Upscale**: Maneja automáticamente el límite de 16MB de la carga útil de respuesta de Stability AI usando internamente el formato de salida JPEG, y luego convirtiendo de vuelta a PNG. Incluye reintentos con backoff exponencial para el throttling de la API.

### 📝 12.6 Ejemplos prácticos

| Ejemplo | Configuración | Costo total |
|---------|-------------|-----------|
| **Más económico** | 1×1, Stable Image Core, sin procesamiento | ~$0.05 |
| **Estándar** | 1×5, Stable Diffusion 3.5 Large, Eliminar fondo | ~$0.76 |
| **Exploración completa** | 5×5, Stable Diffusion 3.5 Large, Eliminar fondo + SVG | ~$3.80 |
| **Premium** | 5×5, Stable Image Ultra, Eliminar fondo + Creative Upscale + SVG | ~$20.30 |

> [!TIP]
> **Punto clave**: La generación de imágenes en sí es económica ($0.01–$0.14/imagen). **Creative Upscale a $0.60/imagen es el costo dominante** — úselo selectivamente en sus recursos finales elegidos, no en el lote completo. Eliminar fondo a $0.07/imagen es razonable. La conversión SVG es gratuita (se ejecuta localmente).

<a id="disclaimer"></a>

## 📌 13. Exención de responsabilidad

> [!IMPORTANT]
> **Calidad del contenido generado**: Todas las imágenes, videos y otros recursos generados por ArtSmoker son producidos por modelos de IA disponibles a través de Amazon Bedrock, incluidos tanto los modelos propios de AWS como los modelos de terceros. La calidad, precisión y adecuación del contenido generado dependen completamente de los prompts proporcionados, los modelos seleccionados y las referencias de estilo subidas por el usuario. Los autores y colaboradores de ArtSmoker no ofrecen garantías respecto a la calidad, idoneidad o aptitud para un propósito de cualquier contenido generado.
>
> **Propiedad intelectual**: Los usuarios son los únicos responsables de asegurar que sus prompts, imágenes de referencia y salidas generadas no infrinjan derechos de propiedad intelectual de terceros, incluyendo pero no limitado a derechos de autor, marcas registradas y derechos de imagen. ArtSmoker es una herramienta — no filtra, valida ni evalúa el estado de PI de las entradas o salidas. Los autores y colaboradores de la herramienta no asumen responsabilidad alguna por cualquier infracción de PI derivada del uso de este software.
>
> **Términos de los modelos de IA y del servicio**: El contenido generado está sujeto a los términos de servicio y las políticas de uso aceptable de los proveedores de modelos de IA subyacentes accesibles a través de Amazon Bedrock. Los usuarios deben revisar los [AWS Service Terms](https://aws.amazon.com/service-terms/), el [Amazon Bedrock SLA](https://aws.amazon.com/bedrock/sla/) y los términos de cada proveedor de modelos antes de usar recursos generados en contextos de producción o comerciales.
>
> **Licencias de modelos y uso comercial**: Los modelos autoalojados desplegados a través de ArtSmoker se rigen por los términos de licencia de sus creadores, que le vinculan a **usted** directamente. ArtSmoker muestra la licencia y el desglose de dependencias de cada modelo en el momento del despliegue y registra su aceptación, pero **no** verifica, hace cumplir ni garantiza su derecho de uso comercial — mantenerse dentro de los términos de la licencia (umbrales de ingresos/usuarios, restricciones territoriales, requisitos de atribución, informes de uso) es responsabilidad exclusivamente suya. La orientación sobre licencias comerciales de la [sección 1.9.3](#-193-uso-comercial-de-un-modelo--a-quién-pagar-y-cómo) es solo informativa, refleja los términos de los proveedores en el momento de redactarse y **no constituye asesoramiento legal**; los términos de licencia cambian con frecuencia — confirme siempre los términos vigentes del proveedor y consulte a un abogado antes de un lanzamiento comercial. ArtSmoker no tiene afiliación alguna con ningún proveedor de modelos ni recibe nada de ellos.
>
> **Los costos son solo estimaciones — vigile su propio gasto**: Todos los costos que muestra ArtSmoker (por imagen, por video, por token, cómputo 3D, despliegue y totales de sesión/recurso) son **estimaciones solo orientativas**, calculadas a partir de los precios publicados de AWS y el uso previsto. **No son una factura ni una garantía** de sus cargos reales. El costo real depende de los precios de su cuenta de AWS, la región, los descuentos, los impuestos, la transferencia de datos, el tiempo de actividad de los endpoints (incluidas las instancias de SageMaker inactivas/en caliente), el comportamiento del autoescalado y factores ajenos a esta herramienta. **Usted es el único responsable de supervisar y controlar su propio gasto de AWS** — use la [AWS Billing Console](https://console.aws.amazon.com/billing/), [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/) y los [presupuestos/alarmas de facturación](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html) para rastrear y limitar los cargos reales. En particular, los endpoints de SageMaker autoalojados siguen facturando mientras estén desplegados o mantenidos en caliente, incluso inactivos — recuerde desmantelarlos al terminar. Los autores y colaboradores no asumen responsabilidad alguna por cualquier cargo de AWS derivado del uso de este software.
>
> **Sin garantía**: Este software se proporciona "tal cual" sin garantía de ningún tipo. Consulte [LICENSE](LICENSE) para los términos completos.

## 📌 14. Especificación completa

Consulte **[SPEC.md](SPEC.md)** para la especificación técnica completa — arquitectura, diseño de componentes, configuración de modelos, referencia de API, modelo de seguridad, precios, hoja de ruta de despliegue y suficiente detalle para reconstruir el proyecto desde cero.
