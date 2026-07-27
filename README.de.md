> Dieses Dokument ist eine Übersetzung des englischen README. Für die aktuellsten Informationen konsultieren Sie bitte das [englische README](README.md).

# ArtSmoker
> *Der Smoke-Test für Ihre Kunstwerke!*

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green?logo=fastapi&logoColor=white)
![Amazon Bedrock](https://img.shields.io/badge/Amazon-Bedrock-orange?logo=amazonaws&logoColor=white)
![License](https://img.shields.io/badge/License-MIT--0-yellow)

## 📌 0. Überblick

Eine einfache, künstlerfreundliche Oberfläche für die Bild- und Videogenerierungsmodelle von Amazon Bedrock. ArtSmoker hilft Kreativteams, Bedrock effizient zu nutzen — ohne die API, das CLI oder Prompt-Engineering erlernen zu müssen.

### 📝 Das Problem

Kreativteams und Spielestudios möchten KI für die Asset-Generierung nutzen, stoßen dabei aber auf reale Hürden:

- **Keine einfache Oberfläche** — Künstler sollten sich nicht in der Bedrock-Konsole anmelden oder API-Aufrufe schreiben müssen, um Bilder zu generieren
- **Prompt-Engineering ist schwierig** — das Verfassen wirksamer Prompts mit passenden Negativ-Prompts, Stildirektiven und modellspezifischer Formatierung erfordert Fachwissen, das die meisten Künstler nicht besitzen
- **Teams bauen/trainieren keine eigenen Modelle** — sie benötigen Zugriff auf die vielen bereits auf Bedrock verfügbaren Modelle, über ein Werkzeug, das sie tatsächlich nutzen können
- **Bildbearbeitung ist unzugänglich** — Inpainting, Outpainting, Suchen & Ersetzen und Stiltransfer erfordern allesamt API-Kenntnisse
- **2D-zu-3D ist eine separate Pipeline** — von einem 2D-Konzept zu einem texturierten, spielengine-fertigen 3D-Modell zu gelangen, erfordert normalerweise manuelle Modellierung, UV-Unwrapping und Texture-Painting — oder teure Drittanbieter-Werkzeuge

### 📝 Die Lösung

ArtSmoker ist eine selbst gehostete Webanwendung, die Amazon Bedrock in einer klaren kreativen Oberfläche kapselt — speziell für die Produktion von Spiele-Assets konzipiert, aber auch anwendbar in anderen kreativen Branchen wie Werbung, E-Commerce, Verlagswesen und digitalen Medien, in denen KI-generierte visuelle Inhalte einen Mehrwert bieten.

- **Künstler beschreiben in einfacher Sprache, was sie brauchen** — ArtSmoker übernimmt im Hintergrund die Prompt-Dekomposition, die Verbesserung, die modellspezifische Optimierung und die Stilanwendung. Ein geführter Prompt Designer lässt Nutzer einzelne visuelle Elemente (Motiv, Szene, Beleuchtung, Farben) mit Sperren/Variieren-Steuerelementen für wirklich unterschiedliche kreative Optionen feinabstimmen
- **Stilbewusste Generierung** — laden Sie die vorhandene Grafik Ihres Spiels hoch, und die Vision-Modelle von ArtSmoker erlernen Ihre visuelle Identität. Jedes generierte Asset passt zum Look and Feel Ihres Spiels
- **Alle Bedrock-Modelle, alle Regionen** — vollständig konfigurierbar. Wählen Sie Ihre Text-to-Image-Modelle, Videomodelle und Regionen. Das System entdeckt verfügbare Modelle dynamisch über die Bedrock-API
- **Selbst gehostete Open-Source-Modelle — 1-Klick-Deployment** — durchstöbern Sie einen kuratierten Katalog vorab getesteter Modelle (HunyuanImage 3.0, FLUX.2 und mehr), wählen Sie eine GPU-Instanz und deployen Sie mit einem Klick auf Amazon SageMaker. Alles wird übernommen: Inferenz-Packaging, Quantisierung, CUDA-Konfiguration, Auto-Scaling und Job-Tracking. Jedes Katalogmodell wird vor der Auslieferung durchgängig validiert
- **Image-to-3D mit einem Klick** — generieren Sie ein texturiertes 3D-Modell (GLB) direkt aus jedem 2D-Spiele-Asset oder Charakterbild. Multi-View-Synthese und Texture-Baking erzeugen spielengine-fertige Meshes, die sich direkt in Unity, Unreal oder Blender importieren lassen — ohne manuelle Modellierung
- **Ihr AWS-Konto, Ihr geistiges Eigentum** — alles läuft in Ihrem eigenen privaten AWS-Konto. Sämtliche Kunstwerke, Prompts, Stile und generierten Assets bleiben in Ihrer isolierten Umgebung — keine Daten gelangen zu Drittanbieterdiensten. Sie behalten das volle Eigentum und die volle Kontrolle über Ihr kreatives geistiges Eigentum

**Amazon-Bedrock-Modelle**: Claude Sonnet/Opus (Prompt-Engineering & Chat), Stable Diffusion 3.5 Large, Stable Image Ultra, Stable Image Core, Stability-AI-Dienste (Bildbearbeitung), Nova Reel, Luma AI Ray (Videogenerierung) sowie 80+ LLMs von 16 Anbietern für Chat Studio. **Selbst gehostete Modelle**: Qwen-Image (Text-to-Image) & Qwen-Image-Edit (referenzgeführte + instruktionsbasierte Bearbeitung, Apache-2.0), HunyuanImage 3.0 (BF16/NF4), FLUX.2, FLUX.1, TripoSG & TRELLIS.2 (Image-to-3D) und mehr über Amazon SageMaker — mit einem erweiterbaren Katalog zum Hinzufügen neuer Modelle.

**[Jetzt loslegen — zu Voraussetzungen & Installation springen ▸](#get-started)**

### Language / 言語 / 语言 / 언어 / हिन्दी / Язык / Langue / Idioma

ArtSmoker unterstützt 9 Sprachen. Wechseln Sie die UI-Sprache über die Sprachschaltflächen in der oberen Navigationsleiste (EN | 日 | 中 | 한 | हिं | РУ | FR | ES | DE). Ihre Auswahl wird automatisch gespeichert.

| Sprache | README |
|---------|--------|
| English (Englisch) | [README.md](README.md) |
| 日本語 (Japanisch) | [README.ja.md](README.ja.md) |
| 中文 (Chinesisch) | [README.zh.md](README.zh.md) |
| 한국어 (Koreanisch) | [README.ko.md](README.ko.md) |
| हिन्दी (Hindi) | [README.hi.md](README.hi.md) |
| Русский (Russisch) | [README.ru.md](README.ru.md) |
| Français (Französisch) | [README.fr.md](README.fr.md) |
| Español (Spanisch) | [README.es.md](README.es.md) |
| Deutsch | Dieses Dokument |

**Mehrsprachige Prompt-Unterstützung:**
- Nicht-englische Prompts werden automatisch erkannt (Japanisch, Chinesisch, Koreanisch, Hindi, Russisch, Französisch, Spanisch und mehr) und vor der Generierung ins Englische übersetzt
- Eine zweisprachige Vorschau erscheint im Prompt-Bereich: Wechseln Sie zwischen Ihrem Originaltext und der englischen Übersetzung, um genau zu sehen, was das Modell erhalten wird
- Der ursprüngliche Prompt, die erkannte Sprache und die englische Übersetzung werden alle in den Asset-Metadaten aufbewahrt
- Dateinamen werden aus dem übersetzten englischen Prompt generiert (sodass „病院の建物" → `hospital-building_opt1_var1.png`)
- Chat Studio übergibt Prompts direkt an das LLM (ohne Übersetzung), da Modelle wie Claude nativ mehrsprachig sind
- Der Text in Type Studio bleibt in Ihrer Sprache (er wird unverändert auf dem Bild gerendert)
- Alle Moderations-Vorprüfungen und die Inhaltsprüfung arbeiten aus Konsistenzgründen mit dem übersetzten englischen Prompt

## 📌 1. Was es kann

ArtSmoker arbeitet in zwei Modi — **eigenständig** (keine Einrichtung eines Kunststils oder Themas nötig, einfach beschreiben und generieren) und **stilgeführt** (laden Sie Ihre vorhandene Grafik hoch, und jede Generierung passt zu Ihrer visuellen Identität). Beide Modi nutzen dieselben Studios und dieselbe Generierungs-Pipeline.

### 📝 Eigenständiger Modus (Schnellstart)

Keine Stil- oder Themen-Einrichtung nötig — öffnen Sie das 2D Image Studio, das Video Studio oder das Type Studio und beginnen Sie sofort mit dem Gestalten.

1. **Beschreiben Sie, was Sie brauchen** — geben Sie einen Prompt wie „hospital building" oder „fire mage character" ein oder nutzen Sie die Spracheingabe. Die KI zerlegt Ihre Idee in visuelle Komponenten, verbessert sie mit modellspezifischen Optimierungen und respektiert Ihre kreative Absicht durch intelligente Sperren/Variieren-Steuerelemente. Schreiben Sie in jeder Sprache — nicht-englische Prompts werden automatisch übersetzt.
2. **Wählen Sie Ihre Modelle und Einstellungen** — Mehrfachauswahl aus allen verfügbaren Text-to-Image-Modellen (Amazon Bedrock + selbst gehostet auf SageMaker), wählen Sie Abmessungen, Qualitätsstufe und Region. Aktivieren Sie mehrere Modelle für einen Vergleich nebeneinander oder eines für eine fokussierte Generierung. Die Kostenschätzung aktualisiert sich in Echtzeit.
3. **Erhalten Sie wirklich unterschiedliche Optionen** — das System generiert bis zu 5 deutlich unterschiedliche kreative Konzepte (mit variierender Kleidung, Stimmung, Beleuchtung, Komposition — nicht nur dem Kamerawinkel), jeweils mit bis zu 5 Seed-Variationen (insgesamt 25 Bilder). Vom Nutzer angegebene Details werden gesperrt; von der KI abgeleitete Details werden mutig variiert.
4. **Bearbeiten und verfeinern** — nutzen Sie Inpainting, Outpainting, Radieren, Suchen & Ersetzen oder Umfärben direkt im Asset Viewer. Jede Bearbeitung erzeugt eine neue Version — das Original bleibt stets erhalten.
5. **Laden Sie spielfertige Dateien herunter** — PNG mit transparentem Hintergrund + SVG, aussagekräftig benannt (z. B. `hospital-building_opt2_var3.png`). Videos werden als MP4 exportiert.

### 📝 Stilgeführter Modus (an Ihren Kunststil & Ihr Thema anpassen)

Für Teams, die möchten, dass jedes generierte Asset zu einem vorhandenen Kunststil passt — laden Sie Referenzbilder hoch und lassen Sie die KI zunächst Ihre visuelle Identität erlernen.

1. **Laden Sie die Grafik Ihres Spiels hoch** — importieren Sie Referenzbilder aus lokalen Verzeichnissen (rekursiver Scan, per Symlink verknüpft, um Duplizierung zu vermeiden) oder aus S3-Buckets (rekursives Listing mit Paginierung). Die **intelligente Deduplizierung** läuft automatisch — sie entfernt Rotationsvarianten (barrel_N/E/S/W.png behält nur barrel_S.png) und Animations-Frames (Idle0-Idle8 behält nur Idle). So wird beispielsweise ein isometrisches Asset-Paket mit 747 Dateien auf ~99 eindeutige Objekte dedupliziert. Unterstützt: .png, .jpg, .jpeg, .gif, .bmp, .webp, .tiff, .tif, .tga, .ico, .svg sowie automatische Texturextraktion aus 3D-Modellen (.glb, .gltf).
2. **Die KI erlernt Ihren Stil** — eine zweiphasige, kohäsionsbewusste Analyse: Zuerst bestimmt eine schnelle Prüfung, ob Ihre Sammlung einheitlich, strukturell konsistent oder vielfältig ist. Anschließend erzeugt eine Tiefenanalyse des gesamten Referenzsatzes ein metadatenreiches Stilprofil — Farbpaletten, Linienstärken, Beleuchtungsmuster, Kompositionsregeln und Produktionskonventionen. Wenn Sie Generierungshinweise angeben, erhält die KI diese als „Artist's Guidance", damit die Analyse Ihre Absicht versteht, nicht nur das, was sichtbar ist.
3. **Generieren mit angewandtem Stil** — wenn Sie im Image Studio einen Stil auswählen, wird jeder Prompt automatisch mit den visuellen Direktiven Ihres Stils angereichert. Ein Prompt wie „hospital building" wird zu einer detaillierten Generierungsanweisung, die die Farbpalette, Perspektivkonventionen und den Rendering-Stil Ihres Spiels einbezieht.
4. **Alles aus dem eigenständigen Modus gilt** — mehrere Optionen, Modellvergleich, Bearbeitung, Versionierung und spielfertige Downloads funktionieren auf dieselbe Weise, nun geführt von Ihrem Kunststil.

> [!NOTE]
> Alle generierten Inhalte werden von KI-Modellen erzeugt und hängen von den Prompts und Referenzen ab, die Sie bereitstellen. Bitte lesen Sie den [Haftungsausschluss](#disclaimer) zu Inhaltsqualität, geistigem Eigentum und geltenden Servicebedingungen, bevor Sie generierte Assets in der Produktion einsetzen.

### 📝 1.1 Funktionen auf einen Blick

- 🎨 **Style Library** — Grafik hochladen, die KI erlernt Ihre visuelle Identität
- 🖼️ **2D Image Studio** — Bilder generieren mit Optionen x Variationen, geführter 3-Schritt-Prompt-Workflow
- 🎨 **Prompt Designer** — Die KI zerlegt Ihren Prompt in bearbeitbare visuelle Komponenten (Motiv, Szene, Beleuchtung, Farben) mit Sperren/Variieren-Umschaltern pro Feld, Stilintegration und intelligenter Asset-Typ-Klassifizierung. Photorealistic, Character, Environment und mehr
- 🎬 **Video Studio** — Text-to-Video mit modellspezifischer Prompt-Anleitung (Nova-Reel-Kamerasteuerung, natürliche Sprache für Luma Ray), Multi-Shot, Image-to-Video
- ✍️ **Type Studio** — KI-gestaltete Text-Overlays mit Schriftauswahl
- 💬 **Chat Studio** — Multi-Modell-LLM-Chat mit Streaming, Markdown, Code-Hervorhebung, Vision, Sitzungen, Kontext-Kompaktierung
- 📁 **Einheitliche Galerie** — Masonry-Layout, das jedes Asset in seinem echten Seitenverhältnis zeigt (Hochformat, Quadrat, Querformat — niemals beschnitten). Bilder + Videos durchstöbern, Medienfilter (Alle / 2D-Grafik / 3D-Modelle / Video), Suche, vollständige Datum-Uhrzeit-Zeitzone-Stempel, Download, Löschen. Assets, die bereits ein generiertes 3D-Modell besitzen, tragen ein **3D-Badge**, und der Filter **3D-Modelle** blendet genau diese ein
- 📥 **Bild importieren** — Bringen Sie ein vorhandenes Bild (beliebiges Format) als vollwertiges Asset in die Galerie. Automatisch in PNG konvertiert, mit einem von Ihnen gewählten Asset-Typ versehen und sofort bearbeitbar sowie 3D-bereit — alles (Versionierung, Bearbeitung, Image-to-3D) funktioniert genauso wie bei einem generierten Bild
- ✏️ **Bildbearbeitung** — Inpainting, Outpainting, Radieren, Suchen & Ersetzen, Umfärben (im AssetViewer). Jeder Modus verfügt über eine KI-Schaltfläche **Generate Prompt**: Ein Vision-Modell liest das Bild + seinen Original-Prompt und schlägt einen Bearbeitungs-Prompt vor, der auf diesen Modus und das ausgewählte Bearbeitungsmodell zugeschnitten ist (eine beschreibende Bildunterschrift für Stability-Editoren, eine Anweisung für Qwen-Image-Edit). Extend/Outpaint zeigt eine Live-Vorschau des wachsenden Rahmens mit Pixel-Linealen, sodass Sie vor dem Anwenden genau sehen, wie weit sich die Leinwand ausdehnt
- 🔄 **Echtzeit-Fortschritt** — SSE-Streaming mit Sichtbarkeit von Wiederholungen/Drosselung
- 🛡️ **Intelligente Moderation** — Canary-Test, automatischer Modellwechsel, KI-gestütztes Umschreiben
- ⚙️ **Model Registry** — Admin-UI nach Studio organisiert (Image, Video, Chat, Type, Shared), Bedrock-Erkennung, Unterstützung benutzerdefinierter Modelle
- 📝 **Prompt Templates** — 28 bearbeitbare LLM-Direktiv-Prompts, KI-gestützte Verfeinerung, Variablenvalidierung mit automatischer Korrektur
- 📦 **Asset-Versionierung** — In-Place-Bearbeitung mit Versionsverlauf (v1, v2, ...) und Versionsnavigation
- 💰 **Kostenverfolgung** — Geschätzte AWS-Ausgaben pro Anfrage, pro Sitzung, pro Asset — an die PulseBoard-Telemetrie gesendet
- 🌐 **i18n in 9 Sprachen** — Vollständige UI-Übersetzung (EN, JA, ZH, KO, HI, RU, FR, ES, DE), automatische Erkennung nicht-englischer Prompts, zweisprachige Vorschau
- 🔍 **Unterstützung benutzerdefinierter Modelle** — Automatische Erkennung von fein abgestimmten, importierten und deployten benutzerdefinierten Bedrock-Modellen
- 🔧 **Selbst gehostete Modelle — 1-Klick-Deployment** — Durchstöbern Sie einen kuratierten Katalog vorab getesteter Open-Source-Modelle (HunyuanImage 3.0, FLUX.2, FLUX.1, TripoSG und mehr), wählen Sie eine GPU-Instanz und klicken Sie auf Deploy. ArtSmoker übernimmt alles: Packaging des Inferenz-Handlers, Konfiguration der Quantisierung, Auswahl des richtigen CUDA-Toolkits, Einrichtung des Auto-Scalings, Registrierung von CloudWatch-Alarmen und Verdrahtung des asynchronen Job-Trackings. Jedes Modell im Katalog wurde durchgängig validiert — vom Kaltstart über die Generierung bis zur Auslieferung in die Galerie — sodass Sie keine GPU-Treiber, Speicherüberläufe oder Container-Kompatibilität debuggen müssen. Unterstützt BF16 + FlashInfer für beste Qualität, NF4 für Kosteneffizienz, automatische Multi-GPU-Erkennung, skaliert automatisch auf null ($0 im Leerlauf), und dasselbe Modell läuft ohne Neukonfiguration auf verschiedenen Instanztypen
- 🧊 **Image-to-3D-Generierung** — Wandeln Sie jedes Game-Asset- oder Character-Bild mit einem Klick in ein texturiertes 3D-Mesh (GLB) um. Multi-View-Synthese + Texture-Baking erzeugen spielengine-fertige Assets. Interaktiver 3D-Viewer mit Orbit/Zoom/Schwenk
- 🩹 **Intelligente Quellen-Vervollständigung für 3D** — Image-to-3D kann nur das aufbauen, was sichtbar ist, sodass ein zugeschnittener Charakter (abgeschnittene Beine) zu einem beinlosen Mesh wird. Vor der Generierung prüft ArtSmoker die Quelle per Vision und **bietet** an, sie bei Zuschnitt per Outpainting zu vervollständigen (ein KI-vorgeschlagener, vollständig bearbeitbarer Prompt) — zeigt eine Vorher/Nachher-Vorschau, prüft das Ergebnis erneut, lässt Sie erneut erweitern oder verwerfen und speichert es als neue Bildversion. Opt-in und nicht blockierend; gut gerahmte Bilder werden direkt generiert
- 🔄 **Auto-Update** — Versionsgesteuertes Git-Pull beim Start, Selbst-Neustart bei Update, 24-Stunden-Periodenprüfung (`ARTSMOKER_AUTO_UPDATE=false` zum Deaktivieren)

### 📝 1.2 Screenshots

**2D Image Studio** — Einstellungen links mit Mehrfachauswahl-Dropdown für Modelle, Asset-Typ, Abmessungen und Nachbearbeitungsoptionen. 3-Schritt-Prompt-Workflow rechts mit den Schaltflächen Prompt Designer und Generate Enhanced Prompt. IP-Erklärung und Kostenschätzung unten.

![2D Image Studio — Einstellungen, Prompt-Workflow und Generierungssteuerung](docs/images/image-studio-top.png)

**2D Image Studio — Generierungsergebnisse** — Der verbesserte Prompt wird oben angezeigt, die Multi-Modell-Vergleichsergebnisse darunter. Jedes Modell generiert unabhängig mit modellspezifischer Prompt-Optimierung. Die Ergebnisse zeigen Modellname, Abmessungen und Generierungskosten.

![2D Image Studio — Verbesserter Prompt und Generierungsergebnisse](docs/images/image-studio-results.png)

**2D Image Studio — Modellvergleich** — Vergleichsraster nebeneinander über alle ausgewählten Modelle (7 Modelle abgebildet). Variationen der ausgewählten Option werden darunter angezeigt. Nachbearbeitungs-Umschalter (Hintergrund entfernen, In SVG konvertieren, Hochskalieren) links.

![2D Image Studio — Multi-Modell-Vergleichsraster mit Variationen](docs/images/image-studio-comparison.png)

**Prompt Designer** — Die KI zerlegt Ihren Prompt in bearbeitbare visuelle Komponenten (Motiv, Szene, Komposition, Beleuchtung, Stil & Farben). Jedes Feld kann einzeln mit Sperren/Variieren-Steuerelementen für wirklich unterschiedliche kreative Optionen bearbeitet werden.

![Prompt Designer — Strukturierte visuelle Dekomposition mit bearbeitbaren Feldern](docs/images/prompt-designer-top.png)

**Prompt Designer — Farbpalette** — Benannte Farbpaletten mit Hex-Farbmustern, Stil-Schlüsselwörtern und Qualitätsstufen-Steuerung. Die KI erlernt Ihre visuelle Identität und wendet sie konsistent über alle Generierungen hinweg an.

![Prompt Designer — Farbpalette, Stil-Schlüsselwörter und Qualitätssteuerung](docs/images/prompt-designer-bottom.png)

**Style Library** — Laden Sie die vorhandene Grafik Ihres Spiels hoch, die KI analysiert den visuellen Stil und erstellt einen metadatenreichen Prompt-Leitfaden. Referenzbilder werden mit der vollständigen KI-Analyse und dem JSON-Stilprofil angezeigt.

![Style Library — KI-Stilanalyse mit Referenzbildern](docs/images/style-library-top.png)

![Style Library — Referenzbilder, Importoptionen und Analysedaten](docs/images/style-library-bottom.png)

**Galerie** — Einheitliche Ansicht aller generierten Bilder und Videos mit Medientyp-Filter, Stilfilter, Suche und Sortierung. Klicken Sie auf ein beliebiges Asset, um den vollständigen Viewer zu öffnen. Die Schaltfläche **Bild importieren** bringt ein vorhandenes Bild in die Galerie — wählen Sie einen Asset-Typ (Character/Game Asset aktivieren 3D), und es wird in PNG konvertiert und sofort bearbeitbar sowie 3D-bereit gemacht.

![Galerie — Raster generierter Assets mit Filtern](docs/images/gallery.png)

**Asset Viewer** — Vorschau in voller Größe mit Registerkarten-Oberfläche (PNG, Bearbeiten, SVG, Metadaten, 3D-Modell). Laden Sie PNG und SVG direkt herunter. Das Compositing des transparenten Hintergrunds wird mit einem Schachbrettmuster dargestellt.

![Asset Viewer — Vorschau in voller Größe mit Download-Optionen](docs/images/asset-viewer.png)

**Asset Viewer — Bildbearbeitung** — Registerkarte „Bearbeiten" mit Inpainting: Malen Sie eine Maske über den zu ändernden Bereich, beschreiben Sie, was Sie möchten, wählen Sie ein Bearbeitungsmodell und wenden Sie es an. Versionsverlauf bleibt erhalten — Originale werden nie überschrieben.

![Asset Viewer — Inpainting mit Maske und Prompt](docs/images/asset-viewer-edit.png)

**3D-Modell-Generierung** — Wandeln Sie jedes Game-Asset- oder Character-Bild in ein texturiertes 3D-Mesh (GLB) um. Konfigurieren Sie die Marching-Cubes-Auflösung, das Vordergrundverhältnis und die Generierungsparameter direkt in der Registerkarte „3D-Modell" des Asset Viewers.

![3D-Modell-Generierung — Einstellungen und Generierung im Asset Viewer](docs/images/3d-model-generation.png)

**Video Studio** — Einstellungen links (Modell, Generierungsmodus, Dauer, Region, Kostenschätzung), Prompt rechts. Unterstützt Nova Reel (Einzelaufnahme, Multi-Shot auto/manuell bis zu 2 Minuten) und Luma AI Ray (Seitenverhältnisse, Loop).

![Video Studio — Einstellungen und Prompt](docs/images/video-studio.png)

![Video Studio — Generierung mit KI-verbessertem Prompt läuft](docs/images/video-studio-generating.png)

![Video Studio — Fertiges Video mit Vorschaubild und neuesten Videos](docs/images/video-studio-completed.png)

**Videoplayer** — Klicken Sie auf ein Video, um es inline mit vollständigen Metadaten (Original-Prompt, KI-verbesserter Prompt, Modell, Dauer, Region) abzuspielen.

![Videoplayer — Wiedergabe eines generierten Videos mit Metadaten](docs/images/video-player.png)

### 📝 1.3 Zweistufige Generierung

Für jeden Prompt erstellt die KI **Optionen** — grundlegend unterschiedliche Design-Interpretationen (z. B. für „a warrior": Wikinger-Berserker, japanischer Samurai, Stammeskrieger, Cyber-Soldat, griechischer Hoplit). Für jede Option erzeugt das Bildmodell **Variationen** — verschiedene Zufalls-Seeds mit subtilen visuellen Unterschieden. Das gibt Künstlern eine breite kreative Palette zur Auswahl.

### 📝 1.4 Multi-Modell-Auswahl

Das Modell-Dropdown unterstützt **checkbox-basierte Mehrfachauswahl** — wählen Sie eine beliebige Kombination von Modellen für einen einzelnen Generierungslauf:

- **Einzelnes Modell** — aktivieren Sie ein Modell für eine fokussierte Generierung (am schnellsten, am günstigsten)
- **Mehrere Modelle** — aktivieren Sie 2-3 spezifische Modelle für einen gezielten Vergleich (z. B. nur SD 3.5 + FLUX.2)
- **All Available Models** — der Umschalter unten wählt alle aktivierten Modelle für einen vollständigen Vergleich nebeneinander an bzw. ab

Jedes Modell läuft unabhängig: Wenn strengere Modelle den Prompt blockieren, erhalten Sie dennoch Ergebnisse von Modellen, die ihn akzeptiert haben, mit klaren Statuskennzeichnungen (erfolgreich, durch Moderation blockiert oder fehlgeschlagen) auf jeder Options-Karte. Die Kostenschätzung aktualisiert sich in Echtzeit, während Sie Modelle an- und abwählen.

Ein optionaler Umschalter **„Model-optimized prompts"** passt den Prompt an die Stärken jedes Modells an — Prompts werden pro Modell umgeschrieben (z. B. Qualitäts-Booster für SD 3.5, natürliche Sprache für FLUX.2, prägnante Bildunterschriften für Qwen-Image).

### 📝 1.5 Video Studio

Generieren Sie KI-gestützte Videos und Animationen aus Text-Prompts. Unterstützt **Amazon Nova Reel** (v1.0, v1.1) und **Luma AI Ray** (v2.0).

| Funktion | Nova Reel | Luma Ray v2 |
|----------|-----------|-------------|
| **Max. Dauer** | 120s (2 Minuten) | 9 Sekunden |
| **Auflösung** | 1280x720 | 720p / 540p |
| **Seitenverhältnisse** | nur 16:9 | 7 Optionen (1:1, 16:9, 9:16 usw.) |
| **Image-to-Video** | Ja (Startframe) | Ja (Start- + Endframe) |
| **Loop-Video** | Nein | Ja |
| **Multi-Shot-Steuerung** | Ja (auto + manuell) | Nein |
| **Preis** | ~$0.08/Sek. | ~$1.50/Sek. |

**So funktioniert es:**
1. Wählen Sie ein Videomodell und konfigurieren Sie Dauer, Seitenverhältnis, Region
2. Geben Sie einen Prompt ein — die KI reichert ihn mit filmischem Vokabular, Kamerabewegungen und Hinweisen zur zeitlichen Kohärenz an
3. Klicken Sie auf Generate — der Job läuft asynchron über `StartAsyncInvoke`, die Ausgabe geht in Ihren konfigurierten S3-Bucket
4. Statusabfrage alle 5 Sekunden — bei Abschluss wird ein Vorschaubild extrahiert (über ffmpeg) und die MP4 lokal heruntergeladen (oder aus S3 gestreamt)
5. Videos erscheinen sowohl im Bereich „Recent Videos" des Video Studios als auch in der einheitlichen Galerie

**S3-Bucket erforderlich**: Die Videogenerierung gibt Ausgaben nach S3 aus. Sie können dies über Video Settings in der UI konfigurieren (vorhandene Buckets durchsuchen oder neu erstellen) oder einen über das CLI erstellen:

```bash
# Einen S3-Bucket für Videospeicher erstellen (REGION und YOUR_ORG ersetzen)
aws s3api create-bucket --bucket artsmoker-video-YOUR_ORG --region us-east-1

# Für andere Regionen als us-east-1 den LocationConstraint hinzufügen:
aws s3api create-bucket --bucket artsmoker-video-YOUR_ORG --region us-west-2 \
  --create-bucket-configuration LocationConstraint=us-west-2
```

Speichermodus: lokaler Download (Standard) oder Streaming aus S3 bei Bedarf.

**Verbesserung von Video-Prompts**: Das LLM fügt Kamerabewegungen (Schwenk, Zoom, Dolly, Tracking), Beleuchtungsdetails und zeitliche Hinweise hinzu. Da Videomodelle keine Negativ-Prompts unterstützen, werden zu vermeidende Konzepte auf natürliche Weise in den positiven Prompt eingewoben.

### 📝 1.6 Chat Studio

Eine voll ausgestattete LLM-Chat-Oberfläche — wie eine selbst gehostete konversationelle KI, die in Ihrem eigenen AWS-Konto läuft, ohne Datenzugriff durch Dritte.

**80+ Modelle von 16 Anbietern** — Claude (Sonnet, Opus, Haiku), Amazon Nova, Meta Llama, Mistral, Cohere, Qwen, DeepSeek, Google Gemma, NVIDIA Nemotron und mehr. Plus alle benutzerdefinierten/importierten Modelle in Ihrem Konto. Alle automatisch über Sync from AWS erkannt.

**Kernfunktionen:**
- **Streaming-Antworten** — Echtzeit-Rendering Token für Token über Bedrock ConverseStream
- **Markdown-Rendering** — Überschriften, fett/kursiv, Listen, Tabellen, Blockzitate, horizontale Linien
- **Code-Blöcke** — Syntaxhervorhebung (highlight.js) mit Sprach-Badge + Kopier-Schaltfläche
- **Metriken pro Nachricht** — Eingabe-/Ausgabe-Tokens, Latenz, geschätzte Kosten, verwendetes Modell
- **Kontextfenster-Leiste** — visueller Füllstandsanzeiger (grün/gelb/rot) mit Zähler der verwendeten/maximalen Tokens
- **Regionswechsel** — jedes Modell zeigt alle verfügbaren Regionen an, wählen Sie die nächste oder günstigste

**Sitzungsverwaltung:**
- Mehrere gleichzeitige Sitzungen mit automatischem Speichern
- Inline-Umbenennen, Duplizieren, Löschen, Suchen/Filtern in der Seitenleiste
- Export von Konversationen als Markdown
- Sitzungssummen: Token-Anzahl, geschätzte Kosten, Nachrichtenanzahl

**Erweiterte Funktionen:**
- **System-Prompt-Vorlagen** — General Assistant, Coding Expert, Creative Writer, Game Designer, Data Analyst, Technical Writer
- **Vision/Multimodal** — Drag-and-Drop, Dateiauswahl oder Ctrl+V zum Einfügen von Bildern für vision-fähige Modelle
- **Kontext-Kompaktierung** — die KI fasst ältere Nachrichten zusammen, um Platz im Kontextfenster freizugeben
- **Neu generieren** — jede KI-Antwort mit demselben Prompt erneut ausführen
- **Bearbeiten & erneut senden** — jede Nutzernachricht ändern und ab diesem Punkt erneut abspielen
- **Fork** — eine Konversation von einer beliebigen Nachricht in eine neue Sitzung verzweigen

**Preistransparenz:** Der Modell-Auswähler zeigt die Kosten pro 1K Tokens an, die Preisinfo-Leiste zeigt die geschätzten Kosten für Konversationen mit 10K und 100K Tokens.

### 📝 1.7 Asset-Typ-Bewusstsein

Der ausgewählte **Asset-Typ** verändert grundlegend, wie die KI Ihren Prompt interpretiert — nicht nur das Bildmodell, sondern jede Stufe der Pipeline. Wenn Sie „hospital" eingeben und verschiedene Asset-Typen wählen, erhalten Sie völlig unterschiedliche Ergebnisse:

| Typ | Komposition | Rahmung | Technischer Ansatz |
|-----|-------------|---------|-------------------|
| **Game Asset** | Einzelnes isoliertes Objekt auf transparentem Hintergrund. Keine Szene, kein Text, keine UI. | Frontal oder isometrisch, Objekt füllt 70-80% des Rahmens. | Saubere, scharfe Kanten für die Hintergrundentfernung, konsistente Beleuchtung von oben links, keine Bodenschatten. Für die Komposition mit anderen Spiele-Assets in verschiedenen Maßstäben konzipiert. |
| **Character** | Ganzkörper- oder 3/4-Körper-Figur, isoliert auf sauberem Hintergrund. Nur ein Charakter. | Charakter füllt 60-75% vertikal, Kopf bis Fuß, leicht außermittig. | Starke, lesbare Silhouette (allein an der Silhouette erkennbar), ausdrucksstarke Pose, die Persönlichkeit vermittelt, klare Gesichtszüge und Kostümdetails. |
| **Icon** | Einzelnes, kräftiges, erkennbares Symbol, zentriert mit großzügigem Abstand. Maximale Einfachheit. | Frontal oder leichte 3/4-Neigung, Freiraum an den Rändern. | Muss bei 64x64 Pixeln klar lesbar sein. Hoher Kontrast, maximal 3-5 Farben, kräftige Formen, keine dünnen Linien oder feinen Details. |
| **Marketing Banner** | Vollständige szenische Illustration mit dramatischer Komposition. Saubere, textsichere Zone auf einer Seite reserviert — kein gerenderter Text oder Typografie. | Breites, filmisches Gefühl, Kamera zurückgezogen, um eine Szene zu zeigen. | Reiche, gesättigte Farben, dramatische Beleuchtung (Rim Light, volumetrische Strahlen), Tiefenschärfe. Die KI wird ausdrücklich angewiesen, KEINEN Text zu rendern; die textsichere Zone bleibt sauber für das Post-Production-Overlay in Design-Tools (Figma, Canva usw.). |
| **Environment** | Vollständige Landschaft mit Tiefenebenen aus Vordergrund/Mittelgrund/Hintergrund, Führungslinien. | Weite Establishing-Aufnahme, Horizont im oberen oder unteren Drittel. | Atmosphärische Perspektive (entfernte Objekte heller/dunstiger), Umgebungserzählung durch Details, stimmungssetzende Beleuchtung. |

Das ist in jeder Phase von Bedeutung:

- **Schaltfläche „Preview Enhanced Prompt"** — Wenn Sie auf Compose klicken, nutzt die KI den Asset-Typ, um Ihr Briefing in einen detaillierten Generierungs-Prompt umzuformen und Ihre Worte mit Stilrichtlinien und Asset-Typ-Direktiven zu kombinieren. Ihre explizite Absicht überschreibt immer die Stil-Standardwerte. Sie können die zusammengesetzte Version vor der Generierung überprüfen.
- **Konzeptgenerierung** — Bei der Generierung mehrerer Optionen erstellt die KI N verschiedene Design-Interpretationen, die alle die strukturellen Regeln des Asset-Typs respektieren. Eine Character-Option hat immer eine lesbare Silhouette; eine Marketing-Banner-Option hat immer eine textsichere Zone ohne gerenderten Text.
- **Das Ergebnis** — Zwei Bilder aus demselben Prompt, aber mit unterschiedlichen Asset-Typen sehen völlig anders aus. Ein Game-Asset-„warrior" ist ein einzelnes, zentriertes Charakter-Sprite. Ein Marketing-Banner-„warrior" ist eine epische Schlachtszene mit einer sauberen Zone für ein Schlagzeilen-Overlay.

### 📝 1.8 3D-Modell-Generierung (Image-to-3D)

Generieren Sie produktionsreife, vollständig texturierte 3D-Meshes aus jedem 2D-Bild — direkt im Asset Viewer. Wählen Sie ein **Game Asset**- oder **Character**-Bild, öffnen Sie die Registerkarte **3D Model** und klicken Sie auf Generate. Das Ergebnis ist eine spielengine-fertige GLB, die Sie umkreisen, zoomen und herunterladen können — ohne manuelle Modellierung, UV-Unwrapping oder Texture-Painting.

**Das generierte Modell — umkreisen, inspizieren, herunterladen:**

![3D-Modell-Generierung — das generierte Soldaten-Mesh aus mehreren Blickwinkeln im interaktiven 3D-Viewer betrachtet](docs/images/3d-model-result.png)

Ein einzelnes 2D-Charakterbild (links, in der Registerkarte PNG) wird zu einem vollständig texturierten 3D-Mesh, das Sie im Browser frei drehen können. Die Registerkarte **3D Model** listet nun auch die genauen **Modelle & Werkzeuge** auf, die zur Erstellung jedes Assets verwendet wurden (Geometriemodell, Texturierungs-Backend, Ausgabetyp, Instanz und Generierungsparameter) — in den Metadaten des Assets für eine vollständige Nachvollziehbarkeit gespeichert.

**Zwei Pipelines — Ihre Wahl.** ArtSmoker bietet zwei Wege, ein Bild in ein texturiertes 3D-Modell zu verwandeln. Deployen Sie eine (oder beide) über Custom Models; wenn beide aktiv sind, wählen Sie pro Generierung im Asset Viewer — jede zeigt ihre geschätzten Kosten, Zeit und Lizenz, damit Sie informiert entscheiden:

| Pipeline | Funktionsweise | Lizenz | Kommerzielle Nutzung | Ideal für |
|----------|----------------|--------|----------------------|-----------|
| **TripoSG + Texturierungs-Backend** | TripoSG baut das Mesh; ein gewähltes Texturierungs-Backend (TRELLIS.2 / Hunyuan3D-Paint) bemalt es | je Backend (unten) | je Backend | Kombination von Geometrie + einem bestimmten Texturierer |
| **TRELLIS.2 (Full)** | Ein einziges Modell generiert **sowohl** Geometrie als auch PBR-Textur (SLAT) | MIT | ✅ Ja — Attribution „Built with DINOv3" | Produktion, kommerzielle Assets, einfachster Weg |

**So funktioniert die TripoSG-Pipeline:**

1. **Geometrie-Extraktion** — ein Rectified-Flow-Transformer (TripoSG, 1,5 Mrd. Parameter, MIT-lizenziert) wandelt ein einzelnes 2D-Bild mithilfe einer Signed-Distance-Field-Darstellung (SDF) in ein hochauflösendes 3D-Mesh um. Die Mesh-Dichte skaliert mit dem Qualitäts-Preset (bis zu ~1 Mio. Faces bei höchster Octree-Auflösung) für gestochen scharfe Details an Gesichtern und Ausrüstung.
2. **Texturierung** — das Mesh wird von einem **Texturierungs-Backend bemalt, das Sie beim Deployment wählen** (Standard **TRELLIS.2**, Microsoft, MIT — ein SLAT/Voxel-konditionierter Texturierer, der vollständige PBR-Materialien in einem 4096²-Atlas erzeugt).
3. **PBR-Ausgabe** — exportiert als GLB mit eingebetteten PBR-Maps, bereit für physikalisch basiertes Rendering in jeder modernen Engine.

Die **TRELLIS.2 (Full)**-Pipeline erledigt dasselbe durchgängig in einem einzigen Modell — ohne separaten Texturierungsschritt.

**Lizenz gut sichtbar — beim Deployment UND bei der Generierung.** Jede deploybare Option zeigt ihre **vollständige Lizenz- und Abhängigkeitsaufschlüsselung** im Deploy-Dialog — jedes Modell, das sie herunterlädt, dessen Lizenz und ob es kommerziell unbedenklich oder zugriffsbeschränkt ist — und Sie lesen und akzeptieren dies vor dem Deployment. Zum Zeitpunkt der Generierung zeigt der Asset Viewer die Lizenz erneut an und bestätigt *„akzeptiert beim Deployment am `<date>`"* (kein zweiter Klick nötig):

| Texturierungs-Backend | Lizenz | Kommerzielle Nutzung | Ideal für |
|-----------------------|--------|----------------------|-----------|
| **TRELLIS.2** *(Standard)* | MIT | ✅ Ja — erfordert eine Attribution „Built with DINOv3" in Ihrem Produkt | Produktion, kommerzielle Assets, höchste Qualität |
| **Hunyuan3D-Paint** | Tencent Community | ❌ Nicht kommerziell | Forschung / nicht kommerziell, außergewöhnliche Gesichter |

Die Hintergrundentfernung (der Freistell-Schritt) verwendet standardmäßig **BiRefNet (MIT)** — vollständig kommerziell unbedenklich — mit einer nicht kommerziellen Alternative (RMBG), die als offengelegtes Opt-in verfügbar ist. ArtSmoker lädt niemals stillschweigend eine eingeschränkte Abhängigkeit herunter: Alles, was zugriffsbeschränkt oder nicht kommerziell ist, wird benannt, mit einem Badge versehen und hinter einer expliziten Zustimmung geschützt.

**Ausgabe:** Standard-GLB mit eingebetteten PBR-Texturen — importiert direkt in Unity, Unreal Engine, Blender und andere Spiele-Engines. Der interaktive 3D-Viewer unterstützt Orbit, Zoom und Schwenk zur sofortigen Inspektion, und die Registerkarte **3D Model** listet die genauen verwendeten Modelle & Werkzeuge auf (Geometriemodell, Texturierungs-Backend, Abhängigkeiten, Instanz, Parameter) für eine vollständige Nachvollziehbarkeit.

**Infrastruktur:** Beide Pipelines werden über denselben 1-Klick-Custom-Models-Flow deployt, wobei der Auswähler zum Deployment-Zeitpunkt für jede Option die Lizenz, die Abhängigkeitstabelle, die Basisinstanz und die geschätzten Kosten/Zeiten anzeigt. Die passgenaue Basisinstanz der vollständigen TRELLIS.2-Pipeline ist **`ml.g6e.xlarge`** (~$2.61/Std.; gemessener Spitzenwert ~6,5 GB VRAM + ~22 GB Host-RAM — der Host-RAM ist die bindende Einschränkung, nicht die GPU). Größere `g6e`-Größen werden als RAM-Reserve-Upsells angeboten. Endpoints skalieren im Leerlauf auf null — $0 Kosten zwischen Jobs. Der erste Kaltstart baut die CUDA-Erweiterungen einmalig (danach in S3 zwischengespeichert für schnelle Neustarts). Vor dem Deployment eines zugriffsbeschränkten Modells **prüft der Dialog vorab den HuggingFace-Zugriff für jedes Repo, das es herunterlädt** und zeigt pro Repo ein ✓/✗ mit dem genauen nächsten Schritt — sodass Sie nie erst Minuten nach Beginn eines Kaltstarts eine fehlende Lizenzzustimmung entdecken.

> **Anzeige der GLB:** Texturen sind als WebP kodiert (`EXT_texture_webp`), um Dateien kompakt zu halten — wird im In-App-Viewer, in Blender 4.x, three.js und modernen Unity/Unreal-Importern perfekt gerendert. macOS Preview/QuickLook unterstützt WebP-in-glTF nicht und zeigt das Modell schwarz an; nutzen Sie den In-App-Viewer oder ein beliebiges modernes glTF-Werkzeug.

| Metrik | Wert |
|--------|------|
| Mesh-Qualität | Bis zu ~1 Mio. Faces, vollständige Vertex-Normalen |
| Texturauflösung | 4096²-PBR-Atlas (Base Color + Metallic-Roughness + Alpha) |
| Lizenzierung | Standardmäßig kommerziell unbedenklich (TRELLIS.2 MIT + BiRefNet MIT); nicht kommerzielle Backends mit vollständiger Offenlegung angeboten |
| Unterstützte Asset-Typen | Game Asset, Character |

<a id="get-started"></a>

## 📌 2. Voraussetzungen

- **Python 3.11+** (3.12, 3.13, 3.14 funktionieren alle)
- **AWS CLI** mit funktionierenden Anmeldeinformationen konfiguriert
- **IAM-Berechtigungen** für den Bedrock-Zugriff (siehe unten)

### 📝 2.1 AWS-Anmeldeinformationen

ArtSmoker verwendet die [Standard-Anmeldeinformationsauflösung von boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials), sodass alle folgenden Methoden funktionieren:

| Methode | Ideal für | Wie |
|---------|-----------|-----|
| **Umgebungsvariablen** | CI/CD, Container | `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` |
| **Gemeinsame Anmeldeinformationsdatei** | Lokale Entwicklung | `~/.aws/credentials` über `aws configure` |
| **Benanntes Profil** | Mehrere Konten | `ARTSMOKER_AWS_PROFILE=myprofile` oder `AWS_PROFILE` setzen |
| **AWS SSO** | Unternehmens-SSO | `aws configure sso` |
| **IAM Instance Profile** | EC2, ECS, App Runner | Hängen Sie eine IAM-Rolle an die Instanz an — keine Anmeldeinformationen auf der Maschine nötig |
| **ECS Task Role** | ECS/Fargate-Container | Weisen Sie eine Task-Ausführungsrolle mit den erforderlichen Berechtigungen zu |

Schnelle Prüfung, ob die Anmeldeinformationen funktionieren:

```bash
aws sts get-caller-identity
```

> [!NOTE]
> Auf EC2 und anderen AWS-Compute-Diensten müssen Sie keine expliziten Anmeldeinformationen konfigurieren. Hängen Sie ein [IAM Instance Profile](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2_instance-profiles.html) mit den erforderlichen Berechtigungen an, und boto3 übernimmt es automatisch über den Instance-Metadata-Service.

### 📝 2.1.1 Bedrock-Zugriff überprüfen

Die Bestätigung, dass Anmeldeinformationen funktionieren (`sts:GetCallerIdentity`), verifiziert nur die Identität — sie bestätigt nicht, dass Sie über Bedrock-Berechtigungen verfügen. ArtSmoker verwendet mehrere Bedrock-APIs, daher reicht ein schneller Listing-Test allein nicht aus. Die zuverlässigste Prüfung:

```bash
# Test 1: Können Sie Modelle auflisten? (erfordert bedrock:ListFoundationModels)
aws bedrock list-foundation-models --region us-east-1 --query "modelSummaries[0].modelId" --output text

# Test 2: Können Sie ein Bildmodell aufrufen? (erfordert bedrock:InvokeModel)
aws bedrock-runtime invoke-model --region us-west-2 \
  --model-id stability.sd3-5-large-v1:0 \
  --content-type application/json --accept application/json \
  --body '{"prompt":"test","aspect_ratio":"1:1"}' \
  /dev/null 2>&1 && echo "InvokeModel: OK" || echo "InvokeModel: FAILED"

# Test 3: Können Sie die Converse-API verwenden? (erfordert bedrock:Converse)
# (Ersetzen Sie durch eine beliebige Claude-Modell-ID, auf die Sie Zugriff haben — z. B. das
#  aktuelle Sonnet-Inferenzprofil aus der Liste von Test 1; die genaue Version ändert sich mit der Zeit.)
aws bedrock-runtime converse --region us-west-2 \
  --model-id us.anthropic.claude-sonnet-4-6 \
  --messages '[{"role":"user","content":[{"text":"hi"}]}]' \
  --inference-config '{"maxTokens":1}' \
  --query "output.message.content[0].text" --output text 2>&1 && echo "Converse: OK" || echo "Converse: FAILED"

# Test 4: Können Sie benutzerdefinierte Modelle auflisten? (erfordert bedrock:ListCustomModels)
aws bedrock list-custom-models --region us-east-1 \
  --query "modelSummaries[0].modelName" --output text 2>&1 && echo "ListCustomModels: OK" || echo "ListCustomModels: keine benutzerdefinierten Modelle (oder Berechtigung verweigert)"
```

Wenn die Tests 1-3 bestehen, sind Ihre Kernberechtigungen eingerichtet. Test 4 wird nur für die Erkennung benutzerdefinierter Modelle benötigt. Wenn Test 1 besteht, aber die Tests 2-3 fehlschlagen, erlaubt Ihre IAM-Richtlinie das Auflisten, aber nicht das Aufrufen — aktualisieren Sie sie anhand der Berechtigungstabelle unten.

### 📝 2.2 IAM-Berechtigungen

Ihr IAM-Benutzer, Ihre Rolle oder Ihr Instance-Profil benötigt diese Berechtigungen:

| Berechtigung | Verwendet für |
|--------------|---------------|
| `bedrock:InvokeModel` | Bildgenerierung, Bildbearbeitung, Nachbearbeitung (alle Bildmodelle) |
| `bedrock:Converse` | LLM-Aufrufe — Prompt-Verfeinerung, Stilanalyse, Konzeptgenerierung |
| `bedrock:InvokeModelWithBidirectionalStream` | Sprachtranskription (optional — die App funktioniert auch ohne) |
| `bedrock:StartAsyncInvoke` | Videogenerierung (asynchroner Aufruf) |
| `bedrock:GetAsyncInvoke` | Status von Videogenerierungs-Jobs abfragen |
| `bedrock:ListAsyncInvokes` | Videogenerierungs-Jobs auflisten |
| `bedrock:ListFoundationModels` | Erkennung von Foundation-Modellen (Sync from AWS) |
| `bedrock:ListCustomModels` | Fein abgestimmte benutzerdefinierte Modelle in Ihrem Konto erkennen |
| `bedrock:ListImportedModels` | Importierte Modelle in Ihrem Konto erkennen |
| `bedrock:GetCustomModel` | Details benutzerdefinierter Modelle lesen (Basismodell, Status) |
| `bedrock:GetImportedModel` | Details importierter Modelle lesen (Architektur, Status) |
| `bedrock:ListProvisionedModelThroughputs` | Aufrufbare benutzerdefinierte Modelle mit bereitgestelltem Durchsatz finden |
| `bedrock:ListCustomModelDeployments` | Benutzerdefinierte Modelle mit On-Demand-Deployments finden |
| `bedrock:CreateInference` *(oder Richtlinie `AmazonBedrockMantleInferenceAccess`)* | **Amazon Bedrock Mantle** — Frontier-Modelle, die nur über den Mantle-Endpoint erreichbar sind (OpenAI GPT‑5.x, Claude Mythos, GLM, Grok, Qwen, Gemma…). Fehlt sie, betrifft dies nur diese Modelle; Claude über Converse funktioniert weiterhin. |
| `account:ListRegions` | Nur die **aktivierten** Regionen Ihres Kontos während des Sync scannen (schnell, keine Fehler bei Opt‑in-Regionen). Optional — fällt auf das Scannen aller Regionen zurück. |
| `account:GetRegionOptStatus` | Opt‑in-Status pro Region lesen (Begleiter zu `account:ListRegions`). Optional. |
| `s3:CreateBucket` | S3-Bucket für Videospeicher erstellen (optional, über die UI) |
| `s3:PutObject` / `s3:GetObject` / `s3:DeleteObject` / `s3:ListBucket` | Speicherung und Abruf der Videoausgabe |
| `aws-marketplace:Subscribe` | Automatisches Abonnement bei erster Nutzung von Drittanbieter-Modellen (inkl. Drittanbieter-Mantle-Modelle) |
| `aws-marketplace:ViewSubscriptions` | Bestehende Modell-Abonnements prüfen |
| `sts:GetCallerIdentity` | Validierung der Anmeldeinformationen beim Start; untermauert auch das lokal signierte Mantle-Bearer-Token |
| `pricing:GetProducts` | Modellpreise während Sync from AWS abrufen (optional) |
| `sagemaker:*` | Selbst gehostete benutzerdefinierte Modelle auf Amazon SageMaker (optional — nur bei Nutzung von Custom Models) |
| `iam:PassRole` | Amazon SageMaker erlauben, Ihre Rolle zu verwenden (optional — nur für Custom Models) |
| `iam:CreateRole` / `iam:AttachRolePolicy` | Amazon-SageMaker-Ausführungsrolle beim ersten Deployment automatisch erstellen (optional — nur für Custom Models) |
| `iam:GetRole` / `iam:UpdateAssumeRolePolicy` | Vorhandene Rolle für Amazon-SageMaker-Vertrauensstellung automatisch konfigurieren (optional) |
| `secretsmanager:CreateSecret` / `secretsmanager:GetSecretValue` / `secretsmanager:DeleteSecret` | Verschlüsselte Speicherung von HuggingFace-Tokens für zugriffsbeschränkte Modelle (optional — wird beim Teardown automatisch bereinigt) |

**Schnellste Einrichtung** (verwaltete Richtlinien — breitester Zugriff):

```bash
# Option A: Verwaltete Richtlinien an Ihren IAM-Benutzer anhängen (am einfachsten für die lokale Entwicklung)
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

# Amazon Bedrock Mantle-Endpoint — benötigt für Frontier-Modelle (OpenAI GPT-5.x,
# Claude Mythos, GLM, Grok usw.). Überspringen Sie dies nur, wenn Sie keine reinen Mantle-Modelle verwenden.
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockMantleInferenceAccess

# S3-Zugriff für Videospeicher hinzufügen
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

**Eingeschränkte Einrichtung** (engere Berechtigungen — für die Produktion empfohlen):

```bash
# Eine eingeschränkte IAM-Richtlinie mit nur den von ArtSmoker benötigten Berechtigungen erstellen
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

# An Ihren IAM-Benutzer anhängen (YOUR_ACCOUNT_ID und YOUR_USERNAME ersetzen)
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/ArtSmokerAccess
```

> [!TIP]
> **Für EC2/ECS/App Runner** — erstellen Sie eine IAM-Rolle, anstatt sie an einen Benutzer anzuhängen. Vollständige Befehle zur Rollenerstellung finden Sie im Abschnitt [EC2-Deployment](#43-ec2--cloud-deployment). Es werden keine Zugriffsschlüssel benötigt — boto3 erkennt die Rolle automatisch über den Instance-Metadata-Service.

> [!NOTE]
> Bedrock-Modelle sind standardmäßig in allen kommerziellen AWS-Regionen verfügbar — es ist kein manueller Aktivierungsschritt erforderlich. Beim ersten Aufruf eines Drittanbieter-Modells (Anthropic, Stability AI) leitet AWS automatisch im Hintergrund ein Marketplace-Abonnement ein (erfordert die oben genannten `aws-marketplace`-Berechtigungen). Anthropic-Modelle erfordern das einmalige Ausfüllen eines [First-Time-Use-Formulars](https://console.aws.amazon.com/bedrock/home#/modelaccess).

### 📝 2.3 Optional: SVG-Konvertierungswerkzeuge

Die SVG-Konvertierung nutzt externe CLI-Werkzeuge (keine Python-Pakete). Ohne diese fällt die SVG-Ausgabe auf einen Pillow-basierten Raster-in-SVG-Wrapper zurück — funktional, aber keine echte Vektorausgabe.

| Werkzeug | Zweck | macOS | Linux (Debian/Ubuntu) | Windows |
|----------|-------|-------|-----------------------|---------|
| **vtracer** | Primäres SVG (Farbvektor-Tracing) | `pip install vtracer` oder `cargo install vtracer` | `pip install vtracer` oder `cargo install vtracer` | `pip install vtracer` oder `cargo install vtracer` oder [vorkompilierte Binaries](https://github.com/visioncortex/vtracer/releases) |
| **potrace** | Fallback-SVG (Monochrom-Tracing) | `brew install potrace` | `sudo apt install potrace` | Download von [potrace.sourceforge.net](http://potrace.sourceforge.net/#downloading) |

Installation überprüfen:

```bash
# SVG-Konvertierungswerkzeuge prüfen
which vtracer && echo "vtracer: OK" || echo "vtracer: not installed (optional)"
which potrace && echo "potrace: OK" || echo "potrace: not installed (optional)"
```

### 📝 2.4 Optional: Werkzeuge für Video-Vorschaubilder & Metadaten

Video Studio generiert MP4-Videos über Amazon Nova Reel und Luma AI Ray. Um Vorschaubilder (erster Frame als JPEG) und Video-Metadaten (Dauer, Auflösung, FPS) zu extrahieren, müssen **ffmpeg** und **ffprobe** auf der Maschine installiert sein, auf der das ArtSmoker-Backend läuft.

Ohne ffmpeg:
- Videos werden weiterhin korrekt generiert und abgespielt (aus S3 gestreamt oder als MP4 heruntergeladen)
- Vorschaubilder fehlen — Galerie und Video Studio zeigen einen schwarzen Platzhalter statt eines Vorschaubildes
- Video-Metadaten (Dauer, Auflösung) werden nicht angezeigt

| Werkzeug | Zweck | macOS | Linux (Debian/Ubuntu) | Windows |
|----------|-------|-------|-----------------------|---------|
| **ffmpeg** | Vorschaubild-Extraktion + Video-Metadaten | `brew install ffmpeg` | `sudo apt install ffmpeg` | Download von [ffmpeg.org/download](https://ffmpeg.org/download.html) oder `winget install ffmpeg` |

> [!NOTE]
> `ffprobe` ist in ffmpeg enthalten — keine separate Installation nötig. ArtSmoker prüft zur Laufzeit auf ffmpeg und fällt elegant zurück, falls es nicht gefunden wird — die Videogenerierung funktioniert in beiden Fällen, Sie erhalten lediglich keine Vorschaubilder.

Installation überprüfen:

```bash
ffmpeg -version 2>&1 | head -1 && echo "ffmpeg: OK" || echo "ffmpeg: not installed (optional)"
ffprobe -version 2>&1 | head -1 && echo "ffprobe: OK" || echo "ffprobe: not installed (optional)"
```

## 📌 3. Installation

### 📝 3.1 macOS

```bash
git clone <repo-url> && cd ArtSmoker

# Option A: Mit virtueller Umgebung (empfohlen)
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Option B: Ohne virtuelle Umgebung (systemweite Installation)
pip3 install -r backend/requirements.txt
```

> [!NOTE]
> Auf macOS sind `python3` und `pip3` über Homebrew (`brew install python`) oder die Xcode-Kommandozeilenwerkzeuge verfügbar. Wenn „command not found" erscheint, installieren Sie Python von [python.org](https://www.python.org/downloads/) oder über `brew install python@3.12`.

### 📝 3.2 Linux (Debian/Ubuntu)

```bash
# Python bei Bedarf installieren
sudo apt update && sudo apt install python3 python3-pip python3-venv

git clone <repo-url> && cd ArtSmoker

# Option A: Mit virtueller Umgebung (empfohlen)
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Option B: Ohne virtuelle Umgebung
pip3 install --user -r backend/requirements.txt
```

> [!NOTE]
> Auf manchen Linux-Distributionen erfordert `pip install` außerhalb eines venv das Flag `--user` oder `--break-system-packages` (PEP 668). Die Verwendung eines venv vermeidet dies vollständig.

### 📝 3.3 Windows

```powershell
git clone <repo-url>
cd ArtSmoker

# Option A: Mit virtueller Umgebung (empfohlen)
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt

# Option B: Ohne virtuelle Umgebung
pip install -r backend\requirements.txt
```

> [!NOTE]
> Verwenden Sie unter Windows `python` (nicht `python3`). Installieren Sie Python von [python.org](https://www.python.org/downloads/) — aktivieren Sie „Add to PATH" während der Installation. Die Schriftauswahl von Type Studio erkennt Schriften aus `C:\Windows\Fonts` (die Systemschrifterkennung ist derzeit nur für macOS/Linux verfügbar — Windows-Nutzer können globale oder stilspezifische benutzerdefinierte Schriften verwenden).

## 📌 4. Ausführen

### 📝 4.1 Einzelentwicklung (alle Plattformen)

Einzelprozess mit automatischem Neuladen bei Dateiänderungen — ideal für einen einzelnen lokal arbeitenden Entwickler:

```bash
# Mit venv (zuerst aktivieren)
source .venv/bin/activate          # macOS / Linux
.venv\Scripts\activate             # Windows

uvicorn backend.main:app --reload
```

```bash
# Ohne venv (bei systemweiter Installation)
uvicorn backend.main:app --reload

# Oder falls uvicorn nicht im PATH ist
python3 -m uvicorn backend.main:app --reload     # macOS / Linux
python -m uvicorn backend.main:app --reload       # Windows
```

Öffnen Sie **http://localhost:8000** — das Frontend wird von FastAPI ausgeliefert, es ist kein separater Webserver nötig.

Beim Start zeigt die Konsole die Ergebnisse der AWS-Anmeldeinformationsvalidierung an. Wenn etwas nicht stimmt, sehen Sie eine deutliche Fehlerbox. Sie können den Status auch unter `http://localhost:8000/api/health` prüfen.

### 📝 4.2 Mehrbenutzer / gemeinsame Testmaschine / Produktion (macOS / Linux)

Für jede Umgebung mit mehr als einem gleichzeitigen Nutzer — ob eine gemeinsame Dev-/Test-Maschine, Staging oder Produktion — verwenden Sie **gunicorn** mit mehreren Workern:

```bash
# gunicorn installieren (einmalig, zusätzlich zu requirements.txt)
pip install gunicorn

# Mit gunicorn ausführen (Multi-Worker, verarbeitet gleichzeitige Nutzer)
gunicorn backend.main:app \
  -w 2 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 300
```

| Flag | Zweck |
|------|-------|
| `-w 2` | 2 Worker-Prozesse (bei höherer Last erhöhen) |
| `-k uvicorn.workers.UvicornWorker` | Die asynchrone Worker-Klasse von uvicorn verwenden |
| `--bind 0.0.0.0:8000` | Auf allen Schnittstellen lauschen (nicht nur localhost) |
| `--timeout 300` | 5-Minuten-Timeout für große Batch-Generierungen mit Wiederholungen |

> [!TIP]
> **gunicorn** ist nur für Linux/macOS. Verwenden Sie unter Windows `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2` für Multi-Worker-Betrieb.

<a id="43-ec2--cloud-deployment"></a>

### 📝 4.3 EC2 / Cloud-Deployment

Empfohlen: **t3.small** (~$15/Monat) für 1-2 gleichzeitige Nutzer.

**Schritt 1: Eine IAM-Rolle für die EC2-Instanz erstellen** (von Ihrer lokalen Maschine aus ausführen):

```bash
# Die IAM-Rolle mit EC2-Vertrauensrichtlinie erstellen
aws iam create-role --role-name ArtSmokerEC2Role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Die ArtSmoker-Richtlinie anhängen (verwenden Sie die eingeschränkte Richtlinie aus Abschnitt 2.2 oder die verwaltete Richtlinie)
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# Ein Instance-Profil erstellen und die Rolle anhängen
aws iam create-instance-profile --instance-profile-name ArtSmokerEC2Profile
aws iam add-role-to-instance-profile \
  --instance-profile-name ArtSmokerEC2Profile \
  --role-name ArtSmokerEC2Role
```

**Schritt 2: Eine EC2-Instanz starten** (oder das Profil an eine bestehende anhängen):

```bash
# An eine bestehende laufende Instanz anhängen
aws ec2 associate-iam-instance-profile \
  --instance-id i-YOUR_INSTANCE_ID \
  --iam-instance-profile Name=ArtSmokerEC2Profile
```

**Schritt 3: Auf der Instanz installieren und ausführen** (per SSH auf die Instanz):

```bash
# Installieren (einmalig)
sudo yum install -y python3 python3-pip git   # Amazon Linux
# sudo apt install -y python3 python3-pip python3-venv git   # Ubuntu

git clone <repo-url> && cd ArtSmoker
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install gunicorn

# Optional: ffmpeg für Video-Vorschaubilder installieren
sudo yum install -y ffmpeg   # Amazon Linux
# sudo apt install -y ffmpeg   # Ubuntu
```

**Schritt 4: Als systemd-Dienst ausführen** (persistent, mit automatischem Neustart):

```bash
# Die Dienstdatei erstellen
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

# Aktivieren und starten
sudo systemctl daemon-reload
sudo systemctl enable artsmoker
sudo systemctl start artsmoker

# Überprüfen, ob es läuft
sudo systemctl status artsmoker

# Logs ansehen
sudo journalctl -u artsmoker -f
```

Öffnen Sie **http://YOUR_INSTANCE_IP:8000** — stellen Sie sicher, dass Ihre EC2-Sicherheitsgruppe eingehenden TCP-Verkehr auf 8000 zulässt.

### 📝 4.4 Erste Schritte nach der Einrichtung

Nachdem ArtSmoker läuft, führen Sie diese Schritte aus, um die besten Ergebnisse zu erzielen:

**1. Modelle von AWS synchronisieren** — Öffnen Sie **Model Settings** (Zahnrad-Symbol in einem beliebigen Studio) → klicken Sie auf **Sync from AWS**. Dies erkennt alle verfügbaren Bild-, Video- und Chat-Modelle über alle Bedrock-Regionen hinweg. Dauert 30-60 Sekunden. Nur einmal erforderlich oder wenn AWS neue Modelle hinzufügt.

**2. Prompt-Vorlagen überprüfen und anpassen** — Dies ist die wirkungsvollste Konfiguration, die Sie vornehmen können. Öffnen Sie die Registerkarte **Model Settings → Prompt Templates**. ArtSmoker verwendet 28 bearbeitbare Direktiv-Prompts, die das Verhalten der KI steuern:

| Vorlage | Was sie steuert |
|---------|-----------------|
| Image Prompt Refinement | Wie Ihre Textbeschreibungen in detaillierte Bildgenerierungs-Prompts umgewandelt werden |
| Multi-Concept Generation | Wie mehrere kreative Optionen aus einer einzigen Idee generiert werden |
| Style Analysis | Wie Referenzbilder analysiert werden, um Ihren Kunststil zu erlernen |
| Content Moderation | Wie streng das Vorprüfungs- und Umschreibungssystem ist |
| Video Enhancement | Wie Video-Prompts mit Kamerabewegungen und Beleuchtung angereichert werden |
| Text Layout | Wie Type Studio die Textpositionierung auf Bildern gestaltet |

Jede Vorlage kann:
- **Direkt bearbeitet werden** — passen Sie die Anweisungen an die Bedürfnisse Ihres Teams an
- **Mit KI verbessert werden** — wählen Sie ein beliebiges LLM-Modell, fügen Sie optional Anweisungen hinzu (z. B. „für Pixel Art optimieren") und klicken Sie auf „Enhance with AI". Überprüfen Sie den Vorschlag und akzeptieren (Accept) oder verwerfen (Dismiss) Sie ihn
- **Auf Standard zurückgesetzt werden** — stellen Sie jederzeit das Original wieder her

Die Vorlagen sind nach Studio organisiert (Image Studio, Style Library, Content Safety, Video Studio, Type Studio, Chat Studio, Translation) mit benutzerfreundlichen Beschreibungen, was jede steuert.

**Variablensicherheit:** Vorlagen verwenden `{curly_brace}`-Variablen (z. B. `{user_prompt}`, `{model_name}`), die zur Laufzeit ersetzt werden. Wenn Sie versehentlich eine erforderliche Variable entfernen, wird ArtSmoker:
1. Das Speichern blockieren und anzeigen, welche Variablen fehlen
2. **„Fix & Save"** anbieten — ein LLM fügt die fehlenden Variablen automatisch an den richtigen Stellen wieder in Ihren bearbeiteten Text ein
3. Die Korrektur vor dem Speichern überprüfen

Vorlagen werden aus `backend/prompt_templates.json` geladen — der Laufzeit-Quelle der Wahrheit. Ihre Bearbeitungen werden in `backend/prompt_templates.user.json` (gitignored) gespeichert und darüber gelegt, sodass ein Update oder `git pull` Ihre Anpassungen niemals überschreibt. Falls die JSON fehlt oder beschädigt ist oder eine neue Vorlage im Code ausgeliefert wird, heilt sie sich selbst: Der integrierte Code-Seed regeneriert/ergänzt nur die fehlenden Einträge und überschreibt niemals bestehende.

> [!TIP]
> Beginnen Sie mit der Überprüfung der Vorlagen **Image Prompt Refinement** und **Creative Options**. Diese haben den größten Einfluss auf die Ausgabequalität. Wenn sich Ihr Team auf einen bestimmten Kunststil spezialisiert hat (z. B. Pixel Art, Aquarell, isometrisch), fügen Sie diese Präferenzen direkt in die Vorlagen ein, damit jede Generierung davon profitiert.

**3. Ein Stilprofil einrichten** (optional) — Gehen Sie zur **Style Library**, erstellen Sie einen neuen Stil, laden Sie Referenzbilder hoch und klicken Sie auf **Analyze**. Dies bringt ArtSmoker Ihre visuelle Identität bei.

**4. Ihre Sprache wählen** — Klicken Sie auf eine Sprachschaltfläche in der Navigationsleiste (EN | JA | ZH | KO | FR | ES), wenn Sie eine nicht-englische Oberfläche bevorzugen.

## 📌 5. Architektur

```
┌─────────────────────────────────────────────┐
│  Browser (SPA)                              │
│  Vanilla JS + Tailwind CSS                  │
└──────────────────────┬──────────────────────┘
                       │ HTTP / SSE
                       ▼
┌─────────────────────────────────────────────┐
│  FastAPI-Backend (Python)                   │
│                                             │
│  /api/styles      Stil-CRUD + Import        │
│  /api/generate    Zweistufige Generierung   │
│  /api/type-studio Text-Overlay + Schriften  │
│  /api/video       Videogenerierung + Jobs   │
│  /api/chat        LLM-Chat + Sitzungen      │
│  /api/gallery     Asset-Durchsicht + Export │
│  /api/browse      Datei-/S3-Browser         │
│  /api/admin       Modellregistry + Vorlagen │
│  /api/refine-prompt  Prompt + Übersetzung    │
│  /api/transcribe  Sprache-zu-Text           │
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
└──────────────────────┘  └──────────────────────────┘ ... (andere Regionen)
             │
             ▼
┌──────────────────────┐
│  Lokaler Speicher     │
│  data/styles/         │
│  data/generated/      │
│  data/video/          │
│  data/chat/           │
└──────────────────────┘
```

## 📌 6. Nutzung

### 📝 6.1 Workflow-Überblick

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
  │ Upload   │ │Bilder  │ │Videos  │ │ Text zu  │ │ Multi- │
  │ Analyze  │ │gener.  │ │gener.  │ │ Bildern  │ │ Modell │
  │ Schriften│ │        │ │        │ │          │ │ LLM    │
  │          │ │        │ │        │ │          │ │ chat   │
  └────┬─────┘ └───┬────┘ └───┬────┘ └────┬─────┘ └────────┘
             │              │            │               │
             │    ┌─────────┴────────────┴─────────┐     │
             │    │  Stil gewählt? (optional)      │     │
             └───►│  Verbessert die Ausgabe        │◄────┘
                  └─────────┬──────────────────────┘
                                    │
                                    ▼
                          ┌─────────────────┐
                          │    Galerie      │
                          │                 │
                          │ Alle durchsuchen│
                          │ Suchen/Filtern  │
                          │ Wählen & löschen│
                          └────────┬────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
            ┌──────────────┐ ┌──────────┐ ┌──────────────┐
            │ Download     │ │ Neu laden│ │ Text hinzuf. │
            │ PNG / SVG    │ │ in 2D    │ │ in Type      │
            │              │ │ Image    │ │ Studio       │
            │              │ │ Studio   │ │              │
            │              │ │ (verfein.│ │ (Text        │
            │              │ │  & neu)  │ │  überlagern) │
            └──────────────┘ └──────────┘ └──────────────┘
```

**Drei Einstiegspunkte, eine einheitliche Galerie:**

- **Mit einem Stil beginnen** — laden Sie Referenzgrafik in die Style Library hoch, lassen Sie die KI sie analysieren und generieren Sie dann in einem beliebigen Studio. Der Stil leitet alle Ausgaben.
- **Ohne Stil beginnen** — springen Sie direkt in das 2D Image Studio, Video Studio oder Type Studio. Die KI nutzt ihr bestes Urteilsvermögen.
- **Von der Galerie aus beginnen** — wählen Sie ein zuvor generiertes Asset und laden Sie es zur Verfeinerung im passenden Studio neu, fügen Sie Text hinzu, spielen Sie ein Video ab oder laden Sie es als PNG/SVG/MP4 herunter.

Alle generierten Assets (Bilder, Videos, Text-Overlays, eigenständiger Text) landen in der einheitlichen Galerie. Nichts wird überschrieben — jede Generierung erzeugt neue Assets.

### 📝 6.2 Generierungs-Pipeline

```
Nutzer-Prompt: "hospital building"
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 1. Prompt-Komposition           Claude Sonnet (1 Opt.) │
│    (optionale "Compose"-Taste)  oder Opus (2-5 Opt.)   │
│    + Stil + Asset-Typ                                  │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 2. Canary-Test                                         │
│    Einzelbild testet Moderation                        │
│    Bestanden? ──► Voller Batch  Fehlschlag? ──► Wechsel│
│                                  oder Umschreib-Vorschlag│
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 3. Parallele Bildgenerierung                           │
│    Bis zu 5 Optionen × 5 Variationen = 25 Bilder       │
│    ThreadPool (3-5 Worker)                             │
│    Wiederholung mit exponentiellem Backoff (3 Versuche)│
│    SSE-Fortschritts-Streaming zum Browser              │
│    Kooperativer Abbruch bei Moderationsblockade        │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 4. Nachbearbeitung (pro Bild, optional)                │
│    Hintergrund entfernen ──► Stability AI ($0.07/Bild) │
│    Hochskalieren ──► Stability AI Creative Upscale ($0.60)│
│    SVG ──► vtracer / potrace / Pillow (kostenlos, lokal)│
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 5. Speicherung                                         │
│    data/generated/{asset_id}/                          │
│    ├── asset.png (transparenter Hintergrund)           │
│    ├── asset.svg (optional)                            │
│    └── metadata.json (vollständige Prompt-Historie)    │
│    Intelligente Dateinamen: prompt-slug_opt1_var2.png  │
└────────────────────────────────────────────────────────┘
```

### 📝 6.3 Ablauf der Inhaltsmoderation

```
Nutzer klickt Generate
         │
         ▼
┌──────────────────────┐
│ Vorprüfung aktiv?    │
│ (Prompt Pre-Check    │
│  Umschalter, standard│
│  mäßig an)           │
└───┬────────────┬─────┘
  Ja             Nein
    │            │
    ▼            │
┌──────────┐     │
│ Claude   │     │
│ Sonnet   │     │
│ prüft    │     │
│ Prompt   │     │
└───┬────┬─┘     │
Probl.? Nein     │
    │    └──────►│
    ▼            │
┌──────────────┐  │
│ Indigo-      │  │
│ Dialog:      │  │
│ • Wechseln   │  │
│ • Umschreib. │  │
│ • Fortfahren │  │
│ • Abbrechen  │  │
└──┬───────────┘  │
   │◄────────────┘
   ▼
┌──────────────────────┐
│ Canary-Test          │
│ (1 Bild an Modell)   │
└───┬────────────┬─────┘
Blockiert       Bestanden
    │            │
    ▼            ▼
┌──────────┐  ┌──────────┐
│ Alt.     │  │ Voller   │
│ Modelle  │  │ Batch    │
└───┬────┬─┘  │ läuft    │
Klappt? Nein  └──────────┘
    │    │
    ▼    ▼
Smaragd    Bernstein
Dialog     Dialog
(Wechsel   (Umschreib. →
 oder       verbesserter
 Umschreib.)Prompt-Bereich)
```

### 📝 6.4 2D Image Studio (Assets generieren)

Das 2D Image Studio verwendet einen geführten 3-Schritt-Workflow:

**Schritt 1 — Beschreiben Sie Ihre Idee**: Geben Sie einen Prompt in das Textfeld ein. Der Platzhalter zeigt ein realistisches Beispiel, das sich je nach ausgewähltem Asset-Typ ändert (z. B. „A young female warrior in ornate silver armor..." für Character oder „A misty Japanese garden at dawn..." für Environment). Nutzen Sie die Spracheingabe (Mikrofon-Taste), um statt zu tippen zu diktieren.

**Schritt 2 — Prompt Designer** *(optional)*: Klicken Sie auf **🎨 Prompt Designer**, um Ihren Prompt in strukturierte visuelle Komponenten zu zerlegen. Die KI analysiert Ihren Prompt und teilt ihn in bearbeitbare Abschnitte auf:

- **Motiv (Subject)** — Charakterbeschreibung, Kleidung, Accessoires, Pose, Ausdruck
- **Szene (Scene)** — Setting, Hintergrund, Requisiten, Tageszeit
- **Komposition (Composition)** — Kamerawinkel, Rahmung, Tiefenschärfe
- **Beleuchtung (Lighting)** — Hauptlicht, Fülllicht/Rim Light, Stimmung
- **Stil & Farben (Style & Colors)** — Kunststil, Qualitätsstufe und eine benannte Farbpalette mit Hex-Farbmustern

Jedes Feld kann einzeln bearbeitet werden. **Generate Enhanced Prompt** setzt Ihre Bearbeitungen zu einem flachen, neu zusammengesetzten Prompt zusammen (in Schritt 2 schreibgeschützt angezeigt) und generiert dann automatisch den Enhanced AI Prompt für Schritt 3.

Bevor der Prompt Designer öffnet, läuft eine **KI-Asset-Typ-Klassifizierung** — wenn Ihr Prompt eine Szene beschreibt, Sie aber „Game Asset" gewählt haben, schlägt ein Dialog vor, zu „Environment" oder „Character" zu wechseln. So stellt der Prompt Designer sicher, dass die Dekomposition mit dem richtigen Kontext erfolgt.

**Schritt 3 — Vorschau des verbesserten Prompts** *(optional)*: Klicken Sie auf **Generate Enhanced Prompt**, um den modelloptimierten Prompt vor der Generierung zu sehen. Die KI nimmt den neu zusammengesetzten Prompt aus Schritt 2 und reichert ihn mit modellspezifischer Anleitung an (Anatomie, Materialien, Beleuchtung, Prompt-Struktur). Sie können den verbesserten Prompt vor der Generierung bearbeiten. Wenn Sie in Schritt 2 den Prompt Designer verwendet haben, wird dieser automatisch befüllt.

**Prompt-Pipeline**: Nutzer-Prompt → Dekomposition → Rekomposition (`recomposed_prompt`) → Verbesserung mit Modellanleitung (`enhanced_prompt`) → Bildmodell. Bei mehreren Optionen erzeugt der Verbesserungsschritt N unterschiedliche Interpretationen aus derselben neu zusammengesetzten Basis. Alle drei Ebenen werden in den Metadaten gespeichert.

**Generate**: Klicken Sie jederzeit auf Generate — die Schritte 2 und 3 sind optional. Wenn Sie sie überspringen, wird Generate Ihren Prompt automatisch dekomponieren, neu zusammensetzen und verbessern, bevor fortgefahren wird. **Prompt Pre-Check** (standardmäßig an) prüft den Prompt vor der Generierung auf Moderationsprobleme.

**Zusätzliche Steuerelemente:**
- **Asset-Typ** — in der Seitenleiste auswählen. Ändert den Prompt-Platzhalter und beeinflusst, wie die KI Ihren Prompt interpretiert. Das System schlägt einen Wechsel vor, wenn es eine Diskrepanz erkennt.
- **Kunststil (Art Style)** — wählen Sie ein Stilprofil, um die Generierung mit Ihrer visuellen Identität zu leiten.
- **Abmessungen, Optionen, Variationen** — konfigurieren Sie die Ausgabegröße und wie viele kreative Konzepte generiert werden sollen.
- **Nachbearbeitung** — Hintergrund entfernen, Hochskalieren, SVG-Konvertierung (nach der Generierung angewendet).
- **IP-Erklärung** — behaupten Sie Eigentum oder Lizenzierung für die Kompatibilität mit strengen Modellen.
- **Model Settings** — Modellkonfiguration ansehen/bearbeiten, verfügbare Amazon-Bedrock-Modelle entdecken.

Der Generierungsfortschritt wird in Echtzeit über SSE gestreamt — die UI zeigt, welches Bild gerade generiert wird (z. B. „Generating images... 12/25"), die verstrichene Zeit und die aktuelle Pipeline-Phase. Wenn die API gedrosselt wird, sehen Sie „API throttled — waiting to retry..." mit der Verzögerung, dann „Retrying... (attempt 2/3)" — jedes Bild wird bis zu 3 Mal mit exponentiellem Backoff wiederholt, damit große Batches keine Varianten durch vorübergehende Drosselung verlieren.

Generierte Ergebnisse überstehen die Navigation — das Wechseln von Registerkarten und zurück bewahrt den DOM-Zustand des 2D Image Studios. Nur die Reset-Schaltfläche löscht ihn.

**Intelligente Inhaltsmoderation**: Wenn Ihr Prompt von den Inhaltsmoderationsfiltern eines Modells blockiert wird, behandelt ArtSmoker dies schrittweise über drei farbcodierte Dialoge:

- **Indigo (Vorprüfung)** — vor der Generierung prüft eine KI Ihren Prompt gegen die bekannte Sensibilität des ausgewählten Modells vor. Wenn Probleme erkannt werden, sehen Sie die konkreten Bedenken und können: zu einem empfohlenen Modell wechseln, **den Prompt umschreiben** für das aktuelle Modell, trotzdem fortfahren oder abbrechen.
- **Smaragd (Modellwechsel)** — nach einer Generierungsblockade zeigt ArtSmoker, welches Modell funktioniert und warum, falls ein alternatives Modell Ihren Prompt unverändert akzeptiert. Ein Klick zum Wechseln. Vollständiges Versuchsprotokoll verfügbar („View N model tests").
- **Bernstein (Umschreiben)** — wenn alle Modelle ablehnen, wird ein KI-generiertes Umschreiben in einem bearbeitbaren Textfeld mit aufgelisteten konkreten Problemen angeboten. Ein Verifiziert/Nicht-verifiziert-Badge zeigt an, ob das Umschreiben den Canary-Test bestanden hat.

**Verhalten beim Umschreiben von Prompts**: In allen drei Dialogen überschreibt die Wahl von „Rewrite" niemals Ihren ursprünglichen Prompt. Die umgeschriebene Version erscheint im **Bereich des verbesserten Prompts** unter Ihrem Originaltext, mit einem dauerhaften Bernstein-Hinweis: *„This rewrite is an attempt to make the prompt compatible — it is still subject to the model's own moderation assessment and may be rejected."* Sie überprüfen und bearbeiten den verbesserten Prompt und klicken dann auf Generate, wenn Sie zufrieden sind. Ihr ursprünglicher Prompt bleibt stets im Verlauf und in den Metadaten erhalten.

Häufige Auslöser sind urheberrechtlich geschützte IP-Namen und Charakterreferenzen, Gewalt-/Waffensprache und Verweise auf Erwachseneninhalte. Tipp: Die Schaltfläche **„Preview Enhanced Prompt"** erzeugt oft Prompts, die die Moderation von Natur aus bestehen, da die KI in beschreibenden Begriffen umformuliert.

**Intelligentes Canary-Testing**: Vor der Generierung des gesamten Batches sendet ArtSmoker eine einzelne „Canary"-Bildanfrage, um den Prompt gegen die Moderationsfilter des Modells zu testen. Wenn der Canary blockiert wird, stoppt der Batch sofort (1 verschwendeter API-Aufruf statt N×M×3). Wenn der Canary besteht, laufen die verbleibenden Aufgaben parallel mit kooperativem Abbruch — wenn eine Aufgabe auf eine Moderationsblockade stößt, überspringen die übrigen automatisch ihre API-Aufrufe.

### 📝 6.5 Ein Stilprofil verwenden

1. Gehen Sie zur Registerkarte **Style Library**.
2. Klicken Sie auf **Create New Style** — geben Sie einen Namen ein und fügen Sie optional Generierungshinweise hinzu. Nutzen Sie im Erstellungs-Modal den Bereich **„Import References From"** mit den Schaltflächen **Local** und **S3**, um ein Quellverzeichnis oder einen Bucket-Pfad auszuwählen. Das Durchsuchen öffnet einen serverseitigen Datei-/Verzeichnisbrowser-Modal (ein Klick wählt ein Element aus, Doppelklick navigiert in Verzeichnisse). Importierte Referenzen werden bei der Erstellung automatisch analysiert.
3. Lokale Verzeichnisimporte durchsuchen **rekursiv** alle Unterverzeichnisse nach Bildern (.png, .jpg, .jpeg, .gif, .bmp, .webp, .tiff, .tif, .tga, .ico, .svg) und 3D-Modellen (.glb, .gltf). Bilddateien werden mit **relativen Symlinks** verknüpft (keine Duplizierung, portabel zwischen Maschinen). Bei 3D-Modelldateien (.glb/.gltf) werden die eingebetteten Texturen **automatisch extrahiert** — Base64-Daten-URIs, binäre Puffer-Chunks und externe Texturreferenzen werden alle verarbeitet. Extrahierte Texturen werden als Kopien gespeichert (mit dem Modellnamen präfigiert, um Kollisionen zu vermeiden). S3-Importe listen rekursiv mit Paginierung und **laden** Dateien lokal herunter. Es werden bis zu **100 Referenzbilder** pro Stil importiert. Unterstützte Erweiterungen sind in `backend/config.py` zentralisiert (`IMAGE_EXTENSIONS` und `MODEL_EXTENSIONS_WITH_TEXTURES`).
4. **Zweiphasige kohäsionsbewusste Analyse**: Phase 1 sendet 8 Bilder an Claude Sonnet, um den Kohäsionsgrad zu bestimmen (hoch/mittel/niedrig) — hoch bedeutet einheitlicher Stil, mittel bedeutet gemeinsame Struktur mit unterschiedlichen Themen, niedrig bedeutet vielfältige Stile. Phase 2 gibt die Kohäsionsbewertung neben den Referenzbildern an Claude Opus weiter und leitet es an, angemessen für den Sammlungstyp zu analysieren. Wenn ein Stil mehr als 20 Referenzen hat, wählt der Analyzer eine vielfältige repräsentative Teilmenge von 20 für den Opus-Vision-Aufruf — was die Abdeckung über Dateinamengruppen und Dateigrößenvielfalt hinweg sicherstellt. Der KI wird mitgeteilt, wie viele Bilder insgesamt existieren gegenüber wie viele sie sieht. Der Analyse-Prompt ist speziell für Spiele-Assets auf transparenten Hintergründen konzipiert — fragt nach materialspezifischen Rendering-Details, dem Proportionssystem und Schatten-/Beleuchtungsspezifika. Extrahiert 9 Stilattribute, darunter `materials` (wie Stein, Holz, Metall gerendert werden) und `detail_level` (welche Oberflächendetails sichtbar sind gegenüber vereinfacht). Generierungshinweise werden auf 200 Wörter erweitert, die 8 Dimensionen abdecken: Perspektive, Rendering, Materialien, Farbpalette, Proportionen, Kantenbehandlung, Schatten/Beleuchtung, Detailgrad und Hintergrund — spezifisch genug, dass generierte Assets sich visuell mit vorhandenen Referenzen verbinden.
5. Nutzen Sie in der Stil-Detailansicht **„Import & Analyze"**, um weitere Referenzen hinzuzufügen und die Analyse in einem Schritt auszulösen. Das Hochladen per Drag-and-Drop wird ebenfalls unterstützt und **analysiert automatisch neu**, wenn neue Bilder hinzugefügt werden.
6. **„Re-Analyze Style"** erscheint nach der ersten Analyse und lässt Sie die Analyse jederzeit manuell erneut ausführen.
7. **Generierungshinweise** sind Teil des Analysekontexts — die KI erhält beim Analysieren sowohl Referenzbilder als auch Ihre Hinweise als „Artist's Guidance", sodass das Stilprofil die Absicht versteht, nicht nur das visuelle Erscheinungsbild. Das Bearbeiten von Generierungshinweisen löst ebenfalls eine **automatische Neuanalyse** aus.
8. Zurück im **2D Image Studio** wählen Sie Ihren Stil aus dem Dropdown — alle generierten Assets werden zu seiner visuellen Identität passen (Palette, Perspektive, Rendering-Stil, Stimmung).

### 📝 6.6 Ablauf der Stilanalyse

```
┌──────────────────────────────────────────┐
│ Stil erstellen / importieren             │
│ (Referenzbilder hochgeladen/importiert)  │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│ Phase 1: Kohäsionsprüfung                │
│ Claude Sonnet — 8 Bilder — ~$0.01        │
│ Bestimmt: hoch / mittel / niedrig        │
│   hoch   = einheitlicher Stil            │
│   mittel = geteilte Struktur, div. Themen│
│   niedrig = vielfältige Sammlung         │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│ Phase 2: Vollständige Analyse            │
│ Claude Opus — bis zu 20 Bilder           │
│ Geleitet vom Kohäsionsgrad               │
│ + Artist's Guidance (Nutzerhinweise)     │
│ Extrahiert 9 Stilattribute               │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│ Phase 3: Hinweisgenerierung              │
│ Claude Sonnet — 200-Wort-Hinweise        │
│ 8 Dimensionen: Perspektive, Rendering,   │
│ Materialien, Palette, Proportionen, Kanten│
│ Schatten/Beleuchtung, Detailgrad         │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│ In profile.json gespeichert              │
│ ~$0.14 gesamt pro Stilanalyse            │
│ Bei allen künftigen Generierungen genutzt│
└──────────────────────────────────────────┘
```

### 📝 6.7 Type Studio

Fügen Sie Text zu Bildern hinzu oder generieren Sie eigenständige Text-Assets mit KI-gestalteter Typografie.

- **Zwei Modi**: „On Image" komponiert Text auf ein Galeriebild; „Standalone" rendert Text auf einem transparenten Hintergrund.
- **Mehrzeiliger Texteditor** mit Schriftauswahl pro Zeile, Positionierungssteuerung und **Spracheingabe** (Mikrofon-Taste pro Zeile — Text per Nova-Sonic-Transkription diktieren).
- **KI-gestaltete Layouts** — die KI schlägt Farben, Größen, Positionen und Effekte (Schatten, Kontur, Glühen) vor. Fordern Sie 1–5 Layout-Optionen für unterschiedliche kreative Richtungen an. Das für das Layout verwendete **LLM-Modell** ist konfigurierbar (Complex LLM für beste Qualität, Fast LLM für günstiger) — liest aus den Registry-Kategorien.
- **Schriftauswahl mit Live-Vorschau** — Stil-Schriften, 8 mitgelieferte Schriften (Roboto, Open Sans, Lato, Montserrat, Playfair Display, Oswald, Raleway, Source Code Pro), Systemschriften und **clientseitig erkannte Schriften** (über die Local Font Access API oder Canvas-Probing).
- **Vor-/Nachbearbeitung** — derselbe Workflow wie im 2D Image Studio, mit einer „Apply"-Schaltfläche für die Nachbearbeitung. Die SVG-Konvertierung ist standardmäßig an.
- **Klicken zum Zoomen** — ein Klick auf die Ergebnisvorschau öffnet den AssetViewer mit vollem Zoom/Schwenk, Metadaten, Download und Bildbearbeitungswerkzeugen.
- Ergebnisse werden als neue Galerie-Assets gespeichert (Originale werden nie überschrieben).

### 📝 6.8 Galerie

- **Einheitliche Ansicht** aller generierten Bilder und Videos in einem **Masonry-Layout** (jedes Asset in seinem echten Seitenverhältnis dargestellt — Hochformat, Quadrat oder Querformat — niemals mittig beschnitten), mit einem **Medienfilter** (Alle / 2D-Grafik / 3D-Modelle / Video). Der Filter **3D-Modelle** zeigt nur Assets, die bereits ein generiertes 3D-Modell besitzen, und diese Assets tragen ein **3D-Badge** auf ihrer Kachel.
- **Suchleiste** für sofortiges Filtern über alle Assets (Prompts, Stile, Modelle).
- **Mehrfachauswahl** mit Checkboxen für Massenlöschung (verarbeitet sowohl Bild- als auch Video-Assets). Löschvorgänge sind **batch-bewusst** — überlebende Geschwister verfolgen, wie viele Varianten entfernt wurden, sodass das Neuladen eines Teil-Batches im Image Studio „X von Y Bildern verbleibend (Z gelöscht)" anzeigt.
- Assets werden sofort mit einem In-Memory-Metadaten-Cache geladen. Sortiert nach neuesten zuerst.
- Paginierungsunterstützung (limit/offset) für große Sammlungen.
- Die Galerie aktualisiert sich automatisch, wenn Sie zu ihr zurücknavigieren, und nach Abschluss jeder Bearbeitung oder Videogenerierung.
- **Video-Karten** zeigen ein Vorschaubild mit einem Abspiel-Overlay, einem VIDEO-Badge und einer Daueranzeige. Klicken Sie, um den Videoplayer-Modal zu öffnen.
- **Kontextbezogene Aktionsschaltflächen** pro Asset je nach Typ: **„2D Studio"** (Indigo) zum Neuladen im Image Studio, **„Add Text"** (Smaragd) zum Öffnen in Type Studio, **„Edit in Type Studio"** (Violett) für Text-Assets.
- Klicken Sie auf ein beliebiges Bild, um den **AssetViewer**-Modal zu öffnen mit:
  - **Zoom/Schwenk** — Mausrad zum Zoomen, Ziehen zum Schwenken, Fit/1:1-Schaltflächen mit aktiver Modushervorhebung.
  - **Registerkarte „Bearbeiten"** — das Bild direkt per Inpainting, Radieren, Outpainting, Suchen & Ersetzen oder Umfärben bearbeiten. Pro Modus werden zwei Arten von Editor angeboten: **maskenbasiert** (Stability) — malen Sie eine Maske mit dem Pinselwerkzeug, geben Sie einen Prompt ein und wenden Sie es an; und **maskenfreie Instruktions-Editoren** (Qwen-Image-Edit, sofern deployt) — beschreiben Sie die Änderung einfach in Worten, keine Maske nötig. Die Pinselsteuerung wird bei einem maskenfreien Modell automatisch ausgeblendet. Wählen Sie das Bearbeitungsmodell und wenden Sie es an; standardmäßig wird das Originalbild ersetzt, deaktivieren Sie „Replace original", um als neues Asset zu speichern (jede Bearbeitung bewahrt den Versionsverlauf).
  - **Zurück / Weiter** — Pfeilschaltflächen und Tastatur links/rechts, um durch die Liste zu navigieren, ohne den Viewer zu schließen.
  - **Vollständige Metadaten**: Original-Prompt, KI-verbesserter Prompt, Generierungs-Prompt, Negativ-Prompt, Stil, Asset-Typ, Bildmodell (benutzerfreundliche Namen), Abmessungen, Seed, Batch-ID, Options-/Variationsindex, Status der IP-Erklärung, Dateiname und Erstellungsdatum.
- **Stil-Snapshot**: Jedes Asset speichert einen Snapshot des zur Generierungszeit verwendeten Stils (Name, Beschreibung, Hinweise, Analyse). Wird der ursprüngliche Stil später gelöscht, behält das Asset den vollständigen Kontext. Abwärtskompatibel — ältere Assets ohne Snapshots werden normal angezeigt.

### 📝 6.9 Spracheingabe

Klicken Sie auf die Mikrofon-Schaltfläche neben dem Prompt-Editor, um Ihren Prompt zu diktieren. Das Audio wird zur Transkription an Nova Sonic gesendet.

> [!NOTE]
> Die Sprachtranskription erfordert die bidirektionale Streaming-API von Nova Sonic, die von einer kompatiblen boto3-Version und aktiviertem Modellzugriff in us-east-1 abhängt. Wenn die Streaming-API nicht verfügbar ist, gibt der Dienst eine Platzhalter-Bestätigung zurück. Die vollständige Echtzeit-Transkription funktioniert, wenn Nova-Sonic-Streaming korrekt konfiguriert ist.

### 📝 6.10 Bewahrung des Ansichtszustands

Navigationsreihenfolge: **Style Library → 2D Image Studio → Type Studio → Video Studio → Galerie**. Das Wechseln zwischen Ansichten bewahrt den DOM-Zustand jeder Ansicht. Generierte Ergebnisse, Formulareingaben und Scroll-Positionen überstehen die Navigation. Die Bernstein-Reset-Schaltfläche im 2D Image Studio und Video Studio ist die einzige Möglichkeit, deren Zustand zu löschen.

### 📝 6.11 Modellverwaltung

Die gesamte KI-Modellkonfiguration ist in `backend/model_registry.json` zentralisiert — der einzigen Quelle der Wahrheit. Modelle, Regionen, Preise, Qualitätsstufen und Formatvorlagen werden alle hier gespeichert und über die UI oder API verwaltet:

- Klicken Sie in der Seitenleiste eines beliebigen Studios auf **„Model Settings"**, um das Admin-Modal zu öffnen — es öffnet die für dieses Studio relevante Registerkarte.
- **7 Registerkarten** nach Studio organisiert:
  - **Image Studio** — Bildgenerierungsmodelle (SD 3.5 Large, Stable Image Ultra, Stable Image Core sowie selbst gehostete FLUX, HunyuanImage, Qwen-Image), Regionen, Qualitätsstufen, Prompt-Limits, Moderationsstrenge
  - **Video Studio** — Videomodelle (Nova Reel, Luma Ray), S3-Bucket-Einstellungen, Regionen, Preise
  - **Chat Studio** — Erkannte Chat-/LLM-Modelle (80+ von 16 Anbietern), Kontextfenster, Vision-Fähigkeit, Preise pro 1K Tokens
  - **Type Studio** — LLM-Modell für die Text-Layout-Generierung (Complex oder Fast LLM)
  - **Shared Studio** — Studio-übergreifende LLM-Kategorien (Fast LLM, Complex LLM, Fallback LLM, Voice), Nachbearbeitungsmodelle (Remove Background, Upscale)
  - **Prompt Templates** — 28 bearbeitbare LLM-Direktiv-Prompts nach Studio organisiert (siehe Abschnitt 4.4)
  - **Registry JSON** — Roher JSON-Editor für die vollständige Modellregistry
- Alle Abschnitte sind **einklappbar** mit **Show All / Hide All**-Umschaltern für schnelle Navigation.
- LLM-Kategorien und Nachbearbeitung verwenden **Dropdown-Modell-Auswähler** (befüllt aus erkannten Modellen) — keine rohen Textfelder.
- **Sync from AWS**: Scannt alle von Bedrock unterstützten AWS-Regionen (dynamisch erkannt), registriert automatisch neue Bild-, Video- und **Chat-Modelle**, aktualisiert die regionale Verfügbarkeit, ruft modellspezifische Preise von der AWS Pricing API ab und deaktiviert nicht mehr verfügbare Modelle. Ein **Live-Fortschritts-Overlay** streamt jede Region, während sie gescannt wird. Dies ist die **einzige** Aktion, die die AWS-Erkennungs-APIs aufruft — alle anderen Operationen lesen aus der zwischengespeicherten Registry.
- **Immer auf dem neuesten Claude**: Jeder Sync rollt automatisch Ihr **Fast LLM** auf den neuesten in Ihrem Konto verfügbaren Claude Sonnet und Ihr **Complex LLM** auf den neuesten Claude Opus, sodass Sie nie auf einem veralteten Modell festsitzen — keine manuelle Konfiguration nötig. Wenn Sie für eine Kategorie manuell ein bestimmtes Modell wählen, wird es **angeheftet** und das Auto-Rollen lässt es in Ruhe (es benachrichtigt Sie lediglich, wenn ein neueres erscheint).
- **Erkennung benutzerdefinierter Modelle**: Sync erkennt auch **fein abgestimmte benutzerdefinierte Modelle** (`ListCustomModels`), **importierte Modelle** (`ListImportedModels`) und Modelle mit **On-Demand-Deployments** (`ListCustomModelDeployments`) oder **bereitgestelltem Durchsatz** (`ListProvisionedModelThroughputs`). Benutzerdefinierte Modelle erben ihre Formatfamilie automatisch vom Basismodell.
- **Auto-Erkennung**: Neue Foundation-Modelle werden mit `enabled=true` registriert — der Admin kann sie deaktivieren. Bestehende Modelle erhalten automatisch aktualisierte `available_regions` und Bedrock-Metadaten (Modalitäten, Lebenszyklus, ARN).
- **Gestylte Bestätigungsdialoge**: Alle destruktiven Aktionen (Sync, Löschen, Reset) verwenden benutzerdefinierte gestylte Modals — keine Browser-`confirm()`-Popups.
- Änderungen werden sofort über die Admin-API in `model_registry.json` persistiert.
- Die Registry ist abwärtskompatibel — bestehende Assets referenzieren Modellschlüssel (z. B. `sd35_large`), nicht rohe Bedrock-Modell-IDs.

### 📝 6.12 Selbst gehostete Modelle (Custom Models auf Amazon SageMaker)

ArtSmoker kann Open-Source-KI-Modelle auf **Amazon SageMaker** in Ihrem eigenen AWS-Konto deployen und so Ihre Fähigkeiten über das hinaus erweitern, was Amazon Bedrock bietet. Diese laufen neben den Bedrock-Modellen und erscheinen in denselben Studio-Dropdowns.

**Erweiterbarer Modellkatalog:** Wird mit einem integrierten Katalog von Open-Source-Modellen ausgeliefert, der Bildgenerierung, Hochskalierung, Hintergrundentfernung, Tiefenschätzung, Segmentierung und Video umfasst. Das Hinzufügen eines neuen Modells erfordert nur einen Katalogeintrag — keine Codeänderungen. Sie können auch benutzerdefinierte Modelle über die UI hinzufügen (+ Add Model). Der Katalog und die verfügbaren Modelle entwickeln sich im Laufe der Zeit weiter.

**Deployment-Optionen:**
- **Async (scale-to-zero)** — zahlen Sie nur bei der Generierung. Skaliert im Leerlauf auf null ($0 Kosten), skaliert bei neuer Anfrage automatisch hoch. Kaltstart ~5-10 Min.
- **Always-On** — sofortige Antworten, ~$1.41/Std. (ml.g5.xlarge)

**So wird deployt:** Model Settings → Registerkarte Custom Models → auf Deploy klicken. Der SageMaker-Container lädt die Modellgewichte beim Start direkt von HuggingFace — kein mehrere-GB-großer lokaler Download erforderlich.

**CPU-Offloading:** Große Diffusionsmodelle nutzen intelligentes CPU-Offloading, um auf kleinere GPU-Instanzen zu passen. Der Katalogeintrag jedes Modells legt die Strategie fest — `model_cpu_offload` (behält aktive Layer auf der GPU) oder `sequential_cpu_offload` (aggressives Offloading pro Layer für sehr große Modelle). Wird automatisch vom Inferenz-Handler angewendet.

**Asynchrone Generierung mit Pending Jobs:** Selbst gehostete Modelle generieren asynchron. Ein **Pending Jobs**-Panel erscheint im 2D Image Studio und zeigt aktive Jobs mit Fortschrittsanzeigen. Fertige Bilder erscheinen automatisch in der Galerie — kein Polling oder Seitenneuladen nötig.

**Verwaltung von HuggingFace-Tokens:** Zugriffsbeschränkte Modelle erfordern ein schreibgeschütztes HuggingFace-Token. Das Token wird verschlüsselt im **AWS Secrets Manager** in Ihrem Konto gespeichert, über die UI verwaltet (setzen/aktualisieren/löschen) und über alle Modelle geteilt, die es benötigen. Tokens werden automatisch bereinigt, wenn Sie alle Modelle abbauen.

**Vorprüfung des zugriffsbeschränkten Zugriffs:** Vor einem zugriffsbeschränkten Deployment prüft der Dialog **jedes** HuggingFace-Repo, das das Modell herunterlädt (seine eigenen Gewichte plus etwaige Abhängigkeiten), mit Ihrem gespeicherten Token und zeigt pro Repo ein ✓/✗ mit dem genauen nächsten Schritt — akzeptieren Sie die Lizenz *dieses* Repos auf HuggingFace oder fügen Sie ein Token hinzu. Das Deployment bleibt blockiert, bis jedes erforderliche Repo erreichbar ist, sodass eine vergessene Lizenzzustimmung schnell im Dialog fehlschlägt statt erst Minuten nach Beginn eines Kaltstarts.

**Einrichtung:** Fügen Sie Amazon-SageMaker- und Secrets-Manager-Berechtigungen zu **derselben IAM-Rolle** hinzu, die Sie bereits für Bedrock verwenden — keine separate Rolle oder Umgebungsvariable nötig. ArtSmoker erkennt Ihre Rolle auf EC2/ECS automatisch oder erstellt bei Bedarf automatisch eine `ArtSmokerSageMakerRole`.

```bash
# Amazon-SageMaker-Berechtigungen zu Ihrer bestehenden ArtSmoker-Rolle hinzufügen (ein Befehl)
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
```

**Python-Abhängigkeit:** `huggingface_hub>=0.23` (installieren mit `pip install huggingface_hub`)

### 📝 6.13 Bild- & Videogenerierungsmodelle

Alle Modelle werden **dynamisch** aus der Registry **erkannt** — nicht fest codiert. Das Image-Studio-Dropdown wird beim Laden der Seite aus `GET /api/admin/models/image-options` befüllt und das Video-Studio-Dropdown aus `GET /api/admin/models/video-options`. Jedes Modell, das in der Registry registriert und aktiviert ist, erscheint automatisch.

Das Dropdown **Image Model** ist die primäre Auswahl. Darunter zeigt eine intelligente Zusammenfassungszeile die aktive Region, Qualitätsstufe und die Kosten pro Bild an. Ein ausklappbarer **Advanced**-Bereich lässt Sie Folgendes überschreiben:

- **Qualität** — Modelle, die Qualitätsstufen unterstützen (eine Standard/Premium-Preisaufteilung), zeigen ein Dropdown; Modelle ohne Stufen zeigen „Default". Stufen werden pro Modell in der Registry über `quality_options` deklariert.
- **Region** — zeigt Regionen, in denen das ausgewählte Modell verfügbar ist, mit Preisen nach günstigstem zuerst sortiert. „Auto" wählt die günstigste Region.

Eine **Kostenschätzung** aktualisiert sich dynamisch basierend auf allen Auswahlen (Modell × Qualität × Region × Optionen × Variationen).

**Formatfamilien**: Modelle werden über einen generischen Invoker (`invoke_image_model`) aufgerufen, der Anfragevorlagen aus der Registry (`format_families`) liest. Derzeit 15 Familien, die Bildgenerierung (2), Bildbearbeitung (8), Nachbearbeitung (2) und Videogenerierung (2) abdecken:

- **Bildgenerierung**: `stability_text_to_image` (SD 3.5 Large, Stable Image Ultra, Stable Image Core) sowie selbst gehostete Familien (`sagemaker_*`) für FLUX, HunyuanImage und Qwen-Image
- **Bildbearbeitung**: `amazon_inpainting`, `amazon_outpainting`, `stability_inpaint`, `stability_outpaint`, `stability_erase`, `stability_search_replace`, `stability_search_recolor`, `stability_control`, `stability_style_transfer`
- **Nachbearbeitung**: `stability_remove_bg`, `stability_upscale`
- **Video**: `nova_reel`, `luma_ray`

Das Hinzufügen eines neuen Bedrock-Bildmodells erfordert null Codeänderungen — registrieren Sie es einfach über die Admin-API oder die Auto-Erkennung mit der korrekten Formatfamilie.

**Modelloptimiertes Prompt-Engineering**: Prompts werden automatisch als beschreibende Bildunterschriften (nicht als Befehle) gemäß der [AWS-Dokumentation](https://docs.aws.amazon.com/nova/latest/userguide/prompting-image-generation.html) strukturiert. Negationswörter werden aus dem Haupt-Prompt entfernt und Ausschlussbegriffe als separater **Negativ-Prompt** gesendet. Der Prompt wird auf das modellspezifische `prompt_limit` aus der Registry gekürzt.

> [!NOTE]
> **Die Moderationssensibilität variiert je nach Modell** und wird in der Registry verfolgt (`moderation_strictness`). Die Amazon-Bedrock-Stability-Modelle (SD 3.5 Large, Stable Image Ultra, Stable Image Core) wenden die AWS-Plattform-Moderation an und sind auf „moderat" eingestellt; selbst gehostete Modelle (FLUX, HunyuanImage, Qwen-Image) laufen in Ihrem eigenen Konto ohne plattformseitig auferlegten Inhaltsfilter. ArtSmoker behandelt Blockaden automatisch — wenn ein Prompt abgelehnt wird, versucht das System alternative Modelle, nach Strenge geordnet, bevor es ein Umschreiben vorschlägt.

## 📌 7. Tech-Stack

| Schicht | Technologie |
|---------|-------------|
| Backend | FastAPI (Python 3.11+), boto3, Pydantic |
| Frontend | Vanilla JS, Tailwind CSS (CDN) |
| KI (LLM) | Claude Sonnet (schnelle Aufgaben), Claude Opus (komplexe Aufgaben) |
| KI (Bild) | Stable Diffusion 3.5 Large, Stable Image Ultra, Stable Image Core (Amazon Bedrock); FLUX.2/FLUX.1, HunyuanImage 3.0, Qwen-Image (selbst gehostet auf SageMaker) |
| KI (Nachbearbeitung) | Stability AI (Remove Background, Creative Upscale) |
| KI (Chat) | 80+ LLMs von 16 Anbietern über Bedrock ConverseStream (Claude, Nova, Llama, Mistral usw.) |
| KI (Video) | Nova Reel v1.0/v1.1 (bis zu 2 Min.), Luma AI Ray v2 (bis zu 9 Sek.) |
| KI (Sprache) | Nova Sonic (Sprache-zu-Text über bidirektionales Streaming) |
| i18n | Benutzerdefinierte t()-Funktion, 817 Schlüssel × 6 Sprachen, DOM-Übersetzung per Rückwärtssuche |
| SVG-Konvertierung | vtracer (primär), potrace (Fallback), Pillow (letzter Ausweg) |
| Text-Rendering | Pillow (Schatten, Kontur, Glüheffekte) |
| Speicherung | Lokales Dateisystem (S3-fähige Schnittstelle) |
| Dev | No-Cache-Middleware für statische Dateien; clientseitiges Fehlerlogging über `POST /api/log` |

Für das Frontend ist kein Build-Schritt erforderlich.

## 📌 8. Sicherheitsmodell

ArtSmoker ist als **Entwicklungswerkzeug für lokale/vertrauenswürdige Netzwerke** konzipiert — es läuft auf der eigenen Maschine des Entwicklers oder einer privaten EC2-Instanz. Das Sicherheitsmodell spiegelt dies wider:

- **Keine Authentifizierung** — alle API-Endpoints sind offen. Angemessen für lokale Entwicklung und private Team-Deployments.
- **Dateisystem-Browser** — der Endpoint `GET /api/browse/local` erlaubt das Durchsuchen jedes Verzeichnisses, auf das der Serverprozess zugreifen kann. Dies ist beabsichtigt für den Import von Referenzgrafik von Ihrer Maschine.
- **Schriftauslieferung** — ein Schutz gegen Path Traversal validiert, dass Anfragen für Schriftdateien innerhalb der erwarteten Verzeichnisse bleiben.
- **S3-Zugriff** — S3-Durchsuchen und -Importe verwenden die AWS-Anmeldeinformationen des Servers. Der Nutzer kann auf jeden S3-Bucket zugreifen, den seine IAM-Rolle erlaubt.

> [!WARNING]
> Setzen Sie ArtSmoker nicht in nicht vertrauenswürdigen Netzwerken ein, ohne Authentifizierung und Pfadbeschränkungen hinzuzufügen. Siehe die [Deployment-Roadmap in SPEC.md](SPEC.md#16-deployment--scaling-roadmap) für Anleitungen zur Produktionshärtung (Phase 4 fügt Cognito-Authentifizierung hinzu).

## 📌 9. API

Interaktive Dokumentation unter **http://localhost:8000/docs** (Swagger UI).

Wichtige Endpoints:

| Endpoint | Zweck |
|----------|-------|
| **Generierung** | |
| `POST /api/generate/` | Assets generieren (Optionen × Variationen) mit SSE-Streaming |
| `POST /api/generate/post-process` | Verarbeitung auf bestehende Assets anwenden |
| `POST /api/generate/edit` | Bildbearbeitung: Inpaint, Outpaint, Radieren, Suchen-Ersetzen usw. Akzeptiert Quellbild, Maske, Prompt, Modell. |
| `POST /api/generate/suggest-edit-prompt` | KI-„Generate Prompt" für die Registerkarte „Bearbeiten": liest das Bild + den Original-Prompt und gibt einen Bearbeitungs-Prompt für einen gegebenen Modus zurück, im Stil des Zielbearbeitungsmodells (Bildunterschrift vs. Anweisung) |
| `POST /api/generate/analyze-moderation` | Einen moderationsblockierten Prompt analysieren und ein sicheres Umschreiben vorschlagen |
| **Stile** | |
| `POST /api/styles/` | Ein Stilprofil erstellen |
| `POST /api/styles/{id}/import` | Referenzen aus einem lokalen Ordner oder S3-URI massenhaft importieren |
| `POST /api/styles/{id}/analyze` | KI-Stilanalyse auslösen |
| **Prompt** | |
| `POST /api/refine-prompt/` | Vorschau eines verfeinerten Prompts |
| `POST /api/transcribe/` | Sprache-zu-Text (Nova Sonic) |
| **Galerie** | |
| `GET /api/gallery/` | Generierte Assets durchsuchen (unterstützt limit/offset-Paginierung) |
| `GET /api/gallery/batch/{batch_id}` | Vollständige Optionen-×-Variationen-Struktur für einen Batch rekonstruieren |
| `DELETE /api/gallery/` | Assets massenhaft löschen |
| **Type Studio** | |
| `POST /api/type-studio/preview` | Text-Overlay-Vorschau rendern |
| `POST /api/type-studio/suggest` | KI-Layout-Vorschlag für Text |
| `GET /api/type-studio/fonts` | Verfügbare Schriften auflisten |
| **Browse** | |
| `GET /api/browse/local?path=~` | Inhalte eines lokalen Verzeichnisses durchsuchen |
| `GET /api/browse/s3/buckets` | Verfügbare S3-Buckets auflisten |
| `GET /api/browse/s3?bucket=name&prefix=path` | Inhalte eines S3-Buckets durchsuchen |
| **Chat** | |
| `POST /api/chat/stream` | LLM-Antwort über SSE streamen (Bedrock ConverseStream) |
| `GET /api/chat/models` | Alle verfügbaren Chat-Modelle auflisten (Foundation + Custom + importiert) |
| `POST /api/chat/sessions` | Eine neue Chat-Sitzung erstellen |
| `GET /api/chat/sessions` | Chat-Sitzungen auflisten |
| `GET /api/chat/sessions/{id}` | Eine vollständige Sitzung laden (Nachrichten + Metadaten) |
| `PUT /api/chat/sessions/{id}` | Sitzung aktualisieren (Titel, Nachrichten, Modell, Temperatur) |
| `DELETE /api/chat/sessions/{id}` | Eine Sitzung löschen |
| `POST /api/chat/sessions/{id}/duplicate` | Eine Sitzung duplizieren |
| `GET /api/chat/sessions/{id}/export` | Sitzung als Markdown exportieren |
| `GET /api/chat/sessions/{id}/search?q=` | Innerhalb der Nachrichten einer Sitzung suchen |
| `POST /api/chat/compact` | Ältere Nachrichten per LLM-Zusammenfassung kompaktieren |
| `POST /api/chat/generate-title` | Einen Sitzungstitel automatisch aus dem ersten Austausch generieren |
| **Video** | |
| `POST /api/video/generate` | Asynchronen Videogenerierungs-Job starten |
| `GET /api/video/status/{job_id}` | Status eines Videogenerierungs-Jobs abfragen |
| `GET /api/video/jobs` | Alle Videogenerierungs-Jobs auflisten |
| `GET /api/video/{id}/mp4` | Video-MP4-Datei ausliefern |
| `GET /api/video/{id}/thumbnail` | Video-Vorschaubild ausliefern |
| `DELETE /api/video/{id}` | Ein Video löschen |
| **Admin** | |
| `GET /api/admin/models` | Vollständige Modellregistry abrufen (LLMs, Bildmodelle, Nachbearbeitung) |
| `GET /api/admin/models/image-options` | Aktivierte Text-to-Image-Modelle für das Dropdown (mit Preisen, Qualitätsstufen, Regionen). Akzeptiert `?region=`-Filter. |
| `GET /api/admin/regions` | Zwischengespeicherte Liste der von Bedrock unterstützten AWS-Regionen (keine AWS-Aufrufe) |
| `PATCH /api/admin/models/category/{name}` | Konfiguration einer LLM-Kategorie aktualisieren |
| `PATCH /api/admin/models/image/{key}` | Konfiguration eines Bildmodells aktualisieren |
| `POST /api/admin/models/image` | Ein neues Bildmodell hinzufügen |
| `POST /api/admin/discover/refresh-all` | Vollständige Aktualisierung: Regionen erkennen + Modelle scannen + Preise abrufen + veraltete Daten bereinigen. Der EINZIGE Endpoint, der die AWS-Erkennungs-APIs aufruft. |
| `POST /api/admin/discover/{region}/auto-register` | Eine einzelne Region nach Modellen scannen, neue registrieren, Regionen für bestehende aktualisieren |
| `GET /api/admin/discover/{region}` | Verfügbare Bedrock-Modelle in einer Region erkennen (rohes Listing) |
| `GET /api/admin/templates` | Alle 28 bearbeitbaren Prompt-Vorlagen abrufen |
| `PATCH /api/admin/templates/{name}` | Eine Vorlage aktualisieren (validiert erforderliche Variablen) |
| `POST /api/admin/templates/{name}/reset` | Eine Vorlage auf Standard zurücksetzen |
| `POST /api/admin/templates/{name}/enhance` | Eine Vorlage mit KI verbessern |
| **System** | |
| `POST /api/log` | Clientseitiges Fehler-/Warnungs-Logging (in der Serverkonsole als `[CLIENT]` aufgezeichnet) |
| `GET /api/health` | Health-Check + AWS-Anmeldeinformations-/Bedrock-Validierung |

## 📌 10. Projektstruktur

```
ArtSmoker/
├── backend/
│   ├── main.py              # FastAPI-App, Startvalidierung, Static-Mount
│   ├── config.py            # Einstellungen (AWS-Regionen, Modell-IDs, Pfade, Limits)
│   ├── model_registry.json  # Einzige Quelle der Wahrheit: Modelle, Regionen, Preise, Formatfamilien, Qualitätsstufen
│   ├── requirements.txt
│   ├── prompt_templates.json # Bearbeitbare LLM-Direktiv-Prompts — Laufzeit-Quelle der Wahrheit (28 Vorlagen)
│   ├── routers/
│   │   ├── generate.py      # Zweistufige Asset-Generierung + SSE-Streaming
│   │   ├── styles.py        # Stilprofil-CRUD + Verzeichnis-/S3-Import + Analyse
│   │   ├── gallery.py       # Asset-Durchsicht + Dateiauslieferung + Massenlöschung
│   │   ├── typestudio.py    # Type Studio: Text-Overlay, Schriftauslieferung, KI-Layout
│   │   ├── video.py         # Videogenerierung (async), Job-Polling, MP4-/Vorschaubild-Auslieferung
│   │   ├── chat.py          # Chat Studio: LLM-Streaming, Sitzungen, Export, Kontext-Kompaktierung
│   │   ├── browse.py        # Serverseitiger Datei-/S3-Browser für Referenzimport
│   │   ├── refine.py        # Vorschau der Prompt-Verfeinerung + Übersetzungsvorschau
│   │   ├── transcribe.py    # Sprachtranskription
│   │   └── admin.py         # Modellregistry-Verwaltung + Bedrock-Erkennung + Prompt-Vorlagen
│   ├── services/
│   │   ├── bedrock_client.py     # Gemeinsamer Bedrock-Client mit Connection-Pooling
│   │   ├── model_registry.py     # Modellregistry: lädt/speichert model_registry.json
│   │   ├── prompt_engineer.py    # Claude: Prompt-Verfeinerung + Konzeptgenerierung
│   │   ├── image_generator.py    # Routet zu Bedrock (SD 3.5 / Ultra / Core) oder SageMaker (FLUX / Hunyuan / Qwen)
│   │   ├── style_analyzer.py     # Zweiphasige Stilanalyse (Kohäsion + vollständig)
│   │   ├── post_processor.py     # Stability AI: Hintergrundentfernung, Hochskalierung; vtracer: SVG
│   │   ├── transcriber.py        # Nova Sonic: Streaming-Sprache-zu-Text
│   │   ├── import_dedup.py       # Intelligente Deduplizierung (Rotationen, Animationen, Ordner)
│   │   ├── texture_extractor.py  # glTF/GLB-Texturextraktion
│   │   ├── prompt_translator.py  # Sprache automatisch erkennen + ins Englische übersetzen
│   │   ├── prompt_templates.py   # Bearbeitbare LLM-Direktiv-Prompts (laden/speichern/validieren)
│   │   ├── video_generator.py   # Video: asynchroner Bedrock-Aufruf, S3-Download, ffmpeg-Vorschaubilder
│   │   ├── cost_tracker.py      # Request-bezogener Kostensammler
│   │   ├── telemetry.py         # PulseBoard-SDK-Wrapper: verfolgt Serverereignisse
│   │   ├── custom_models.py    # Katalog selbst gehosteter Modelle (erweiterbar)
│   │   ├── async_jobs.py       # Warteschlange für asynchrone Generierungs-Jobs (Pending-Jobs-Panel)
│   │   ├── sagemaker_deployer.py # Amazon-SageMaker-Endpoint-Verwaltung (direkter HF-Pull für HF-Modelle)
│   │   └── sagemaker_invoker.py  # Leitet Inferenz an Amazon-SageMaker-Endpoints weiter
│   ├── models/
│   │   ├── style_profile.py       # StyleProfile, AnalyzedStyle, Create/Update
│   │   ├── generation_request.py  # GenerationRequest, AssetType, ImageModel-Enums
│   │   └── generation_result.py   # GenerationResult, OptionResult, VariantResult
│   └── storage/
│       └── local_store.py         # Lokales Dateisystem (S3-kompatible Schnittstelle)
├── frontend/
│   ├── index.html           # SPA-Einstiegspunkt
│   ├── css/styles.css       # Dark Theme + Animationen
│   └── js/
│       ├── app.js               # SPA-Router + DOM-Caching + Navigation + showConfirm()
│       ├── i18n/
│       │   ├── i18n.js          # Kern: t()-Funktion, Sprachwechsel, Rückwärtssuche
│       │   ├── en.json          # Englisch (Basis) — 817 Schlüssel
│       │   ├── ja.json          # Japanisch
│       │   ├── zh.json          # Vereinfachtes Chinesisch
│       │   ├── ko.json          # Koreanisch
│       │   ├── fr.json          # Französisch
│       │   └── es.json          # Spanisch
│       ├── services/api.js      # Backend-API-Client
│       └── components/
│           ├── ImageStudio.js   # 2D Image Studio (Optionen × Variationen)
│           ├── TypeStudio.js    # Type Studio (Text-Overlay)
│           ├── VideoStudio.js   # Video Studio (Text-to-Video-Generierung)
│           ├── ChatStudio.js    # Chat Studio (Multi-Modell-LLM-Chat)
│           ├── Gallery.js       # Galerie-Raster + Suche + Massenoperationen
│           ├── StyleLibrary.js  # Stilverwaltung + Datei-Browser
│           ├── AssetViewer.js   # Vorschau in voller Größe + Metadaten + Download
│           ├── ModelSettings.js # Modellregistry-Admin-UI (Modal)
│           ├── PromptEditor.js  # Zwei-Bereich-Prompt-Editor + Compose
│           └── VoiceInput.js    # MediaRecorder + Transkription
├── data/
│   ├── styles/              # Stilprofile + Referenzbilder (per Symlink)
│   ├── generated/           # Ausgabe-Assets (PNG + SVG + metadata.json)
│   ├── video/               # Video-Assets (MP4 + Vorschaubilder + Job-Metadaten)
│   └── chat/                # Chat-Sitzungen (JSON pro Sitzung)
├── SPEC.md                  # Vollständige technische Spezifikation (Rebuild-Blueprint)
└── README.md                # Diese Datei
```

## 📌 11. Konfigurierbare Limits

Einstellungen in `backend/config.py` können über Umgebungsvariablen (Präfix `ARTSMOKER_`) überschrieben werden:

| Einstellung | Umgebungsvariable | Standard | Zweck |
|-------------|-------------------|----------|-------|
| `max_reference_images` | `ARTSMOKER_MAX_REFERENCE_IMAGES` | 100 | Max. pro Stil importierte Bilder |
| `max_analysis_images` | `ARTSMOKER_MAX_ANALYSIS_IMAGES` | 20 | Max. pro Analyseaufruf an die KI gesendete Bilder |
| `aws_region_models` | `ARTSMOKER_AWS_REGION_MODELS` | us-west-2 | Region für Claude- + Stability-AI-Modelle |
| `aws_region_images` | `ARTSMOKER_AWS_REGION_IMAGES` | us-east-1 | Region für Amazon (Nova Sonic Sprache, Nova Reel Video) |
| `aws_profile` | `ARTSMOKER_AWS_PROFILE` | None | AWS-Profilname (nutzt Standardkette, falls nicht gesetzt) |
| `auto_update` | `ARTSMOKER_AUTO_UPDATE` | true | Git-Pull beim Start + 24-Std.-Periodenprüfung, Selbst-Neustart bei Update |

Das Reduzieren von `max_analysis_images` senkt die KI-Vision-Kosten pro Analyse. Das Reduzieren von `max_reference_images` begrenzt den Speicher. Beide können basierend auf dem Budget angepasst werden.

## 📌 12. Amazon-Bedrock-Preise & Kostenaufschlüsselung

> [!IMPORTANT]
> **Modelle werden schnell abgekündigt und ändern sich.** Neue Modelle erscheinen und alte werden häufig eingestellt, sodass jeder in der Dokumentation fest hinterlegte Modellname oder Preis rasch veraltet. ArtSmoker handhabt dies automatisch — jede **Sync from AWS** erkennt das aktuelle Modellangebot neu, rollt die gemeinsam genutzten LLM-Slots automatisch auf den neuesten Claude Sonnet/Opus und aktualisiert die Live-Preise pro Modell von der AWS Pricing API in `model_registry.json`. **Die App ist die Quelle der Wahrheit** — sowohl dafür, welche Modelle existieren, als auch dafür, was sie kosten (live in der Seitenleiste des Image Studios angezeigt, entsprechend dem ausgewählten Modell, der Qualitätsstufe, der Region und der Batch-Größe). Modellnamen und alle nachstehenden Zahlen sind **nur illustrative Beispiele** — bestätigen Sie die aktuellen Modelle/Preise stets in der App oder auf der offiziellen [Amazon-Bedrock-Preisseite](https://aws.amazon.com/bedrock/pricing/).

Die **Standardregionen** der App sind `us-west-2` (Claude, Stability AI) und `us-east-1` (Amazon Nova Sonic, Nova Reel); die Preise unterscheiden sich je nach Region. Siehe auch [SPEC.md](SPEC.md#14-amazon-bedrock-pricing--cost-breakdown) für das Kostenmodell.

### 📝 12.1 Preise pro Einheit

Was Kosten verursacht und die zugehörige Abrechnungseinheit (den aktuellen Preis pro Einheit finden Sie in der App):

| Service | Abrechnung | Hinweise |
|---------|-----------|----------|
| **LLM-Prompt-Engineering & Chat** (Claude Sonnet / Opus, bei Sync automatisch auf die neueste Version gerollt) | pro Input-/Output-Token | Prompt-Verfeinerung, Konzepte, Chat, Stilanalyse, Moderation |
| **Bedrock-Bildgenerierung** (Stable Diffusion 3.5 Large, Stable Image Ultra, Stable Image Core) | pro Bild | Ultra ≫ SD 3.5 ≫ Core im Preis; Live-Wert in der App angezeigt |
| **Selbst gehostet Bild / 3D** (FLUX, HunyuanImage, Qwen-Image, TripoSG, TRELLIS.2) | pro SageMaker-GPU-Sekunde Ihrer Instanz | Scale-to-Zero im Leerlauf ($0); nicht pro Bild abgerechnet |
| **Nachbearbeitung** (Remove Background, Creative Upscale) | pro Bild | Stability-AI-Services |
| **SVG-Konvertierung** | kostenlos | Lokal (vtracer/potrace) — $0.00 |

> [!NOTE]
> Preise von der offiziellen [Amazon-Bedrock-Preisseite](https://aws.amazon.com/bedrock/pricing/) mit Stand März 2026. Preise können sich ändern — überprüfen Sie sie vor der Budgetierung stets anhand der offiziellen Quelle.

### 📝 12.2 Zusätzliche LLM-Kosten (pro Nutzung)

Diese LLM-Aufrufe sind im Generierungs-Workflow enthalten, aber nicht separat in den Batch-Kostentabellen unten aufgeschlüsselt:

| Aufruf | Modell | Wann | Ungefähre Kosten |
|--------|--------|------|------------------|
| **Prompt Pre-Check** | Claude Sonnet | Vor der Generierung (falls Umschalter aktiviert) | ~$0.005 |
| **Moderation Rewrite** | Claude Sonnet | Nur wenn alle Modelle einen Prompt ablehnen | ~$0.005 |
| **Type Studio Layout** | Claude Opus | Bei jeder KI-Layout-Vorschlagsanfrage | ~$0.02–$0.05 |

Diese sind gering — Vorprüfung und Moderations-Umschreiben kosten jeweils einen Bruchteil eines Cents. Type-Studio-Layout ist mit einer Ein-Options-Prompt-Verfeinerung vergleichbar.

### 📝 12.3 Kosten der Stilanalyse (einmalig pro Stil)

~**$0.14** pro Stil (20 Bilder an Claude Opus gesendet + 8 Bilder Kohäsionsprüfung bei Claude Sonnet). Die Kohäsionsprüfung fügt ~$0.01 hinzu (Sonnet mit 8 Bildern ist sehr günstig).

### 📝 12.4 Generierungskosten nach Batch-Größe

Beinhaltet Prompt-Verfeinerung/Konzeptgenerierung + Bildgenerierung:

| Szenario | Stable Image Core | Stable Diffusion 3.5 Large | Stable Image Ultra |
|----------|-------------------|----------------------------|--------------------|
| 1 Option × 1 Variation | ~$0.05 | ~$0.09 | ~$0.15 |
| 1 Option × 5 Variationen | ~$0.21 | ~$0.41 | ~$0.71 |
| 5 Optionen × 5 Variationen | ~$1.05 | ~$2.05 | ~$3.55 |

Selbst gehostete SageMaker-Modelle (FLUX, HunyuanImage, Qwen-Image) werden nach GPU-Zeit auf Ihrer eigenen Instanz abgerechnet (scale-to-zero im Leerlauf), nicht pro Bild — siehe [SPEC.md](SPEC.md#14-amazon-bedrock-pricing--cost-breakdown) für das Compute-Kostenmodell.

### 📝 12.5 Nachbearbeitungs-Add-ons (pro Bild)

| Add-on | Pro Bild | 1 Bild | 5 Bilder | 25 Bilder |
|--------|----------|--------|----------|-----------|
| Remove Background | $0.07 | $0.07 | $0.35 | $1.75 |
| Creative Upscale | $0.60 | $0.60 | $3.00 | $15.00 |
| Convert to SVG | $0.00 | $0.00 | $0.00 | $0.00 |

> [!TIP]
> **Hinweis zu Creative Upscale**: Behandelt die 16-MB-Antwort-Payload-Grenze von Stability AI automatisch, indem intern das JPEG-Ausgabeformat verwendet und dann zurück in PNG konvertiert wird. Beinhaltet Wiederholung mit exponentiellem Backoff bei API-Drosselung.

### 📝 12.6 Durchgerechnete Beispiele

| Beispiel | Konfiguration | Gesamtkosten |
|----------|---------------|--------------|
| **Am günstigsten** | 1×1, Stable Image Core, keine Verarbeitung | ~$0.05 |
| **Standard** | 1×5, Stable Diffusion 3.5 Large, Remove BG | ~$0.76 |
| **Vollständige Erkundung** | 5×5, Stable Diffusion 3.5 Large, Remove BG + SVG | ~$3.80 |
| **Premium** | 5×5, Stable Image Ultra, Remove BG + Upscale + SVG | ~$20.30 |

> [!TIP]
> **Kernaussage**: Die Bildgenerierung selbst ist günstig ($0.01–$0.14/Bild). **Creative Upscale mit $0.60/Bild ist der dominierende Kostenfaktor** — nutzen Sie es selektiv für Ihre final gewählten Assets, nicht für den gesamten Batch. Remove Background mit $0.07/Bild ist angemessen. Die SVG-Konvertierung ist kostenlos (läuft lokal).

<a id="disclaimer"></a>

## 📌 13. Haftungsausschluss

> [!IMPORTANT]
> **Qualität generierter Inhalte**: Alle Bilder, Videos und anderen von ArtSmoker generierten Assets werden von KI-Modellen erzeugt, die über Amazon Bedrock verfügbar sind, einschließlich sowohl AWS-eigener Modelle als auch Drittanbieter-Modelle. Die Qualität, Genauigkeit und Angemessenheit generierter Inhalte hängen vollständig von den bereitgestellten Prompts, den ausgewählten Modellen und den vom Nutzer hochgeladenen Stilreferenzen ab. Die Autoren und Mitwirkenden von ArtSmoker geben keinerlei Garantien hinsichtlich der Qualität, Eignung oder Tauglichkeit für einen bestimmten Zweck der generierten Inhalte.
>
> **Geistiges Eigentum**: Nutzer sind allein dafür verantwortlich sicherzustellen, dass ihre Prompts, Referenzbilder und generierten Ausgaben keine geistigen Eigentumsrechte Dritter verletzen, einschließlich, aber nicht beschränkt auf Urheberrechte, Marken und Persönlichkeitsrechte. ArtSmoker ist ein Werkzeug — es filtert, validiert oder bewertet den IP-Status von Eingaben oder Ausgaben nicht. Die Autoren und Mitwirkenden des Werkzeugs tragen keine Verantwortung für jegliche IP-Verletzung, die aus der Nutzung dieser Software entsteht.
>
> **KI-Modell- und Servicebedingungen**: Generierte Inhalte unterliegen den Nutzungsbedingungen und Richtlinien zur akzeptablen Nutzung der zugrunde liegenden KI-Modellanbieter, die über Amazon Bedrock zugänglich sind. Nutzer sollten die [AWS Service Terms](https://aws.amazon.com/service-terms/), das [Amazon Bedrock SLA](https://aws.amazon.com/bedrock/sla/) und die einzelnen Modellanbieterbedingungen prüfen, bevor sie generierte Assets in Produktions- oder kommerziellen Kontexten einsetzen.
>
> **Nur Kostenschätzungen — überwachen Sie Ihre eigenen Ausgaben**: Alle in ArtSmoker angezeigten Kosten (pro Bild, pro Video, pro Token, 3D-Compute, Deployment sowie Sitzungs-/Asset-Summen) sind **Schätzungen, nur zur Orientierung**, berechnet aus den von AWS veröffentlichten Preisen und der erwarteten Nutzung. Sie sind **keine Rechnung und keine Garantie** Ihrer tatsächlichen Gebühren. Die tatsächlichen Kosten hängen von den Preisen Ihres AWS-Kontos, der Region, Rabatten, Steuern, Datenübertragung, der Endpoint-Laufzeit (einschließlich inaktiver/warmgehaltener SageMaker-Instanzen), dem Auto-Scaling-Verhalten und Faktoren außerhalb dieses Werkzeugs ab. **Sie sind allein für die Überwachung und Kontrolle Ihrer eigenen AWS-Ausgaben verantwortlich** — nutzen Sie die [AWS Billing Console](https://console.aws.amazon.com/billing/), den [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/) und [Budgets/Abrechnungsalarme](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html), um tatsächliche Gebühren zu verfolgen und zu deckeln. Insbesondere selbst gehostete SageMaker-Endpoints werden weiterhin abgerechnet, solange sie deployt oder warmgehalten werden, selbst im Leerlauf — denken Sie daran, sie abzubauen, wenn Sie fertig sind. Die Autoren und Mitwirkenden tragen keine Verantwortung für jegliche AWS-Gebühren, die durch die Nutzung dieser Software entstehen.
>
> **Keine Gewährleistung**: Diese Software wird „wie besehen" ohne jegliche Gewährleistung bereitgestellt. Siehe [LICENSE](LICENSE) für die vollständigen Bedingungen.

## 📌 14. Vollständige Spezifikation

Siehe **[SPEC.md](SPEC.md)** für die vollständige technische Spezifikation — Architektur, Komponentendesign, Modellkonfiguration, API-Referenz, Sicherheitsmodell, Preise, Deployment-Roadmap und genügend Details, um das Projekt von Grund auf neu zu erstellen.
