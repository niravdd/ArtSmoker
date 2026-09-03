# ArtSmoker
> *Le smoke-test de vos créations artistiques !*

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green?logo=fastapi&logoColor=white)
![Amazon Bedrock](https://img.shields.io/badge/Amazon-Bedrock-orange?logo=amazonaws&logoColor=white)
![License](https://img.shields.io/badge/License-MIT--0-yellow)

![Visite guidée d'ArtSmoker — du prompt texte à l'art 2D prêt pour la production, jusqu'au modèle 3D entièrement texturé prêt pour le moteur de jeu](docs/images/artsmoker-walkthrough.gif)

## 📌 0. Présentation

**ArtSmoker transforme une idée en art prêt pour le moteur de jeu — en quelques minutes, sans aucun pipeline à gérer de votre côté.** Décrivez un personnage, un accessoire, un environnement ou une illustration clé en langage naturel et obtenez de l'art 2D prêt pour la production, des modèles 3D entièrement texturés et de la vidéo — le tout aligné sur l'identité visuelle de votre projet et conservé dans votre propre environnement. Les tout derniers modèles d'IA d'image, d'édition, de 3D et de vidéo se cachent derrière une interface unique, épurée et pensée avant tout pour les artistes, dotée de véritables contrôles créatifs : ArtSmoker exécute l'intégralité du pipeline de production pour vous, afin que votre équipe dirige le rendu au lieu de se débattre avec la mécanique.

### 📝 Le problème

Les équipes créatives des studios de jeux vidéo et de médias veulent tirer parti de l'IA générative — mais aujourd'hui cette puissance est enfermée derrière des outils pour développeurs qu'elles n'ont jamais été censées gérer :

- **C'est conçu pour les ingénieurs, pas pour les artistes** — les meilleurs modèles se trouvent derrière des consoles cloud, des lignes de commande, des SDK et des API REST. Aucun directeur artistique ni concept artist ne devrait avoir besoin d'un terminal pour créer une œuvre.
- **Des idées claires, des prompts obscurs** — les artistes savent exactement ce qu'ils veulent, mais les modèles ne comprennent pas les consignes formulées en langage créatif ordinaire ; des résultats cohérents et conformes au brief dépendent encore de la structure du prompt, des prompts négatifs et d'une formulation spécifique à chaque modèle qui s'interposent entre le brief et le résultat.
- **Les meilleurs modèles d'IA sont dispersés et difficiles à faire tourner** — de puissants modèles d'IA pour l'image, l'édition, la 3D et la vidéo sortent en permanence chez différents fournisseurs et dans différents formats ; mettre en place chacun d'eux (empaquetage, GPU, quantification, mise à l'échelle) constitue à lui seul un projet d'ingénierie complet.
- **L'édition et la 3D sont des mondes distincts** — l'inpainting, l'outpainting, la recoloration, les éditions guidées par référence et la transformation d'un concept 2D en modèle 3D texturé nécessitent normalement chacun leurs propres outils, API et spécialistes.
- **Rester fidèle à votre charte est un travail manuel** — faire en sorte que chaque asset respecte votre apparence établie implique généralement de surveiller chaque génération à la main.

### 📝 La solution

ArtSmoker est un studio créatif auto-hébergé qui place les meilleurs modèles génératifs d'aujourd'hui derrière une interface unique pensée pour les artistes — conçu spécifiquement pour la production d'assets de jeux vidéo, et tout aussi à l'aise dans le cinéma, la publicité, le e-commerce, l'édition et toute équipe qui vit de contenu visuel original.

- **Décrivez-le en langage naturel** — ArtSmoker gère la décomposition des prompts, leur amélioration et l'optimisation spécifique à chaque modèle en coulisses. Un **Prompt Designer** guidé vous permet de façonner chaque élément visuel — sujet, scène, éclairage, couleur — avec des contrôles verrouiller/varier pour explorer des directions véritablement différentes sans perdre ce qui fonctionne déjà.
- **Fidèle à votre charte par défaut** — fournissez à ArtSmoker votre art existant et ses modèles de vision apprennent votre identité visuelle, de sorte que chaque asset produit correspond à l'apparence et à l'atmosphère de votre projet.
- **2D, édité et en 3D — de bout en bout** — générez, puis affinez sur place avec l'inpainting, l'outpainting, la recoloration, le rechercher-remplacer et les éditions guidées par référence ; transformez n'importe quel asset 2D en un **modèle 3D entièrement texturé et prêt pour le moteur de jeu** qui s'intègre directement dans Unity, Unreal ou Blender — sans modélisation manuelle, dépliage UV ni peinture de textures. Plus de la vidéo cinématique et un studio de chat multi-modèle pour l'idéation.
- **Chaque modèle, en un clic** — utilisez les derniers modèles hébergés à travers les régions, ou déployez des modèles open source sélectionnés (Qwen-Image, FLUX.2, HunyuanImage, TripoSG, TRELLIS.2, et plus) sur vos propres GPU en un seul clic — empaquetage, quantification, mise à l'échelle automatique et suivi des tâches entièrement pris en charge, chaque modèle validé de bout en bout avant sa publication.
- **Fonctionne où vous le voulez — et votre IP reste la vôtre** — installez-le sur le poste d'un seul artiste ou sur une instance partagée pour toute l'équipe ; **aucun GPU personnel requis** (les calculs lourds s'exécutent sur des services AWS managés, ou sur des endpoints à mise à l'échelle automatique qu'ArtSmoker démarre et ramène à zéro pour vous). Il ne se connecte qu'à votre propre compte AWS — œuvres, prompts, styles et assets générés restent dans votre environnement, rien ne part vers des services tiers, et vous conservez la pleine propriété de votre IP créative.

**Modèles Amazon Bedrock** : Claude Sonnet/Opus (ingénierie de prompts et chat), Stable Diffusion 3.5 Large, Stable Image Ultra, Stable Image Core, services Stability AI (édition d'images), Nova Reel, Luma AI Ray (génération vidéo), plus 80+ LLM de 16 fournisseurs pour Chat Studio. **Modèles auto-hébergés** : Qwen-Image (text-to-image) et Qwen-Image-Edit (édition guidée par référence + par instruction, Apache-2.0), HunyuanImage 3.0 (BF16/NF4), FLUX.2, FLUX.1, TripoSG et TRELLIS.2 (image-vers-3D), et plus via Amazon SageMaker — avec un catalogue extensible pour ajouter de nouveaux modèles.

**[Commencer maintenant — aller aux prérequis et à l'installation ▸](#get-started)**

### Language / 言語 / 语言 / 언어 / हिन्दी / Язык / Langue / Idioma

ArtSmoker prend en charge 9 langues. Changez la langue de l'interface via les boutons de langue dans la barre de navigation supérieure (EN | 日 | 中 | 한 | हिं | РУ | FR | ES | DE). Votre sélection est automatiquement sauvegardée.

| Langue | README |
|--------|--------|
| English | [README.md](README.md) |
| 日本語 (Japanese) | [README.ja.md](README.ja.md) |
| 中文 (Chinese) | [README.zh.md](README.zh.md) |
| 한국어 (Korean) | [README.ko.md](README.ko.md) |
| हिन्दी (Hindi) | [README.hi.md](README.hi.md) |
| Русский (Russian) | [README.ru.md](README.ru.md) |
| Français (French) | Ce document |
| Español (Spanish) | [README.es.md](README.es.md) |
| Deutsch (German) | [README.de.md](README.de.md) |

**Prise en charge multilingue des prompts :**
- Les prompts non anglais sont automatiquement détectés (japonais, chinois, coréen, hindi, russe, français, espagnol, et plus) et traduits en anglais avant la génération
- Un aperçu bilingue apparaît dans la zone de prompt : basculez entre votre texte original et la traduction anglaise pour voir exactement ce que le modèle recevra
- Le prompt original, la langue détectée et la traduction anglaise sont tous conservés dans les métadonnées de l'asset
- Les noms de fichiers sont générés à partir du prompt traduit en anglais (par exemple « 病院の建物 » → `hospital-building_opt1_var1.png`)
- Chat Studio transmet les prompts directement au LLM (sans traduction), car des modèles comme Claude sont nativement multilingues
- Le texte de Type Studio reste dans votre langue (il est rendu tel quel sur l'image)
- Toutes les pré-vérifications de modération et le filtrage de contenu s'appliquent sur le prompt traduit en anglais, par souci de cohérence

## 📌 1. Fonctionnalités

ArtSmoker fonctionne en deux modes — **autonome** (aucune configuration de style ou de thème nécessaire, décrivez et générez simplement) et **guidé par le style** (téléchargez votre art existant, et chaque génération correspond à votre identité visuelle). Les deux modes utilisent les mêmes studios et le même pipeline de génération.

### 📝 Mode autonome (démarrage rapide)

Aucune configuration de style ou de thème nécessaire — ouvrez le 2D Image Studio, le Video Studio ou le Type Studio et commencez à créer immédiatement.

1. **Décrivez ce dont vous avez besoin** — saisissez un prompt comme « hospital building » ou « fire mage character », ou utilisez l'entrée vocale. L'IA décompose votre idée en composants visuels, l'améliore avec des optimisations spécifiques au modèle, et respecte votre intention créative grâce à des contrôles intelligents verrouiller/varier. Écrivez dans n'importe quelle langue — les prompts non anglais sont traduits automatiquement.
2. **Choisissez vos modèles et paramètres** — multi-sélection parmi tous les modèles text-to-image disponibles (Amazon Bedrock + auto-hébergés sur SageMaker), choisissez les dimensions, le niveau de qualité et la région. Cochez plusieurs modèles pour une comparaison côte à côte, ou un seul pour une génération ciblée. L'estimation des coûts se met à jour en temps réel.
3. **Obtenez des options véritablement différentes** — le système génère jusqu'à 5 concepts créatifs distinctement différents (variant la tenue, l'ambiance, l'éclairage, la composition — pas seulement l'angle de caméra), chacun avec jusqu'à 5 variations de seed (25 images au total). Les détails spécifiés par l'utilisateur sont verrouillés ; les détails inférés par l'IA sont variés audacieusement. Un contrôle **Seed** visible rend les lots reproductibles — la même graine, avec le même prompt final et les mêmes réglages, régénère les mêmes images, et cliquer sur un résultat reprend sa graine pour ne modifier qu'un paramètre et bifurquer depuis un favori.
4. **Éditez et affinez** — utilisez l'inpainting, l'outpainting, l'effacement, la recherche et remplacement ou la recoloration directement dans l'Asset Viewer. Chaque modification crée une nouvelle version — l'original est toujours préservé.
5. **Téléchargez des fichiers prêts pour le jeu** — PNG avec fond transparent + SVG, nommés de manière descriptive (par exemple `hospital-building_opt2_var3.png`). Les vidéos s'exportent en MP4.

### 📝 Mode guidé par le style (correspondre à votre style artistique et thème)

Pour les équipes qui veulent que chaque asset généré corresponde à un style artistique existant — téléchargez des images de référence et laissez l'IA apprendre d'abord votre identité visuelle.

1. **Téléchargez l'art de votre jeu** — importez des images de référence depuis des répertoires locaux (scan récursif, liens symboliques pour éviter la duplication) ou des buckets S3 (listing récursif avec pagination). **Le dédoublonnage intelligent** s'exécute automatiquement — supprime les variantes de rotation (barrel_N/E/S/W.png ne conserve que barrel_S.png) et les frames d'animation (Idle0-Idle8 ne conserve que Idle). Par exemple, un pack d'assets isométriques de 747 fichiers est dédupliqué à environ 99 objets uniques. Formats supportés : .png, .jpg, .jpeg, .gif, .bmp, .webp, .tiff, .tif, .tga, .ico, .svg, plus extraction automatique de textures depuis les modèles 3D (.glb, .gltf).
2. **L'IA apprend votre style** — analyse en deux phases avec détection de cohésion : d'abord, une vérification rapide détermine si votre collection est unifiée, structurellement cohérente ou diverse. Ensuite, une analyse approfondie de l'ensemble complet de références produit un profil de style riche en métadonnées — palettes de couleurs, épaisseurs de traits, motifs d'éclairage, règles de composition et conventions de production. Si vous fournissez des indications de génération, l'IA les reçoit comme « Artist's Guidance » afin que l'analyse comprenne votre intention, pas seulement ce qui est visible.
3. **Générez avec le style appliqué** — lorsque vous sélectionnez un style dans l'Image Studio, chaque prompt est automatiquement enrichi avec les directives visuelles de votre style. Un prompt comme « hospital building » devient une instruction de génération détaillée incluant la palette de couleurs, les conventions de perspective et le style de rendu de votre jeu.
4. **Tout du mode autonome s'applique** — options multiples, comparaison de modèles, édition, versionnement et téléchargements prêts pour le jeu fonctionnent de la même manière, désormais guidés par votre style artistique.

> [!NOTE]
> Tout le contenu généré est produit par des modèles d'IA et dépend des prompts et des références que vous fournissez. Veuillez consulter la [clause de non-responsabilité](#disclaimer) concernant la qualité du contenu, la propriété intellectuelle et les conditions de service applicables avant d'utiliser des assets générés en production.

### 📝 1.1 Aperçu des fonctionnalités

- 🎨 **Style Library** — Téléchargez votre art, l'IA apprend votre identité visuelle
- 🖼️ **2D Image Studio** — Génération d'images avec options x variations, workflow de prompt guidé en 3 étapes
- 🎨 **Prompt Designer** — L'IA décompose votre prompt en composants visuels éditables (sujet, scène, éclairage, couleurs) avec bascules verrouiller/varier par champ, intégration du style et classification intelligente du type d'asset. Photorealistic, Character, Environment, et plus
- 🎬 **Video Studio** — Text-to-video avec guidance de prompt spécifique au modèle (contrôles caméra Nova Reel, langage naturel Luma Ray), multi-shot, image-to-video
- ✍️ **Type Studio** — Superpositions de texte conçues par l'IA avec sélecteur de polices
- 💬 **Chat Studio** — Chat LLM multi-modèle avec streaming, Markdown, coloration syntaxique, vision, sessions, compactage de contexte
- 📁 **Galerie unifiée** — Disposition en maçonnerie (masonry) qui affiche chaque asset à son véritable ratio (portrait, carré, paysage — jamais recadré). Parcourez images + vidéos, filtre par média (Tout / 2D Artwork / 3D Models / Video), recherche, horodatages complets date-heure-fuseau, téléchargement, suppression. Les assets qui possèdent déjà un modèle 3D généré portent un **badge 3D**, et le filtre **3D Models** ne fait remonter que ceux-là
- 📥 **Importer une image** — Intégrez une image existante (tout format) dans la galerie comme un asset à part entière. Convertie automatiquement en PNG, associée au type d'asset que vous choisissez, et immédiatement éditable et prête pour la 3D — tout (versionnage, édition, image-vers-3D) fonctionne exactement comme pour une image générée
- ✏️ **Édition d'images** — Inpainting, outpainting, effacement, rechercher-remplacer, recoloration (dans l'AssetViewer). Chaque mode dispose d'un bouton IA **Générer le prompt** : un modèle de vision lit l'image + son prompt d'origine et propose un prompt d'édition adapté à ce mode et au modèle d'édition sélectionné (légende descriptive pour les éditeurs Stability, instruction pour Qwen-Image-Edit). Étendre/Outpaint affiche un aperçu en direct de l'agrandissement du cadre avec des règles en pixels pour voir exactement de combien le canevas s'étendra avant de valider. Les éditeurs à instructions (Qwen-Image-Edit) prennent en charge **les cinq modes sans masque** — y compris une véritable extension du canevas : ArtSmoker pré-remplit le canevas, fait compléter uniquement la nouvelle zone par le modèle, puis réintègre vos pixels d'origine intacts. Chaque version éditée affiche **les deux étiquettes de modèle** — le générateur d'origine et l'éditeur qui a produit cette version
- 📤 **Export et détourages** — Artefacts d'export par version dans l'AssetViewer : un détourage PNG transparent (fond supprimé) plus de vraies vectorisations SVG (avec et sans fond). La suppression d'arrière-plan se choisit à chaque exécution : **gratuite sur l'appareil** (rembg/u2net, aucun coût cloud) ou le suppresseur **payant Amazon Bedrock** — le même choix est proposé lors de la préparation des images pour la génération 3D
- 🔄 **Progression en temps réel** — Streaming SSE avec visibilité des tentatives/limitations
- 🛡️ **Modération intelligente** — Test canari, changement automatique de modèle, réécriture assistée par l'IA
- ⚙️ **Model Registry** — Interface d'administration organisée par studio (Image, Video, Chat, Type, Shared), découverte Bedrock, support des modèles personnalisés
- 📝 **Prompt Templates** — 28 prompts directifs LLM éditables, amélioration assistée par l'IA, validation de variables avec correction automatique
- 📦 **Versionnage des assets** — Édition sur place avec historique des versions (v1, v2…), navigation entre versions et suppression par version : ne supprimez qu'une seule version (les autres gardent leurs numéros), la visionneuse bascule sur la version précédente — supprimer la dernière version retire tout l'asset
- 💰 **Suivi des coûts** — Dépenses AWS estimées par requête, par session, par asset, calculées à partir des tarifs AWS en direct par région ; les modèles auto-hébergés affichent le tarif horaire de fonctionnement de l'instance GPU + le temps de génération typique (et non un prix par image trompeur)
- 🌐 **i18n en 9 langues** — Traduction complète de l'UI (EN, JA, ZH, KO, HI, RU, FR, ES, DE), détection automatique des prompts non anglais (l'UI anglaise saute entièrement la détection), aperçu bilingue
- 🔍 **Support des modèles personnalisés** — Découverte automatique des modèles Bedrock fine-tunés, importés et déployés
- 🔧 **Modèles auto-hébergés — Déploiement en 1 clic** — Parcourez un catalogue organisé de modèles open source pré-testés (Qwen-Image, Qwen-Image-Edit, HunyuanImage 3.0, FLUX.2, FLUX.1, TripoSG, TRELLIS.2, et plus), choisissez une instance GPU, et cliquez sur Deploy. ArtSmoker gère tout : empaquetage du gestionnaire d'inférence, configuration de la quantification, sélection du bon toolkit CUDA, mise en place de l'auto-scaling, enregistrement des alarmes CloudWatch, et câblage du suivi asynchrone des tâches. Chaque modèle du catalogue est validé de bout en bout — du démarrage à froid à la génération jusqu'à la livraison en galerie — pour que vous n'ayez pas à déboguer les pilotes GPU, les dépassements de mémoire ou la compatibilité des conteneurs. Supporte BF16 + FlashInfer pour la meilleure qualité, NF4 pour l'efficacité des coûts, détection automatique multi-GPU, mise à l'échelle automatique à zéro (0$ en veille), et le même modèle fonctionne sur différents types d'instances sans reconfiguration
- 🧊 **Génération Image-to-3D** — Convertissez n'importe quelle image Game Asset ou Character en un maillage 3D texturé (GLB) en un clic. La synthèse multi-vues + le baking de textures produit des assets prêts pour les moteurs de jeu. Visionneuse 3D interactive avec orbite/zoom/panoramique
- 🩹 **Complétion intelligente de la source pour la 3D** — l'image-to-3D ne peut construire que ce qui est visible ; un personnage recadré (jambes coupées) donne un maillage sans jambes. Avant la génération, ArtSmoker vérifie l'image source par vision et, si elle est recadrée, **propose de la compléter** par outpainting (invite suggérée par l'IA, entièrement modifiable) — affiche l'avant/après, réexamine le résultat, permet d'étendre encore ou d'abandonner, et l'enregistre comme nouvelle version d'image. Optionnel et non bloquant ; les images bien cadrées sont générées directement
- 🔄 **Auto-Update** — Git pull avec contrôle de version au démarrage, redémarrage automatique après mise à jour, vérification périodique toutes les 24h (`ARTSMOKER_AUTO_UPDATE=false` pour désactiver)

### 📝 1.2 Captures d'écran

**2D Image Studio** — Paramètres à gauche avec liste déroulante multi-sélection de modèles, type d'asset, dimensions et options de post-traitement. Workflow de prompt en 3 étapes à droite avec les boutons Prompt Designer et Generate Enhanced Prompt. Déclaration IP et estimation des coûts en bas.

![2D Image Studio — Paramètres, workflow de prompt et contrôles de génération](docs/images/image-studio-top.png)

**2D Image Studio — Résultats de génération** — Le prompt amélioré est affiché au-dessus, les résultats de comparaison multi-modèle en dessous. Chaque modèle génère indépendamment avec une optimisation du prompt spécifique à chaque modèle. Les résultats affichent le nom du modèle, les dimensions et le coût de génération.

![2D Image Studio — Prompt amélioré et résultats de génération](docs/images/image-studio-results.png)

**2D Image Studio — Comparaison de modèles** — Grille de comparaison côte à côte de tous les modèles sélectionnés (8 affichés — Amazon Bedrock et auto-hébergés à égalité). Chaque carte d'option porte sa propre bande de variations ; le prompt négatif propre au modèle est affiché pour l'option sélectionnée. Les bascules de post-traitement (Remove Background, Convert to SVG, Upscale) s'appliquent aux résultats existants sans régénération.

![2D Image Studio — Grille de comparaison multi-modèle avec variations](docs/images/image-studio-comparison.png)

**Image Inspiration (guidée par référence)** — Déposez 1 à 3 images de référence, dites ce que vous voulez, et choisissez leur usage : **Fidèle à la référence** (édition fidèle au pixel sur un modèle d'édition d'images déployé) ou **Inspiré de la référence** (une IA de vision écrit le prompt enrichi — fonctionne avec n'importe quelle sélection de modèles, options et variations). Le prompt dérivé est prévisualisé et entièrement modifiable avant la génération.

![Image Inspiration — images de référence, instruction et prévisualisation modifiable du prompt enrichi](docs/images/image-inspiration.png)

**Image Inspiration — Résultats** — La référence devient une nouvelle création (ici, une caricature dessinée à partir de la photo de référence), avec le prompt exact envoyé au modèle et le coût par image enregistrés.

![Image Inspiration — caricatures générées à partir d'une image de référence](docs/images/image-inspiration-results.png)

**Prompt Designer** — L'IA décompose votre prompt en composants visuels éditables (Subject, Scene, Composition, Lighting, Style & Colors). Chaque champ peut être édité individuellement avec des contrôles verrouiller/varier pour des options créatives véritablement distinctes.

![Prompt Designer — Décomposition visuelle structurée avec champs éditables](docs/images/prompt-designer-top.png)

**Prompt Designer — Palette de couleurs** — Palettes de couleurs nommées avec échantillons hexadécimaux, mots-clés de style et contrôles de niveau de qualité. L'IA apprend votre identité visuelle et l'applique de manière cohérente à toutes les générations.

![Prompt Designer — Palette de couleurs, mots-clés de style et contrôles de qualité](docs/images/prompt-designer-bottom.png)

**Style Library** — Téléchargez l'art existant de votre jeu, l'IA analyse le style visuel et produit un guide de prompts riche en métadonnées. Les images de référence sont affichées avec l'analyse IA complète et le profil de style JSON.

![Style Library — Analyse de style IA avec images de référence](docs/images/style-library-top.png)

![Style Library — Images de référence, options d'importation et données d'analyse](docs/images/style-library-bottom.png)

**Galerie** — Vue unifiée de toutes les images et vidéos générées avec filtre par type de média, filtre par style, recherche et tri. Cliquez sur n'importe quel asset pour ouvrir la vue complète. Le bouton **Importer une image** ajoute une image existante à la galerie — choisissez un type d'asset (Character/Game Asset activent la 3D), elle est convertie en PNG et rendue instantanément éditable et prête pour la 3D.

![Galerie — Grille d'assets générés avec filtres](docs/images/gallery.png)

**Asset Viewer** — Aperçu en taille réelle avec interface à onglets (PNG, Edit, Export & Cutouts, Metadata, 3D Model), barre de versions de l'image et téléchargement direct PNG/SVG. Contrôles zoom/ajustement/mesure sur l'image composée en damier.

![Asset Viewer — Aperçu en taille réelle avec options de téléchargement](docs/images/asset-viewer.png)

**Asset Viewer — Édition d'images** — Cinq modes d'édition : Remplir/Remplacer, Supprimer, Étendre, Rechercher et remplacer, Recolorer. Ici : **Étendre**, avec la règle de mesure, les valeurs en pixels par côté et le bouton ✨ Générer le prompt, qui lit l'image et écrit le prompt d'édition pour vous. L'historique des versions est préservé — les originaux ne sont jamais écrasés.

![Asset Viewer — Extension avec règle de mesure et prompt suggéré par l'IA](docs/images/asset-viewer-edit.png)

**Asset Viewer — Export & Cutouts** — Des artefacts par version, prêts pour votre jeu, moteur ou outil de design : SVG vectoriel de l'image complète, découpe PNG sans arrière-plan et découpe SVG. La suppression d'arrière-plan s'exécute gratuitement sur votre machine (un traitement payant Amazon Bedrock est optionnel).

![Asset Viewer — Export & Cutouts avec SVG vectoriel et découpes sans arrière-plan](docs/images/asset-viewer-export-cutouts.png)

Après un passage d'outpainting (v3 ci-dessous), le même onglet régénère les trois artefacts pour la version corps entier améliorée.

![Asset Viewer — Export & Cutouts pour la version corps entier après outpainting](docs/images/asset-viewer-export-cutouts-outpainted.png)

**Asset Viewer — Metadata** — La généalogie complète du prompt (votre prompt → décomposition Prompt Designer → prompt recomposé → prompt raffiné adapté au modèle), les détails de génération, la ventilation des coûts et l'historique complet des versions.

![Asset Viewer — Metadata avec généalogie complète du prompt et historique des versions](docs/images/asset-viewer-metadata.png)

*Les captures d'écran du pipeline 3D — génération, vérification de la source, export prêt pour moteur et variantes — sont présentées plus bas, dans la section 1.9 (Génération de modèle 3D), aux côtés des fonctionnalités qu'elles illustrent.*

**Video Studio** — Paramètres à gauche (modèle, mode de génération, durée, région, estimation des coûts), prompt à droite. Prend en charge Nova Reel (plan unique, multi-shot auto/manuel jusqu'à 2 minutes) et Luma AI Ray (rapports d'aspect, boucle).

![Video Studio — Paramètres et prompt](docs/images/video-studio.png)

![Video Studio — Génération en cours avec prompt amélioré par l'IA](docs/images/video-studio-generating.png)

![Video Studio — Vidéo terminée avec vignette et vidéos récentes](docs/images/video-studio-completed.png)

**Lecteur vidéo** — Cliquez sur une vidéo pour la lire en ligne avec toutes les métadonnées (prompt original, prompt amélioré par l'IA, modèle, durée, région).

![Lecteur vidéo — Lecture d'une vidéo générée avec métadonnées](docs/images/video-player.png)

### 📝 1.3 Génération à deux niveaux

Pour chaque prompt, l'IA crée des **Options** — des interprétations de design fondamentalement différentes (par exemple pour « a warrior » : berserker viking, samouraï japonais, guerrier tribal, cyber-soldat, hoplite grec). Pour chaque option, le modèle d'image produit des **Variations** — différents seeds aléatoires donnant des différences visuelles subtiles. Cela offre aux artistes une large palette créative pour faire leur choix.

### 📝 1.4 Sélection multi-modèle

Le menu déroulant des modèles prend en charge la **multi-sélection par cases à cocher** — choisissez n'importe quelle combinaison de modèles pour une seule génération :

- **Modèle unique** — cochez un modèle pour une génération ciblée (le plus rapide, le moins cher)
- **Plusieurs modèles** — cochez 2-3 modèles spécifiques pour une comparaison ciblée (ex : SD 3.5 + FLUX.2 uniquement)
- **All Available Models** — le toggle en bas sélectionne/désélectionne tous les modèles activés pour une comparaison côte à côte complète

Chaque modèle s'exécute indépendamment : si des modèles plus stricts bloquent le prompt, vous obtenez quand même les résultats des modèles qui l'ont accepté, avec des étiquettes de statut claires (succès, bloqué par la modération, ou échec) sur chaque carte d'option. L'estimation des coûts se met à jour en temps réel au fur et à mesure que vous cochez/décochez les modèles.

Un toggle optionnel **« Model-optimized prompts »** adapte le prompt aux forces de chaque modèle — les prompts sont réécrits par modèle (ex : boosters de qualité pour SD 3.5, langage naturel pour FLUX.2, repères de rendu de texte de premier plan pour Qwen-Image).

### 📝 1.5 Génération guidée par référence

Au-delà de l'écriture d'un prompt à partir de zéro, vous pouvez générer **à partir de 1 à 3 images de référence plus une instruction** — choisissez le mode avec le contrôle segmenté en haut de la zone de prompt de l'Image Studio :

- **Match the reference** — conservez le sujet, le produit ou le personnage de votre référence et changez le reste (thème, arrière-plan, tenue, éclairage) exactement comme le dit votre instruction. Idéal pour des personnages cohérents ou des photos de produit à travers plusieurs scènes. Ce mode s'exécute sur un éditeur à instructions auto-hébergé (Qwen-Image-Edit) et apparaît **une fois qu'il est déployé** — s'il ne l'est pas, ArtSmoker vous dirige directement pour le déployer depuis Custom Models (un clic, même flux que les pipelines 3D). Sûr pour un usage commercial (Apache-2.0).
- **Inspired by the reference** — l'IA de vision d'ArtSmoker lit vos référence(s) et votre instruction, rédige un prompt amélioré (montré d'abord), puis génère avec vos modèles text-to-image habituels. **Toujours disponible** — aucun déploiement nécessaire. Idéal pour emprunter une apparence, une palette ou une composition sans copier le sujet.

- **Remixer la référence (Remix the reference)** — l'image-to-image classique piloté par la force : les *pixels* de votre référence vont directement dans un modèle Bedrock (Stable Diffusion 3.5 Large ou Stable Image Ultra — déterminé par le drapeau de capacité du registre), avec un **curseur de force** : subtil conserve presque intacts la composition, la palette et l'ambiance ; audacieux la traite comme une inspiration libre. Avec plus d'une Option, cela devient une **échelle de forces** — une carte par force, du subtil à l'audacieux, côte à côte. *Conserve la mise en page, pas l'identité* (les visages et produits dérivent — utilisez Fidèle à la référence pour un travail exact). La taille de sortie suit l'image de référence. **Toujours disponible** — aucun déploiement, aucun appel d'analyse visuelle.

Les trois modes requièrent une instruction pour que vous gardiez le contrôle de ce à quoi sert la référence. La génération guidée par référence est distincte de la Style Library (qui analyse de nombreuses images en un profil de style réutilisable) — utilisez-la pour des générations ponctuelles pilotées par l'image.

### 📝 1.6 Video Studio

Générez des vidéos et animations propulsées par l'IA à partir de prompts textuels. Prend en charge **Amazon Nova Reel** (v1.0, v1.1) et **Luma AI Ray** (v2.0).

| Fonctionnalité | Nova Reel | Luma Ray v2 |
|----------------|-----------|-------------|
| **Durée max** | 120s (2 minutes) | 9 secondes |
| **Résolution** | 1280x720 | 720p / 540p |
| **Rapports d'aspect** | 16:9 uniquement | 7 options (1:1, 16:9, 9:16, etc.) |
| **Image-to-video** | Oui (frame de départ) | Oui (frame de départ + de fin) |
| **Vidéo en boucle** | Non | Oui |
| **Contrôle multi-shot** | Oui (auto + manuel) | Non |
| **Prix** | ~$0.08/s | ~$1.50/s |

**Fonctionnement :**
1. Sélectionnez un modèle vidéo et configurez la durée, le rapport d'aspect, la région
2. Saisissez un prompt — l'IA l'enrichit avec un vocabulaire cinématographique, des mouvements de caméra et des repères de cohérence temporelle
3. Cliquez sur Generate — le job s'exécute de manière asynchrone via `StartAsyncInvoke`, la sortie va dans votre bucket S3 configuré
4. Interrogation du statut toutes les 5 secondes — à l'achèvement, la vignette est extraite (via ffmpeg) et le MP4 est téléchargé localement (ou streamé depuis S3)
5. Les vidéos apparaissent à la fois dans la section « Recent Videos » du Video Studio et dans la galerie unifiée

**Bucket S3 requis** : La génération vidéo envoie ses sorties vers S3. Vous pouvez configurer via Video Settings dans l'UI (parcourir les buckets existants ou en créer un nouveau), ou en créer un via CLI :

```bash
# Create an S3 bucket for video storage (replace REGION and YOUR_ORG)
aws s3api create-bucket --bucket artsmoker-video-YOUR_ORG --region us-east-1

# For regions other than us-east-1, add the LocationConstraint:
aws s3api create-bucket --bucket artsmoker-video-YOUR_ORG --region us-west-2 \
  --create-bucket-configuration LocationConstraint=us-west-2
```

Mode de stockage : téléchargement local (par défaut) ou streaming depuis S3 à la demande.

**Amélioration des prompts vidéo** : Le LLM ajoute des mouvements de caméra (panoramique, zoom, dolly, tracking), des détails d'éclairage et des repères temporels. Comme les modèles vidéo ne supportent pas les prompts négatifs, les concepts à éviter sont intégrés naturellement dans le prompt positif.

### 📝 1.7 Chat Studio

Une interface de chat LLM complète — comme une IA conversationnelle auto-hébergée, fonctionnant sur votre propre compte AWS sans accès tiers aux données.

**80+ modèles de 16 fournisseurs** — Claude (Sonnet, Opus, Haiku), Amazon Nova, Meta Llama, Mistral, Cohere, Qwen, DeepSeek, Google Gemma, NVIDIA Nemotron, et bien d'autres. Plus tous les modèles personnalisés/importés de votre compte. Tous découverts automatiquement via Sync from AWS.

**Fonctionnalités principales :**
- **Réponses en streaming** — rendu token par token en temps réel via Bedrock ConverseStream
- **Rendu Markdown** — titres, gras/italique, listes, tableaux, citations, lignes horizontales
- **Blocs de code** — coloration syntaxique (highlight.js) avec badge de langage + bouton copier
- **Métriques par message** — tokens entrée/sortie, latence, coût estimé, modèle utilisé
- **Barre de fenêtre de contexte** — indicateur visuel de remplissage (vert/ambre/rouge) avec compteur de tokens utilisés/maximum
- **Changement de région** — chaque modèle affiche toutes les régions disponibles, choisissez la plus proche ou la moins chère

**Gestion des sessions :**
- Sessions multiples simultanées avec sauvegarde automatique
- Renommage en ligne, duplication, suppression, recherche/filtre dans la barre latérale
- Export des conversations en Markdown
- Totaux de session : nombre de tokens, coût estimé, nombre de messages

**Fonctionnalités avancées :**
- **Modèles de prompts système** — General Assistant, Coding Expert, Creative Writer, Game Designer, Data Analyst, Technical Writer
- **Vision/multimodal** — glisser-déposer, sélecteur de fichiers ou Ctrl+V pour coller des images pour les modèles compatibles vision
- **Compactage de contexte** — l'IA résume les messages anciens pour libérer de l'espace dans la fenêtre de contexte
- **Régénérer** — relancer n'importe quelle réponse de l'IA avec le même prompt
- **Éditer et renvoyer** — modifier n'importe quel message utilisateur et rejouer à partir de ce point
- **Forker** — créer une branche de conversation depuis n'importe quel message vers une nouvelle session

**Transparence tarifaire :** le sélecteur de modèle affiche le coût par 1K tokens, la barre d'information tarifaire affiche le coût estimé pour des conversations de 10K et 100K tokens.

### 📝 1.8 Sensibilité au type d'asset

Le **type d'asset** sélectionné change fondamentalement la façon dont l'IA interprète votre prompt — pas seulement le modèle d'image, mais chaque étape du pipeline. Quand vous tapez « hospital » et sélectionnez différents types d'assets, vous obtenez des résultats complètement différents :

| Type | Composition | Cadrage | Approche technique |
|------|-------------|---------|-------------------|
| **Photorealistic Image** *(par défaut)* | Cadrage naturel, de type photographique — le sujet dans un environnement réel adapté au contexte. | Perspective de caméra réelle : hauteur d'œil, faible profondeur de champ pour les portraits, grand angle pour les paysages. | Dirigé dans le langage de la photographie (heure dorée, softbox de studio, sensation de focale) avec des imperfections naturelles — texture de peau, plis de tissu, patine. Jamais de vocabulaire d'illustration ni de jargon de moteur de rendu. |
| **Game Asset** | Objet unique isolé sur fond transparent. Pas de scène, pas de texte, pas d'UI. | Vue frontale ou isométrique, l'objet remplit 70-80% du cadre. | Bords nets et propres pour la suppression de fond, éclairage cohérent depuis le haut-gauche, pas d'ombres au sol. Conçu pour être composé avec d'autres assets de jeu à différentes échelles. |
| **Character** | Figure en pied ou 3/4, isolée sur fond propre. Un seul personnage. | Le personnage remplit 60-75% de la hauteur, de la tête aux pieds, légèrement décentré. | Silhouette lisible et forte (identifiable par la silhouette seule), pose expressive transmettant la personnalité, traits du visage et détails du costume clairs. |
| **Icon** | Symbole unique, gras et reconnaissable, centré avec un padding généreux. Simplicité maximale. | Vue frontale ou légère inclinaison 3/4, espace respirant aux bords. | Doit être clairement lisible à 64x64 pixels. Contraste élevé, 3-5 couleurs maximum, formes audacieuses, pas de lignes fines ni de détails fins. |
| **Marketing Banner** | Illustration scénique complète avec composition dramatique. Zone de texte propre réservée sur un côté — pas de texte rendu ni de typographie. | Sensation cinématique large, caméra reculée pour montrer une scène. | Couleurs riches et saturées, éclairage dramatique (rim light, rayons volumétriques), profondeur de champ. L'IA est explicitement instruite de NE PAS rendre de texte ; la zone réservée au texte est laissée propre pour la superposition en post-production dans les outils de design (Figma, Canva, etc.). |
| **Environment** | Paysage complet avec couches de profondeur avant-plan/milieu/arrière-plan et lignes directrices. | Plan d'ensemble large, horizon au tiers supérieur ou inférieur. | Perspective atmosphérique (objets distants plus clairs/brumeux), narration environnementale par les détails, éclairage d'ambiance. |

Cela compte à chaque étape :

- **Bouton « Preview Enhanced Prompt »** — Quand vous cliquez sur Compose, l'IA utilise le type d'asset pour reformuler votre brief en un prompt de génération détaillé, combinant vos mots avec les directives de style et les directives du type d'asset. Votre intention explicite prévaut toujours sur les paramètres par défaut du style. Vous pouvez examiner la version composée avant de générer.
- **Génération de concepts** — Lors de la génération d'options multiples, l'IA crée N interprétations de design différentes qui respectent toutes les règles structurelles du type d'asset. Une option Character a toujours une silhouette lisible ; une option Marketing Banner a toujours une zone de texte sans texte rendu.
- **Le résultat** — Deux images du même prompt mais de types d'assets différents ne se ressembleront en rien. Un Game Asset « warrior » est un sprite de personnage unique centré. Un Marketing Banner « warrior » est une scène de bataille épique avec une zone propre pour la superposition du titre.

### 📝 1.9 Génération de modèles 3D (Image-to-3D)

Générez des maillages 3D entièrement texturés à partir de n'importe quelle image 2D — directement dans l'Asset Viewer. Sélectionnez une image **Game Asset** ou **Character**, ouvrez l'onglet **3D Model**, et cliquez sur Generate. Le résultat est un GLB prêt pour le moteur de jeu que vous pouvez orbiter, zoomer et télécharger — sans modélisation manuelle, dépliage UV ni peinture de texture.

**Le résultat final, d'abord :** un personnage généré par ArtSmoker, exporté en FBX prêt pour moteur et ouvert dans un Blender standard — la chaîne de LOD (LOD0–LOD3) intacte dans l'Outliner, textures liées, sans re-rigging ni correction manuelle. Tout ce qui suit montre comment y parvenir à partir d'un prompt texte.

![FBX ArtSmoker ouvert dans Blender — hiérarchie du groupe LOD intacte avec textures liées](docs/images/fbx-in-blender.png)

**Le modèle généré — orbitez, inspectez, téléchargez :**

![Génération de modèle 3D — le maillage du soldat généré vu sous plusieurs angles dans la visionneuse 3D interactive](docs/images/3d-model-result.png)

Une seule image 2D de personnage (à gauche, dans l'onglet PNG) devient un maillage 3D entièrement texturé que vous pouvez faire pivoter librement dans le navigateur. L'onglet **3D Model** liste désormais aussi les **modèles et outils** exacts utilisés pour produire chaque asset (modèle de géométrie, backend de texturation, type de sortie, instance et paramètres de génération) — persistés dans les métadonnées de l'asset pour une traçabilité complète.

**Générer** — L'onglet 3D Model de l'Asset Viewer : choisissez l'endpoint du pipeline déployé, le niveau de qualité (avec temps et coût estimés) et les paramètres avancés. Le panneau de licence affiche les conditions de chaque pipeline, et **Improve the Source** vérifie visuellement l'image avant de consommer du temps GPU.

![Génération de modèle 3D — Paramètres et génération dans l'Asset Viewer](docs/images/3d-model-generation.png)

**Improve the Source** — Avant la génération, ArtSmoker mesure la silhouette du sujet et signale les recadrages (ici : coupé au bord inférieur), en suggérant les valeurs d'extension et un prompt d'outpainting écrit par l'IA — étendez, remplissez, ou utilisez l'image telle quelle.

![Vérification de la source 3D — détection automatique de recadrage avec extension suggérée](docs/images/3d-source-review.png)

**Deux pipelines — à vous de choisir.** ArtSmoker propose deux façons de transformer une image en modèle 3D texturé. Déployez l'un (ou les deux) depuis Custom Models ; lorsque les deux sont actifs, vous choisissez par génération dans l'Asset Viewer — chacun affiche son coût est., son temps et sa licence pour que vous décidiez en connaissance de cause :

| Pipeline | Fonctionnement | Licence | Usage commercial | Idéal pour |
|----------|----------------|---------|------------------|------------|
| **TripoSG + backend de texturation** | TripoSG construit le maillage ; un backend de texturation choisi (TRELLIS.2 / Hunyuan3D-Paint) le peint | selon le backend (ci-dessous) | selon le backend | Combiner géométrie + un texturateur précis |
| **TRELLIS.2 (Full)** | Un seul modèle génère **à la fois** la géométrie et la texture PBR (SLAT) | MIT | ✅ Oui — attribution « Built with DINOv3 » | Production, assets commerciaux, voie la plus simple |

**Variantes 3D** — Conservez plusieurs rendus 3D par version d'image (ici TripoSG contre le pipeline complet TRELLIS.2), basculez entre eux ou définissez le défaut à tout moment ; chaque variante enregistre les modèles et outils exacts qui l'ont produite.

![Variantes 3D — TripoSG et TRELLIS.2 côte à côte avec provenance complète](docs/images/3d-model-variants.png)

**Fonctionnement du pipeline TripoSG :**

1. **Extraction de géométrie** — un rectified flow transformer (TripoSG, 1,5 milliard de paramètres, sous licence MIT) convertit une seule image 2D en un maillage 3D haute fidélité à l'aide d'une représentation par champ de distance signée (SDF). La densité du maillage s'adapte au préréglage de qualité (jusqu'à ~1M de faces à la résolution d'octree la plus élevée) pour des détails nets sur les visages et l'équipement.
2. **Texturation** — le maillage est peint par un **backend de texturation que vous choisissez au moment du déploiement** (par défaut **TRELLIS.2**, Microsoft, MIT — un texturateur conditionné par SLAT/voxels produisant des matériaux PBR complets sur un atlas 4096²).
3. **Sortie PBR** — exporté en GLB avec des cartes PBR intégrées, prêt pour le rendu physiquement réaliste dans n'importe quel moteur moderne.

Le pipeline **TRELLIS.2 (Full)** fait la même chose de bout en bout dans un seul modèle — sans étape de texturation séparée.

**La licence bien en vue — au déploiement ET à la génération.** Chaque option déployable affiche son **détail complet de licence et de dépendances** dans la boîte de dialogue de déploiement — chaque modèle qu'elle télécharge, la licence de ce modèle, et s'il est exploitable commercialement ou restreint — et vous lisez et acceptez avant de déployer. Au moment de la génération, l'Asset Viewer rappelle la licence et confirme *« accepté au déploiement le `<date>` »* (sans second clic nécessaire) :

| Backend de texturation | Licence | Usage commercial | Idéal pour |
|------------------------|---------|------------------|------------|
| **TRELLIS.2** *(par défaut)* | MIT | ✅ Oui — nécessite une attribution « Built with DINOv3 » dans votre produit | Production, assets commerciaux, qualité maximale |
| **Hunyuan3D-Paint** | Tencent Community | ❌ Non commercial | Recherche / non commercial, visages exceptionnels |

La suppression d'arrière-plan (l'étape de détourage) utilise **BiRefNet (MIT)** par défaut — entièrement saine pour un usage commercial — avec une alternative non commerciale (RMBG) disponible en option déclarée. ArtSmoker ne télécharge jamais silencieusement une dépendance restreinte : tout ce qui est restreint ou non commercial est nommé, badgé et conditionné à une acceptation explicite.

**Sortie :** GLB standard avec textures PBR intégrées — s'importe directement dans Unity, Unreal Engine, Blender et d'autres moteurs de jeu. La visionneuse 3D interactive supporte l'orbite, le zoom et le panoramique pour une inspection immédiate, et l'onglet **3D Model** liste les modèles et outils exacts utilisés (modèle de géométrie, backend de texturation, dépendances, instance, paramètres) pour une traçabilité complète.

**Infrastructure :** Les deux pipelines se déploient via le même flux Custom Models en 1 clic, le sélecteur au moment du déploiement affichant pour chaque option sa licence, son tableau de dépendances, son instance de base et le coût/temps estimés. L'instance de base optimale du pipeline TRELLIS.2 complet est **`ml.g6e.xlarge`** (~$2,61/h ; pic mesuré ~6,5 Go de VRAM + ~22 Go de RAM hôte — c'est la RAM hôte qui constitue la contrainte limitante, pas le GPU). Les tailles `g6e` supérieures sont proposées comme montées en gamme offrant davantage de marge en RAM. Les endpoints se mettent à l'échelle à zéro en veille — $0 entre les tâches. Le premier démarrage à froid compile les extensions CUDA une seule fois (puis mises en cache sur S3 pour des redémarrages rapides). Avant de déployer un modèle à accès restreint, la boîte de dialogue **pré-vérifie l'accès HuggingFace pour chaque dépôt qu'il télécharge** et affiche un ✓/✗ par dépôt avec l'étape suivante exacte — vous ne découvrez ainsi jamais une acceptation de licence manquante plusieurs minutes après le début d'un démarrage à froid.

> **Visionner le GLB :** les textures sont encodées en WebP (`EXT_texture_webp`) pour garder des fichiers compacts — rendu parfait dans la visionneuse intégrée, Blender 4.x, three.js et les importateurs Unity/Unreal modernes. Preview/QuickLook de macOS ne prend pas en charge le WebP dans le glTF et affiche le modèle en noir ; utilisez la visionneuse intégrée ou tout outil glTF moderne.

| Métrique | Valeur |
|----------|--------|
| Qualité du maillage | Jusqu'à ~1M de faces, normales de sommets complètes |
| Résolution de texture | Atlas PBR 4096² (couleur de base + métallique-rugosité + alpha) |
| Licence | Exploitable commercialement par défaut (TRELLIS.2 MIT + BiRefNet MIT) ; backends non commerciaux proposés avec divulgation complète |
| Types d'assets supportés | Game Asset, Character |

### 📝 1.9.1 Exports prêts pour le moteur (GLB · FBX · USD)

![Visionneuse 3D avec outils par variante et options d'export FBX/USD prêtes pour moteur](docs/images/3d-model-viewer-export.png)

Chaque modèle 3D généré peut être exporté **préparé pour votre moteur de jeu**, directement depuis l'onglet 3D de l'Asset Viewer :

- **Moteur cible** — choisissez Generic (glTF, axe Y vers le haut), Unreal Engine (axe Z vers le haut), Unity, Godot, Maya ou 3ds Max. Les exports FBX et USD sont orientés avec les bons axes haut/avant pour ce moteur, si bien que les modèles s'importent droits — sans corrections de rotation manuelles.
- **Préparation optionnelle, à votre convenance** (chacune via un menu déroulant indépendant — rien n'est imposé) :
  - **Packing de textures** — jeux de textures par moteur : **ORM** Unreal (AO/Roughness/Metallic), **Metallic + Smoothness dans l'alpha** pour Unity, **HDRP Mask Map** pour Unity. Une fois sélectionné, l'export devient un ZIP contenant le modèle plus un dossier `textures/`.
  - **LODs** — une **chaîne LOD0–LOD3** décimée (100/50/20/5 %) avec un véritable groupe de LOD FBX qu'Unreal importe automatiquement ; le nommage `_LOD0…_LOD3` correspond aussi à la convention d'Unity.
  - **Collision** — une enveloppe convexe ou une **décomposition convexe CoACD**, nommée selon la convention du moteur (`UCX_*` pour l'import automatique d'Unreal, suffixes `-convcolonly` pour Godot).
  - **UV2 de lightmap** — un second canal UV, déplié par projection intelligente, pour l'éclairage précalculé.
- **Flux en deux étapes** — les boutons affichent **Generate FBX/USD/GLB** pour une combinaison qui n'existe pas encore ; un clic déclenche la conversion côté serveur (une ligne de statut vous tient informé — les gros modèles peuvent prendre une minute ou deux). Une fois généré, le bouton passe à **Download** avec un ✓ et livre instantanément. Chaque combinaison distincte est mise en cache — rien n'est jamais régénéré.
- **Pastilles « prêt à télécharger »** — l'onglet 3D liste toutes les combinaisons déjà générées pour la version courante, un clic pour retélécharger n'importe laquelle.
- **Le GLB original est sacré** — « Download GLB (original) » renvoie toujours la sortie intacte, identique à l'octet près, du pipeline de génération. Les exports traités (y compris un GLB traité avec LODs/collision intégrés) sont des fichiers nommés séparément à côté de lui.
- **Zéro installation** — les conversions s'exécutent côté serveur via un Blender headless géré : une installation existante est réutilisée si présente, sinon une copie portable se télécharge automatiquement à la première utilisation (voir l'onglet Model Settings → Maintenance pour la version et les mises à jour). Les utilisateurs finaux n'installent rien.

### 📝 1.9.2 À quoi s'attendre de la 3D générée par IA — Un guide honnête

L'image-to-3D est une technologie jeune, et il vaut la peine de savoir ce que les meilleurs modèles actuels (y compris ceux qu'exécute ArtSmoker) livrent réellement — et ce qu'ils ne livrent pas. La sortie est un **maillage dense de type objet scanné** : jusqu'à ~1M de triangles non structurés avec des textures PBR précalculées. De près, vous remarquerez une surface au grain irrégulier caractéristique, et les éléments fins (mèches de cheveux, sangles, franges de tissu) sont là où la géométrie IA est la plus faible. Il n'y a **ni topologie propre en quads, ni boucles d'arêtes adaptées à l'animation, ni rig** — c'est l'état de l'art dans toute l'industrie, pas une limitation propre à un outil en particulier.

**Là où ces assets excellent — et là où il faut un artiste :**

| Cas d'usage | Prêt à l'emploi ? |
|-------------|-------------------|
| Props, éléments de décor, habillage de scène | ✅ Oui — utilisable tel quel |
| Personnages d'arrière-plan / de moyenne distance, foules | ✅ Oui — à distance, le bruit de surface disparaît ; utilisez la chaîne de LOD |
| Prototypage, blockouts, préviz, démos de pitch | ✅ Oui — sans doute le cas d'usage le plus fort |
| Jeux mobiles / stylisés | ✅ Souvent — les LODs décimés aident |
| Personnages héros, gros plans, personnages animés | ⚠️ Un point de départ — prévoyez retopologie, nettoyage et rigging par un artiste |

Ce qu'ArtSmoker ajoute par-dessus le maillage brut, c'est que tout arrive **correctement empaqueté pour votre moteur** — bon axe vertical par cible, chaîne de LOD, proxys de collision, packing de textures spécifique au moteur — pour que le travail restant soit créatif, pas de la plomberie.

**Vous inspectez les exports dans Blender (ou un autre outil DCC) ? Deux choses paraîtront étranges — les deux sont normales :**

- **Généré avec des LODs ?** Le fichier contient **4 copies empilées** du modèle (LOD0–3). Vues ensemble, elles scintillent (z-fighting) et paraissent bruitées — masquez LOD1–3 dans l'Outliner et jugez la qualité sur LOD0 seul. Les moteurs de jeu n'affichent qu'un seul LOD à la fois, donc cela n'arrive jamais en moteur.
- **Généré avec collision ?** Une coque blanche et anguleuse de maillages `UCX_*` **enveloppe le modèle** — c'est le proxy physique, pas votre asset. Masquez ces objets pour voir le modèle texturé à l'intérieur. Les moteurs les importent automatiquement comme collision invisible.

### 📝 1.9.3 Utiliser un modèle commercialement — qui payer, et comment

Si la production d'un modèle vous plaît et que vous voulez l'utiliser commercialement, la marche à suivre dépend de **la façon dont son créateur monétise**. ArtSmoker affiche la licence de chaque modèle au moment du déploiement ; ceci est le guide compagnon « que faire ensuite ? ». *(Vérifié sur les sites des éditeurs et les fichiers de licence HuggingFace en août 2026 — les licences évoluent vite, confirmez donc toujours les conditions actuelles de l'éditeur. À titre informatif uniquement — voir la [clause de non-responsabilité](#disclaimer).)*

Les quatre schémas que vous rencontrerez :

1. **Déjà à vous (Apache-2.0 / MIT)** — l'usage commercial est inclus, gratuitement. Il n'y a aucun produit de licence à acheter ; le créateur monétise plutôt via sa propre API hébergée. Votre seule obligation est le respect des mentions et attributions.
2. **Gratuit jusqu'à ce que vous deveniez gros (licences communautaires)** — l'usage commercial est inclus **en dessous d'un seuil** (chiffre d'affaires ou utilisateurs actifs mensuels). Au-delà, la licence elle-même vous enjoint de demander un accord entreprise à l'éditeur — une conversation commerciale, pas une boutique.
3. **Acheter la licence, garder les poids** — les poids HuggingFace sont non commerciaux, mais le créateur vend séparément une **licence commerciale d'auto-hébergement**. Une fois que vous la détenez, les *mêmes poids que vous avez déjà déployés* deviennent légaux pour un usage commercial — rien ne change techniquement dans ArtSmoker.
4. **Le verrou est le péage** — le dépôt HuggingFace lui-même est à accès restreint (gated) ; un accord commercial avec l'éditeur débloque l'accès de votre compte HF. Le flux existant d'ArtSmoker — token HuggingFace + pré-vérification des dépôts restreints — fonctionne alors tel quel.

| Créateur / modèles | Schéma | Votre prochaine étape pour l'auto-hébergement commercial |
|---|---|---|
| **Alibaba** — Qwen-Image, Qwen-Image-Edit | 1 | Rien à acheter (Apache-2.0). Conservez les mentions de licence. |
| **Microsoft** — TRELLIS.2 · **VAST** — TripoSG | 1 | Rien à acheter (MIT). Remarque : les dépendances amont (p. ex. Meta DINOv3) portent leurs propres restrictions et conditions. |
| **Black Forest Labs** — FLUX.2 [klein] 4B | 1 | Rien à acheter — Apache-2.0, usage commercial libre. |
| **Stability AI** — SD 3.5 (auto-hébergé) | 2 | Gratuit, usage commercial inclus, sous **1 M$ de chiffre d'affaires annuel total** (l'acceptation du verrou HF *est* la licence). Au-delà, la licence **prend fin automatiquement** — demandez une licence Enterprise sur stability.ai/enterprise. **L'attribution « Powered by Stability AI » est obligatoire à tous les paliers.** |
| **Tencent** — HunyuanImage 3.0 / Hunyuan3D | 2 | Gratuit, usage commercial inclus sous le seuil — **attention, il est propre à chaque modèle** : HunyuanImage 3.0 = 100 M MAU ; **Hunyuan3D-2.1 = seulement 1 M MAU** (au-delà : écrivez à hunyuan3d@tencent.com). **Aucun droit accordé dans l'UE, au Royaume-Uni ni en Corée du Sud**, quelle que soit votre taille. |
| **Black Forest Labs** — FLUX.1/.2 [dev], Kontext | 3 | Achetez une **FLUX Commercial Weights License** (en libre-service sur dashboard.bfl.ai/licensing ; les paliers sont des abonnements plafonnés en volume d'images). Vous continuez d'utiliser les mêmes poids HF. Attention aux obligations : rapports d'utilisation, filtrage des sorties, **interdiction d'exposer le modèle comme API ou de le revendre** ; les nouvelles versions du modèle ne sont **pas** couvertes automatiquement hors Enterprise. |
| **Bria** — FIBO, RMBG-2.0 | 4 | Le verrou HF accorde immédiatement un accès **non commercial** ; l'auto-hébergement commercial exige un **accord payant avec Bria** (formulaire d'achat lié depuis chaque fiche de modèle / bria.ai). Il n'existe aucun seuil de gratuité commerciale. Une fois l'accès accordé, déployez via ArtSmoker exactement comme avant. |

**Comment cela s'articule avec ArtSmoker :** l'acquisition ne change presque jamais rien sur le plan technique. Pour les schémas 1–3, les poids que vous déployez sont identiques avant et après — ce qui change, c'est le contrat que vous détenez (conservez votre justificatif de licence ; le dialogue de déploiement d'ArtSmoker enregistre votre acceptation de la licence des *poids*, mais les accords commerciaux vous lient directement à l'éditeur). Pour le schéma 4, une fois que l'éditeur a approuvé votre compte HuggingFace, la vérification existante d'accès aux dépôts restreints d'ArtSmoker passe au vert et le déploiement se poursuit normalement. Quand un éditeur publie une nouvelle version d'un modèle, revérifiez si votre accord la couvre (celui de Stability oui, automatiquement ; celui de BFL généralement non hors Enterprise ; Tencent publie un nouveau texte de licence pour chaque version).

<a id="get-started"></a>

## 📌 2. Prérequis

- **Python 3.11+** (3.12, 3.13, 3.14 fonctionnent tous)
- **AWS CLI** configuré avec des identifiants valides
- **Permissions IAM** pour l'accès à Bedrock (voir ci-dessous)

### 📝 2.1 Identifiants AWS

ArtSmoker utilise la [résolution standard des identifiants boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials), donc toutes les méthodes suivantes fonctionnent :

| Méthode | Idéal pour | Comment |
|---------|-----------|---------|
| **Variables d'environnement** | CI/CD, conteneurs | `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` |
| **Fichier d'identifiants partagé** | Développement local | `~/.aws/credentials` via `aws configure` |
| **Profil nommé** | Comptes multiples | Définir `ARTSMOKER_AWS_PROFILE=myprofile` ou `AWS_PROFILE` |
| **AWS SSO** | SSO d'entreprise | `aws configure sso` |
| **IAM Instance Profile** | EC2, ECS, App Runner | Attacher un rôle IAM à l'instance — aucun identifiant nécessaire sur la machine |
| **ECS Task Role** | Conteneurs ECS/Fargate | Assigner un rôle d'exécution de tâche avec les permissions requises |

Vérification rapide que les identifiants fonctionnent :

```bash
aws sts get-caller-identity
```

> [!NOTE]
> Sur EC2 et les autres services de calcul AWS, vous n'avez pas besoin de configurer des identifiants explicites. Attachez un [IAM Instance Profile](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2_instance-profiles.html) avec les permissions requises, et boto3 le récupère automatiquement via le service de métadonnées de l'instance.

### 📝 2.1.1 Vérifier l'accès à Bedrock

Confirmer que les identifiants fonctionnent (`sts:GetCallerIdentity`) ne vérifie que l'identité — cela ne confirme pas que vous disposez des permissions Bedrock. ArtSmoker utilise plusieurs API Bedrock, donc un simple test de listing ne suffit pas. La vérification la plus fiable :

```bash
# Test 1: Can you list models? (requires bedrock:ListFoundationModels)
aws bedrock list-foundation-models --region us-east-1 --query "modelSummaries[0].modelId" --output text

# Test 2: Can you invoke an image model? (requires bedrock:InvokeModel)
aws bedrock-runtime invoke-model --region us-west-2 \
  --model-id stability.sd3-5-large-v1:0 \
  --content-type application/json --accept application/json \
  --body '{"prompt":"test","aspect_ratio":"1:1"}' \
  /dev/null 2>&1 && echo "InvokeModel: OK" || echo "InvokeModel: FAILED"

# Test 3: Can you use the Converse API? (authorizes via bedrock:InvokeModel)
# (Substitute any Claude model ID you have access to — e.g. the current Sonnet
#  inference profile from Test 1's list; the exact version rolls over time.)
aws bedrock-runtime converse --region us-west-2 \
  --model-id us.anthropic.claude-sonnet-5 \
  --messages '[{"role":"user","content":[{"text":"hi"}]}]' \
  --inference-config '{"maxTokens":1}' \
  --query "output.message.content[0].text" --output text 2>&1 && echo "Converse: OK" || echo "Converse: FAILED"

# Test 4: Can you list custom models? (requires bedrock:ListCustomModels)
aws bedrock list-custom-models --region us-east-1 \
  --query "modelSummaries[0].modelName" --output text 2>&1 && echo "ListCustomModels: OK" || echo "ListCustomModels: no custom models (or permission denied)"
```

Si les tests 1 à 3 réussissent, vos permissions de base sont en place. Le test 4 n'est nécessaire que pour la découverte des modèles personnalisés. Si le test 1 réussit mais que les tests 2-3 échouent, votre politique IAM autorise le listing mais pas l'invocation — mettez-la à jour à l'aide du tableau de permissions ci-dessous.

### 📝 2.2 Permissions IAM

Votre utilisateur IAM, votre rôle ou votre instance profile a besoin de ces permissions :

| Permission | Utilisée pour |
|------------|---------------|
| `bedrock:InvokeModel` | Génération d'images, édition d'images, post-traitement (tous les modèles d'image) |
| `bedrock:InvokeModelWithResponseStream` | Réponses LLM en streaming (Chat Studio) — l'API ConverseStream s'autorise via cette action. L'API Converse non-streaming (affinage de prompts, analyse de style, génération de concepts) s'autorise via `bedrock:InvokeModel` — il n'existe pas d'action `bedrock:Converse` distincte |
| `bedrock:InvokeModelWithBidirectionalStream` | Transcription vocale (optionnel — l'app fonctionne sans) |
| `bedrock:StartAsyncInvoke` | Génération vidéo (invocation asynchrone) |
| `bedrock:GetAsyncInvoke` | Interroger le statut des jobs de génération vidéo |
| `bedrock:ListAsyncInvokes` | Lister les jobs de génération vidéo |
| `bedrock:ListFoundationModels` | Découverte des modèles de fondation (Sync from AWS) |
| `bedrock:ListCustomModels` | Découverte des modèles personnalisés fine-tunés de votre compte |
| `bedrock:ListImportedModels` | Découverte des modèles importés de votre compte |
| `bedrock:GetCustomModel` | Lire les détails d'un modèle personnalisé (modèle de base, statut) |
| `bedrock:GetImportedModel` | Lire les détails d'un modèle importé (architecture, statut) |
| `bedrock:ListProvisionedModelThroughputs` | Trouver les modèles personnalisés invocables avec throughput provisionné |
| `bedrock:ListCustomModelDeployments` | Trouver les modèles personnalisés avec déploiements on-demand |
| `bedrock:CreateInference` *(ou la politique `AmazonBedrockMantleInferenceAccess`)* | **Amazon Bedrock Mantle** — modèles de pointe accessibles uniquement via l'endpoint Mantle (OpenAI GPT‑5.x, Claude Mythos, GLM, Grok, Qwen, Gemma…). Son absence n'affecte que ces modèles ; Claude via Converse continue de fonctionner. |
| `account:ListRegions` | Scanner uniquement les régions **activées** de votre compte pendant le Sync (rapide, pas d'erreurs sur les régions opt‑in). Optionnel — se rabat sur le scan de toutes les régions. |
| `account:GetRegionOptStatus` | Lire le statut opt‑in par région (complément de `account:ListRegions`). Optionnel. |
| `s3:CreateBucket` | Créer un bucket S3 pour le stockage vidéo (optionnel, via l'UI) |
| `s3:PutObject` / `s3:GetObject` / `s3:DeleteObject` / `s3:ListBucket` | Stockage et récupération des sorties vidéo |
| `aws-marketplace:Subscribe` | Auto-abonnement à la première utilisation de modèles tiers (y compris les modèles Mantle tiers) |
| `aws-marketplace:ViewSubscriptions` | Vérifier les abonnements aux modèles existants |
| `sts:GetCallerIdentity` | Validation des identifiants au démarrage ; sous-tend également le jeton porteur Mantle signé localement |
| `pricing:GetProducts` | Récupérer les tarifs des modèles pendant le Sync from AWS (optionnel) |
| `sagemaker:*` | Modèles personnalisés auto-hébergés sur Amazon SageMaker (optionnel — uniquement si vous utilisez les Custom Models) |
| Suite runtime des Custom Models : `application-autoscaling:*` (cibles/politiques), `cloudwatch:PutMetricAlarm`/`DeleteAlarms`/`DescribeAlarms`, `logs:` (lecture + rétention), `servicequotas:GetServiceQuota`/`RequestServiceQuotaIncrease`, `ecr:DescribeRepositories`, `iam:CreateServiceLinkedRole` (première mise à l'échelle automatique uniquement) | Mise à l'échelle des endpoints vers/depuis zéro, alarme de backlog, scan de disponibilité, vérification des quotas GPU, résolution de l'image DLC (optionnel — Custom Models uniquement ; liste complète dans la politique ciblée ci-dessous) |
| `iam:PassRole` | Autoriser Amazon SageMaker à utiliser votre rôle (optionnel — uniquement pour les Custom Models) |
| `iam:CreateRole` / `iam:AttachRolePolicy` | Auto-création du rôle d'exécution Amazon SageMaker au premier déploiement (optionnel — uniquement pour les Custom Models) |
| `iam:GetRole` / `iam:UpdateAssumeRolePolicy` | Auto-configuration d'un rôle existant pour la relation de confiance Amazon SageMaker (optionnel) |
| `secretsmanager:CreateSecret` / `secretsmanager:GetSecretValue` / `secretsmanager:DeleteSecret` | Stockage chiffré des jetons HuggingFace pour les modèles à accès restreint (optionnel — nettoyé automatiquement au teardown) |

**Configuration la plus rapide** (politiques managées — accès le plus large) :

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

**Configuration à portée restreinte** (permissions plus strictes — recommandée pour la production) :

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

# Attach to your IAM user (replace YOUR_ACCOUNT_ID and YOUR_USERNAME)
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/ArtSmokerAccess
```

> [!NOTE]
> **Deux points à ajuster pour votre compte :** (1) La déclaration S3 est limitée aux buckets nommés `artsmoker-*` — si vous pointez ArtSmoker vers un bucket portant un autre nom (Video Settings permet de choisir n'importe quel bucket existant), élargissez ce `Resource` à l'ARN de votre bucket. (2) Les ressources SageMaker créées par ArtSmoker sont nommées `artsmoker-*`, donc le `Resource` ciblé fonctionne tel quel ; les actions `sagemaker:List*` ne prennent pas en charge le ciblage par ressource et figurent dans une déclaration séparée.
>
> **Une permission manque à l'exécution ?** ArtSmoker surveille chaque appel AWS : si un appel est refusé, il journalise le `service:Operation` exact qui a échoué et affiche une notification persistante dans l'application nommant l'action à ajouter — un manque de permission n'échoue jamais en silence.

> [!TIP]
> **Pour EC2/ECS/App Runner** — créez un rôle IAM au lieu de l'attacher à un utilisateur. Consultez la section [Déploiement EC2](#43-ec2--cloud-deployment) pour les commandes complètes de création de rôle. Aucune clé d'accès nécessaire — boto3 découvre automatiquement le rôle via le service de métadonnées de l'instance.

> [!NOTE]
> Les modèles Bedrock sont disponibles par défaut dans toutes les régions commerciales AWS — aucune étape d'activation manuelle n'est nécessaire. À la première invocation d'un modèle tiers (Anthropic, Stability AI), AWS initie automatiquement un abonnement marketplace en arrière-plan (nécessite les permissions `aws-marketplace` ci-dessus). Les modèles Anthropic nécessitent de remplir une seule fois le [First Time Use form](https://console.aws.amazon.com/bedrock/home#/modelaccess).

### 📝 2.3 Optionnel : outils de conversion SVG

La conversion SVG utilise des outils CLI externes (pas des paquets Python). Sans eux, la sortie SVG se rabat sur un wrapper raster-dans-SVG basé sur Pillow — fonctionnel mais ce n'est pas une véritable sortie vectorielle.

| Outil | But | macOS | Linux (Debian/Ubuntu) | Windows |
|-------|-----|-------|-----------------------|---------|
| **vtracer** | SVG principal (vectorisation couleur) | `pip install vtracer` ou `cargo install vtracer` | `pip install vtracer` ou `cargo install vtracer` | `pip install vtracer` ou `cargo install vtracer` ou [pre-built binaries](https://github.com/visioncortex/vtracer/releases) |
| **potrace** | SVG de secours (vectorisation monochrome) | `brew install potrace` | `sudo apt install potrace` | Télécharger depuis [potrace.sourceforge.net](http://potrace.sourceforge.net/#downloading) |

Vérifier l'installation :

```bash
# Check SVG conversion tools
which vtracer && echo "vtracer: OK" || echo "vtracer: not installed (optional)"
which potrace && echo "potrace: OK" || echo "potrace: not installed (optional)"
```

### 📝 2.4 Optionnel : outils de vignettes et métadonnées vidéo

Video Studio génère des vidéos MP4 via Amazon Nova Reel et Luma AI Ray. Pour extraire les vignettes (première frame en JPEG) et les métadonnées vidéo (durée, résolution, FPS), **ffmpeg** et **ffprobe** doivent être installés sur la machine qui exécute le backend ArtSmoker.

Sans ffmpeg :
- Les vidéos se génèrent et se lisent toujours correctement (streamées depuis S3 ou téléchargées en MP4)
- Les vignettes seront manquantes — la Galerie et le Video Studio affichent un placeholder noir au lieu d'une image d'aperçu
- Les métadonnées vidéo (durée, résolution) ne s'afficheront pas

| Outil | But | macOS | Linux (Debian/Ubuntu) | Windows |
|-------|-----|-------|-----------------------|---------|
| **ffmpeg** | Extraction de vignettes + métadonnées vidéo | `brew install ffmpeg` | `sudo apt install ffmpeg` | Télécharger depuis [ffmpeg.org/download](https://ffmpeg.org/download.html) ou `winget install ffmpeg` |

> [!NOTE]
> `ffprobe` est inclus avec ffmpeg — aucune installation séparée nécessaire. ArtSmoker vérifie la présence de ffmpeg au runtime et se rabat proprement s'il est introuvable — la génération vidéo fonctionne dans tous les cas, vous n'aurez simplement pas de vignettes.

Vérifier l'installation :

```bash
ffmpeg -version 2>&1 | head -1 && echo "ffmpeg: OK" || echo "ffmpeg: not installed (optional)"
ffprobe -version 2>&1 | head -1 && echo "ffprobe: OK" || echo "ffprobe: not installed (optional)"
```

## 📌 3. Installation

### 📝 3.1 macOS

```bash
git clone https://github.com/niravdd/ArtSmoker.git && cd ArtSmoker

# Option A: With virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Option B: Without virtual environment (system-wide install)
pip3 install -r backend/requirements.txt
```

> [!NOTE]
> Sur macOS, `python3` et `pip3` sont disponibles via Homebrew (`brew install python`) ou les Xcode command-line tools. Si vous voyez « command not found », installez Python depuis [python.org](https://www.python.org/downloads/) ou via `brew install python@3.12`.

### 📝 3.2 Linux (Debian/Ubuntu)

```bash
# Install Python if needed
sudo apt update && sudo apt install python3 python3-pip python3-venv

git clone https://github.com/niravdd/ArtSmoker.git && cd ArtSmoker

# Option A: With virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Option B: Without virtual environment
pip3 install --user -r backend/requirements.txt
```

> [!NOTE]
> Sur certaines distributions Linux, `pip install` en dehors d'un venv nécessite le flag `--user` ou `--break-system-packages` (PEP 668). Utiliser un venv évite entièrement ce problème.

### 📝 3.3 Windows

```powershell
git clone https://github.com/niravdd/ArtSmoker.git
cd ArtSmoker

# Option A: With virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt

# Option B: Without virtual environment
pip install -r backend\requirements.txt
```

> [!NOTE]
> Sur Windows, utilisez `python` (pas `python3`). Installez Python depuis [python.org](https://www.python.org/downloads/) — cochez « Add to PATH » pendant l'installation. Le sélecteur de polices de Type Studio détecte les polices depuis `C:\Windows\Fonts` (la détection des polices système n'est actuellement disponible que sur macOS/Linux — les utilisateurs Windows peuvent utiliser des polices personnalisées globales ou spécifiques au style).

## 📌 4. Exécution

### 📝 4.1 Développement solo (toutes plateformes)

Processus unique avec rechargement automatique à chaque modification de fichier — idéal pour un seul développeur travaillant localement :

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

Ouvrez **http://localhost:8000** — le frontend est servi par FastAPI, aucun serveur web séparé n'est nécessaire.

Au démarrage, la console affiche les résultats de la validation des identifiants AWS. Si quelque chose ne va pas, vous verrez une boîte d'erreur claire. Vous pouvez aussi consulter `http://localhost:8000/api/health` pour le statut.

**Logs.** En plus de la console, ArtSmoker écrit un journal complet en **ajout seul** (append-only) dans `logs/artsmoker.log` **par défaut**, afin que vous puissiez revoir une session passée après la fermeture de l'application. Chaque exécution est encadrée par une bannière de session (heure de lancement, version, pid, hôte) et clôturée par une bannière d'arrêt (heure d'arrêt, durée). Pour changer le chemin ou le désactiver :

```bash
ARTSMOKER_LOG_FILE=/var/log/artsmoker/app.log uvicorn backend.main:app   # custom path
ARTSMOKER_LOG_TO_FILE=false uvicorn backend.main:app                      # disable file logging
```

(Ou définissez `log_to_file` / `log_file` dans un `.env` local. Avec plusieurs workers, chaque worker ajoute au même fichier.)

### 📝 4.2 Multi-utilisateur / machine de test partagée / production (macOS / Linux)

Pour tout environnement avec plus d'un utilisateur simultané — qu'il s'agisse d'une machine de dev/test partagée, d'un staging ou d'une production — utilisez **gunicorn** avec plusieurs workers :

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

| Flag | But |
|------|-----|
| `-w 2` | 2 processus workers (augmentez pour une charge plus lourde) |
| `-k uvicorn.workers.UvicornWorker` | Utiliser la classe de worker asynchrone d'uvicorn |
| `--bind 0.0.0.0:8000` | Écouter sur toutes les interfaces (pas seulement localhost) |
| `--timeout 300` | Timeout de 5 minutes pour les grosses générations par lots avec réessais |

> [!TIP]
> **gunicorn** est réservé à Linux/macOS. Sur Windows, utilisez `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2` pour un service multi-worker.

> [!NOTE]
> **Sûr pour les utilisateurs simultanés.** Toutes les écritures serveur — les métadonnées d'images/versions et les registres de modèles et de prompts — sont écrites de manière atomique et sérialisées **entre les processus workers** (verrous de fichiers POSIX), de sorte que des modifications simultanées de plusieurs collaborateurs sur une machine partagée ne corrompent jamais un fichier ni ne perdent une mise à jour. La journalisation dans un fichier fonctionne de la même manière entre les workers — chacun ajoute au même `logs/artsmoker.log`.

<a id="43-ec2--cloud-deployment"></a>

### 📝 4.3 Déploiement EC2 / Cloud

Recommandé : **t3.small** (~$15/mois) pour 1-2 utilisateurs simultanés.

**Étape 1 : Créer un rôle IAM pour l'instance EC2** (à exécuter depuis votre machine locale) :

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

**Étape 2 : Lancer une instance EC2** (ou attacher le profil à une instance existante) :

```bash
# Attach to an existing running instance
aws ec2 associate-iam-instance-profile \
  --instance-id i-YOUR_INSTANCE_ID \
  --iam-instance-profile Name=ArtSmokerEC2Profile
```

**Étape 3 : Installer et exécuter sur l'instance** (SSH sur l'instance) :

```bash
# Install (one-time)
sudo yum install -y python3 python3-pip git   # Amazon Linux
# sudo apt install -y python3 python3-pip python3-venv git   # Ubuntu

git clone https://github.com/niravdd/ArtSmoker.git && cd ArtSmoker
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install gunicorn

# Optional: install ffmpeg for video thumbnails
sudo yum install -y ffmpeg   # Amazon Linux
# sudo apt install -y ffmpeg   # Ubuntu
```

**Étape 4 : Exécuter comme service systemd** (persistant, redémarrage automatique) :

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

Ouvrez **http://YOUR_INSTANCE_IP:8000** — assurez-vous que votre security group EC2 autorise le trafic TCP entrant sur le port 8000.

### 📝 4.4 Premières étapes après l'installation

Une fois ArtSmoker en cours d'exécution, effectuez ces étapes pour obtenir les meilleurs résultats :

**1. Synchroniser les modèles depuis AWS** — Ouvrez **Model Settings** (icône engrenage dans n'importe quel studio) → cliquez sur **Sync from AWS**. Cela découvre tous les modèles d'image, vidéo et chat disponibles dans toutes les régions Bedrock. Prend 30-60 secondes. Nécessaire une seule fois, ou lorsqu'AWS ajoute de nouveaux modèles.

**2. Passer en revue et personnaliser les prompt templates** — C'est la configuration la plus impactante que vous puissiez faire. Ouvrez l'onglet **Model Settings → Prompt Templates**. ArtSmoker utilise 28 prompts directifs éditables qui contrôlent le comportement de l'IA :

| Template | Ce qu'il contrôle |
|----------|-------------------|
| Image Prompt Refinement | Comment vos descriptions textuelles sont transformées en prompts de génération d'images détaillés |
| Multi-Concept Generation | Comment plusieurs options créatives sont générées à partir d'une seule idée |
| Style Analysis | Comment les images de référence sont analysées pour apprendre votre style artistique |
| Content Moderation | À quel point le système de pré-vérification et de réécriture est strict |
| Video Enhancement | Comment les prompts vidéo sont enrichis de mouvements de caméra et d'éclairage |
| Text Layout | Comment Type Studio conçoit le positionnement du texte sur les images |

Chaque template peut être :
- **Édité directement** — modifiez les instructions pour correspondre aux besoins de votre équipe
- **Amélioré avec l'IA** — sélectionnez n'importe quel modèle LLM, ajoutez éventuellement des instructions (par ex. « optimize for pixel art »), et cliquez sur « Enhance with AI ». Examinez la suggestion, puis acceptez ou rejetez
- **Réinitialisé par défaut** — restaurez l'original à tout moment

Les templates sont organisés par studio (Image Studio, Style Library, Content Safety, Video Studio, Type Studio, Chat Studio, Translation) avec des descriptions conviviales de ce que chacun contrôle.

**Sécurité des variables :** Les templates utilisent des variables `{curly_brace}` (par ex. `{user_prompt}`, `{model_name}`) qui sont substituées au runtime. Si vous supprimez accidentellement une variable requise, ArtSmoker va :
1. Bloquer la sauvegarde et indiquer quelles variables manquent
2. Proposer **« Fix & Save »** — un LLM réinsère automatiquement les variables manquantes aux bons endroits de votre texte édité
3. Vérifier la correction avant de sauvegarder

Les templates se chargent depuis `backend/prompt_templates.json` — la source de vérité au runtime. Vos modifications sont enregistrées dans `backend/prompt_templates.user.json` (gitignored) et superposées par-dessus, de sorte qu'une mise à jour ou un `git pull` n'écrase jamais vos personnalisations. Si le JSON est manquant ou corrompu, ou qu'un nouveau template arrive dans le code, il s'auto-répare : la semence de code intégrée régénère/complète uniquement les entrées manquantes, sans jamais écraser les existantes.

> [!TIP]
> Commencez par examiner les templates **Image Prompt Refinement** et **Creative Options**. Ce sont ceux qui ont le plus d'impact sur la qualité de sortie. Si votre équipe est spécialisée dans un style artistique particulier (par ex. pixel art, aquarelle, isométrique), ajoutez ces préférences directement dans les templates pour que chaque génération en bénéficie.

**3. Configurer un profil de style** (optionnel) — Allez dans **Style Library**, créez un nouveau style, téléchargez des images de référence, et cliquez sur **Analyze**. Cela apprend à ArtSmoker votre identité visuelle.

**4. Choisir votre langue** — Cliquez sur un bouton de langue dans la barre de navigation (EN | 日 | 中 | 한 | हिं | РУ | FR | ES | DE) si vous préférez une interface non anglaise.

## 📌 5. Architecture

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

## 📌 6. Utilisation

### 📝 6.1 Aperçu du workflow

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

**Trois points d'entrée, une galerie unifiée :**

- **Commencer par un style** — téléchargez de l'art de référence dans la Style Library, laissez l'IA l'analyser, puis générez dans n'importe quel studio. Le style guide toutes les sorties.
- **Commencer sans style** — allez directement dans le 2D Image Studio, le Video Studio ou le Type Studio. L'IA use de son meilleur jugement.
- **Commencer depuis la Galerie** — choisissez n'importe quel asset précédemment généré et rechargez-le dans le studio approprié pour l'affiner, ajoutez-y du texte, lisez une vidéo, ou téléchargez en PNG/SVG/MP4.

Tous les assets générés (images, vidéos, superpositions de texte, texte autonome) atterrissent dans la Galerie unifiée. Rien n'est écrasé — chaque génération crée de nouveaux assets.

### 📝 6.2 Pipeline de génération

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

### 📝 6.3 Flux de modération de contenu

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

### 📝 6.4 2D Image Studio (générer des assets)

Le 2D Image Studio utilise un workflow guidé en 3 étapes :

**Étape 1 — Décrivez votre idée** : Saisissez un prompt dans la zone de texte. Le placeholder montre un exemple réaliste qui change selon le type d'asset sélectionné (par ex. « A young female warrior in ornate silver armor... » pour Character, ou « A misty Japanese garden at dawn... » pour Environment). Utilisez l'entrée vocale (bouton micro) pour dicter au lieu de taper.

**Étape 2 — Prompt Designer** *(optionnel)* : Cliquez sur **🎨 Prompt Designer** pour décomposer votre prompt en composants visuels structurés. L'IA analyse votre prompt et le décompose en sections éditables :

- **Subject** — description du personnage, vêtements, accessoires, pose, expression
- **Scene** — décor, arrière-plan, accessoires, moment de la journée
- **Composition** — angle de caméra, cadrage, profondeur de champ
- **Lighting** — lumière principale, lumière d'appoint/de contour, ambiance
- **Style & Colors** — style artistique, niveau de qualité, et une palette de couleurs nommée avec échantillons hexadécimaux

Chaque champ peut être édité individuellement. **Generate Enhanced Prompt** recompose vos modifications en un prompt recomposé à plat (affiché en lecture seule à l'Étape 2) puis génère automatiquement l'Enhanced AI Prompt pour l'Étape 3.

Avant l'ouverture du Prompt Designer, une **classification IA du type d'asset** s'exécute — si votre prompt décrit une scène mais que vous avez sélectionné « Game Asset », une boîte de dialogue suggère de basculer vers « Environment » ou « Character ». Cela garantit que le Prompt Designer décompose avec le bon contexte.

**Étape 3 — Aperçu du prompt amélioré** *(optionnel)* : Cliquez sur **Generate Enhanced Prompt** pour voir le prompt optimisé pour le modèle avant de générer. L'IA prend le prompt recomposé de l'Étape 2 et l'enrichit avec une guidance spécifique au modèle (anatomie, matériaux, éclairage, structure de prompt). Vous pouvez éditer le prompt amélioré avant de générer. Si vous avez utilisé le Prompt Designer à l'Étape 2, celui-ci est pré-rempli automatiquement.

**Pipeline de prompt** : Prompt utilisateur → Decompose → Recompose (`recomposed_prompt`) → Enhance avec guidance modèle (`enhanced_prompt`) → Modèle d'image. Pour des options multiples, l'étape d'amélioration génère N interprétations distinctes à partir de la même base recomposée. Les trois niveaux sont stockés dans les métadonnées.

**Générer** : Cliquez sur Generate à tout moment — les étapes 2 et 3 sont optionnelles. Si vous les sautez, Generate décompose, recompose et améliore automatiquement votre prompt avant de continuer. **Prompt Pre-Check** (activé par défaut) analyse le prompt pour détecter les problèmes de modération avant la génération.

**Contrôles additionnels :**
- **Asset Type** — à sélectionner dans la barre latérale. Change le placeholder du prompt et affecte la façon dont l'IA interprète votre prompt. Le système suggère de basculer s'il détecte une incohérence.
- **Art Style** — sélectionnez un profil de style pour guider la génération avec votre identité visuelle.
- **Dimensions, Options, Variations** — configurez la taille de sortie et le nombre de concepts créatifs à générer.
- **Post-Processing** — Remove Background, Upscale, conversion SVG (appliqués après la génération).
- **IP Declaration** — affirmez la propriété ou la licence pour la compatibilité avec les modèles stricts.
- **Model Settings** — consultez/modifiez la configuration des modèles, découvrez les modèles Amazon Bedrock disponibles.

La progression de la génération est streamée en temps réel via SSE — l'UI affiche quelle image est en cours de génération (par ex. « Generating images... 12/25 »), le temps écoulé et l'étape actuelle du pipeline. Si l'API est limitée (throttled), vous verrez « API throttled — waiting to retry... » avec le délai, puis « Retrying... (attempt 2/3) » — chaque image réessaie jusqu'à 3 fois avec un backoff exponentiel afin que les gros lots ne perdent pas de variantes à cause d'une limitation transitoire.

Les résultats générés survivent à la navigation — passer d'un onglet à l'autre et revenir préserve l'état DOM du 2D Image Studio. Seul le bouton de réinitialisation l'efface.

**Modération de contenu intelligente** : Lorsque votre prompt est bloqué par les filtres de modération d'un modèle, ArtSmoker le gère progressivement via trois boîtes de dialogue à code couleur :

- **Indigo (Pre-Check)** — avant la génération, une IA pré-analyse votre prompt selon la sensibilité connue du modèle sélectionné. Si des problèmes sont détectés, vous voyez les préoccupations spécifiques et pouvez : basculer vers un modèle recommandé, **réécrire le prompt** pour le modèle actuel, procéder quand même, ou annuler.
- **Emerald (Model Switch)** — après un blocage de génération, si un modèle alternatif accepte votre prompt tel quel, ArtSmoker indique quel modèle fonctionne et pourquoi. Un clic pour basculer. Journal complet des tentatives disponible (« View N model tests »).
- **Amber (Rewrite)** — quand tous les modèles refusent, une réécriture générée par l'IA est proposée dans une zone de texte éditable avec les problèmes spécifiques listés. Un badge vérifié/non vérifié indique si la réécriture a passé le test canari.

**Comportement de réécriture du prompt** : Dans les trois dialogues, choisir « Rewrite » n'écrase jamais votre prompt original. La version réécrite apparaît dans la **zone du prompt amélioré** sous votre texte original, avec un avertissement ambre persistant : *« This rewrite is an attempt to make the prompt compatible — it is still subject to the model's own moderation assessment and may be rejected. »* Vous examinez et éditez le prompt amélioré, puis cliquez sur Generate quand vous êtes satisfait. Votre prompt original est toujours préservé dans l'historique et les métadonnées.

Les déclencheurs courants incluent les noms d'IP protégés et les références de personnages, le langage de violence/armes, et les références à du contenu adulte. Astuce : le bouton **« Preview Enhanced Prompt »** produit souvent des prompts qui passent naturellement la modération, car l'IA reformule en termes descriptifs.

**Test canari intelligent** : Avant de générer le lot complet, ArtSmoker envoie une seule requête d'image « canari » pour tester le prompt contre les filtres de modération du modèle. Si le canari est bloqué, le lot s'arrête immédiatement (1 appel API gaspillé au lieu de N×M×3). Si le canari passe, les tâches restantes s'exécutent en parallèle avec annulation coopérative — si une tâche rencontre un blocage de modération, les autres sautent automatiquement leurs appels API.

### 📝 6.5 Utiliser un profil de style

1. Allez dans l'onglet **Style Library**.
2. Cliquez sur **Create New Style** — entrez un nom et ajoutez éventuellement des indications de génération. Dans la modale de création, utilisez la section **« Import References From »** avec les boutons de navigation **Local** et **S3** pour sélectionner un répertoire source ou un chemin de bucket. La navigation ouvre une modale d'explorateur de fichiers/répertoires côté serveur (un clic sélectionne un élément, un double-clic navigue dans les répertoires). Les références importées sont auto-analysées à la création.
3. Les imports de répertoires locaux scannent **récursivement** à travers tous les sous-répertoires pour les images (.png, .jpg, .jpeg, .gif, .bmp, .webp, .tiff, .tif, .tga, .ico, .svg) et les modèles 3D (.glb, .gltf). Les fichiers image sont **symlinkés** à l'aide de **liens symboliques relatifs** (pas de duplication, portables entre machines). Les fichiers de modèles 3D (.glb/.gltf) ont leurs textures intégrées **automatiquement extraites** — data URIs base64, chunks de buffer binaire et références de textures externes sont tous gérés. Les textures extraites sont enregistrées comme copies (préfixées du nom du modèle pour éviter les collisions). Les imports S3 listent récursivement avec pagination et **téléchargent** les fichiers localement. Jusqu'à **100 images de référence** sont importées par style. Les extensions supportées sont centralisées dans `backend/config.py` (`IMAGE_EXTENSIONS` et `MODEL_EXTENSIONS_WITH_TEXTURES`).
4. **Analyse en deux phases avec détection de cohésion** : La phase 1 envoie 8 images à Claude Sonnet pour déterminer le niveau de cohésion (élevé/moyen/faible) — élevé signifie un style unifié, moyen signifie une structure partagée avec des thèmes différents, faible signifie des styles divers. La phase 2 transmet l'évaluation de cohésion à Claude Opus avec les images de référence, le guidant pour analyser de manière appropriée selon le type de collection. Lorsqu'un style a plus de 20 références, l'analyseur sélectionne un sous-ensemble représentatif diversifié de 20 pour l'appel de vision Opus — garantissant une couverture entre les groupes de noms de fichiers et la diversité des tailles de fichiers. L'IA est informée du nombre total d'images qui existent par rapport à celles qu'elle voit. Le prompt d'analyse est spécifiquement conçu pour les assets de jeux sur fonds transparents — il demande des détails de rendu spécifiques aux matériaux, un système de proportions et des spécificités d'ombre/éclairage. Il extrait 9 attributs de style dont `materials` (comment la pierre, le bois, le métal sont rendus) et `detail_level` (quels détails de surface sont visibles vs simplifiés). Les indications de génération sont étendues à 200 mots couvrant 8 dimensions : perspective, rendu, matériaux, palette de couleurs, proportions, traitement des bords, ombre/éclairage, niveau de détail et arrière-plan — suffisamment spécifiques pour que les assets générés se fondent visuellement avec les références existantes.
5. Dans la vue de détail du style, utilisez **« Import & Analyze »** pour ajouter plus de références et déclencher l'analyse en une seule étape. Le téléchargement par glisser-déposer est aussi supporté et **relance automatiquement l'analyse** lorsque de nouvelles images sont ajoutées.
6. **« Re-Analyze Style »** apparaît après l'analyse initiale, vous permettant de relancer manuellement l'analyse à tout moment.
7. **Les indications de génération** font partie du contexte d'analyse — l'IA reçoit à la fois les images de référence et vos indications comme « Artist's Guidance » lors de l'analyse, afin que le profil de style comprenne l'intention, pas seulement l'apparence visuelle. Modifier les indications de génération déclenche aussi une **réanalyse automatique**.
8. De retour dans le **2D Image Studio**, sélectionnez votre style dans le menu déroulant — tous les assets générés correspondront à son identité visuelle (palette, perspective, style de rendu, ambiance).

### 📝 6.6 Flux d'analyse de style

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

Ajoutez du texte aux images ou générez des assets de texte autonomes avec une typographie conçue par l'IA.

- **Deux modes** : « On Image » composite le texte sur une image de la galerie ; « Standalone » rend le texte sur un fond transparent.
- **Éditeur de texte multi-lignes** avec sélection de police par ligne, contrôles de positionnement, et **entrée vocale** (bouton micro par ligne — dictez le texte via la transcription Nova Sonic).
- **Mises en page conçues par l'IA** — l'IA suggère les couleurs, tailles, positions et effets (ombre, contour, lueur). Demandez 1 à 5 options de mise en page pour différentes directions créatives. Le **modèle LLM** utilisé pour la mise en page est configurable (Complex LLM pour la meilleure qualité, Fast LLM pour moins cher) — lit depuis les catégories du registre.
- **Sélecteur de polices avec aperçu en direct** — polices de style, 8 polices intégrées (Roboto, Open Sans, Lato, Montserrat, Playfair Display, Oswald, Raleway, Source Code Pro), polices système, et **polices détectées côté client** (via la Local Font Access API ou le sondage canvas).
- **Pré-traitement / Post-traitement** — même workflow que le 2D Image Studio, avec un bouton « Apply » pour le post-traitement. La conversion SVG est activée par défaut.
- **Cliquer pour zoomer** — cliquer sur l'aperçu du résultat ouvre l'AssetViewer avec zoom/panoramique complet, métadonnées, téléchargement et outils d'édition d'image.
- Les résultats sont enregistrés comme de nouveaux assets de la galerie (les originaux ne sont jamais écrasés).

### 📝 6.8 Galerie

- **Vue unifiée** de toutes les images et vidéos générées dans une **disposition en maçonnerie (masonry)** (chaque asset affiché à son véritable ratio — portrait, carré ou paysage — jamais recadré au centre), avec un **filtre Média** (All / 2D Artwork / 3D Models / Video). Le filtre **3D Models** n'affiche que les assets qui possèdent déjà un modèle 3D généré, et ces assets portent un **badge 3D** sur leur tuile.
- **Barre de recherche** pour un filtrage instantané sur tous les assets (prompts, styles, modèles).
- **Multi-sélection** par cases à cocher pour la suppression en masse (gère à la fois les assets image et vidéo). Les suppressions sont **conscientes du lot** — les frères et sœurs survivants suivent combien de variantes ont été retirées, de sorte que recharger un lot partiel dans l'Image Studio affiche « X of Y images remaining (Z deleted) ».
- Les assets se chargent immédiatement avec un cache de métadonnées en mémoire. Triés du plus récent au plus ancien.
- Support de la pagination (limit/offset) pour les grandes collections.
- La Galerie se rafraîchit automatiquement lorsque vous y revenez, et après toute édition ou génération vidéo terminée.
- **Les cartes vidéo** affichent une vignette avec une superposition de lecture, un badge VIDEO et un indicateur de durée. Cliquez pour ouvrir la modale du lecteur vidéo.
- **Boutons d'action contextuels** par asset selon le type : **« 2D Studio »** (indigo) pour recharger dans l'image studio, **« Add Text »** (emerald) pour ouvrir dans Type Studio, **« Edit in Type Studio »** (purple) pour les assets de texte.
- Cliquez sur n'importe quelle image pour ouvrir la modale **AssetViewer** avec :
  - **Zoom/panoramique** — molette de la souris pour zoomer, glisser pour se déplacer, boutons Fit/1:1 avec mise en évidence du mode actif.
  - **Onglet Edit** — inpaint, erase, outpaint, search & replace, ou recolor de l'image directement. Deux types d'éditeurs sont proposés par mode : **basé sur masque** (Stability) — peignez un masque avec l'outil pinceau, entrez un prompt, et appliquez ; et **éditeurs à instructions sans masque** (Qwen-Image-Edit, une fois déployés) — décrivez simplement le changement en mots, aucun masque nécessaire. Les contrôles du pinceau se cachent automatiquement pour un modèle sans masque. Choisissez le modèle d'édition, appliquez ; par défaut cela remplace l'image originale, décochez « Replace original » pour enregistrer comme un nouvel asset (chaque édition préserve l'historique des versions).
  - **Previous / Next** — boutons fléchés et gauche/droite au clavier pour naviguer dans la liste sans fermer la visionneuse.
  - **Métadonnées complètes** : prompt original, prompt amélioré par l'IA, prompt de génération, prompt négatif, style, type d'asset, modèle d'image (noms conviviaux), dimensions, seed, batch ID, index option/variation, statut de déclaration IP, nom de fichier, et date de création.
- **Snapshot de style** : Chaque asset stocke un instantané du style utilisé au moment de la génération (nom, description, indications, analyse). Si le style original est supprimé plus tard, l'asset conserve le contexte complet. Rétrocompatible — les anciens assets sans snapshots s'affichent normalement.

### 📝 6.9 Entrée vocale

Cliquez sur le bouton microphone à côté de l'éditeur de prompt pour dicter votre prompt. L'audio est envoyé à Nova Sonic pour transcription.

> [!NOTE]
> La transcription vocale nécessite l'API de streaming bidirectionnel de Nova Sonic, qui dépend d'une version compatible de boto3 et de l'accès au modèle activé dans us-east-1. Si l'API de streaming n'est pas disponible, le service renvoie un accusé de réception placeholder. La transcription complète en temps réel fonctionne lorsque le streaming Nova Sonic est correctement configuré.

### 📝 6.10 Préservation de l'état des vues

Ordre de navigation : **Style Library → 2D Image Studio → Type Studio → Video Studio → Gallery**. Passer d'une vue à l'autre préserve l'état DOM de chaque vue. Les résultats générés, les saisies de formulaire et les positions de défilement survivent à la navigation. Le bouton de réinitialisation ambre dans le 2D Image Studio et le Video Studio est le seul moyen d'effacer leur état.

### 📝 6.11 Gestion des modèles

Toute la configuration des modèles d'IA est centralisée dans `backend/model_registry.json` — la source de vérité unique. Modèles, régions, tarifs, niveaux de qualité et templates de format sont tous stockés ici et gérés via l'UI ou l'API :

- Cliquez sur **« Model Settings »** dans la barre latérale de n'importe quel studio pour ouvrir la modale d'administration — elle s'ouvre sur l'onglet pertinent pour ce studio.
- **9 onglets** organisés par studio :
  - **Image Studio** — Modèles de génération d'images (SD 3.5 Large, Stable Image Ultra, Stable Image Core, plus FLUX, HunyuanImage, Qwen-Image auto-hébergés), régions, niveaux de qualité, limites de prompt, sévérité de modération
  - **Video Studio** — Modèles vidéo (Nova Reel, Luma Ray), paramètres de bucket S3, régions, tarifs
  - **Chat Studio** — Modèles chat/LLM découverts (80+ de 16 fournisseurs), fenêtres de contexte, capacité vision, tarif par 1K tokens
  - **Type Studio** — Modèle LLM pour la génération de mise en page de texte (Complex ou Fast LLM)
  - **Shared Studio** — Catégories LLM inter-studios (Fast LLM, Complex LLM, Fallback LLM, Voice), modèles de post-traitement (Remove Background, Upscale)
  - **Custom Models** — le catalogue de modèles auto-hébergés : déployer, surveiller et démanteler les endpoints SageMaker (voir section 6.12)
  - **Prompt Templates** — 28 prompts directifs LLM éditables organisés en 6 sections de workflow (voir section 4.4)
  - **Registry JSON** — Éditeur JSON brut pour le registre complet des modèles
  - **Maintenance** — état des outils gérés (p. ex. le Blender headless utilisé pour l'export FBX/USD : chemin, version, mise à jour à la demande)
- Toutes les sections sont **repliables** avec des bascules **Show All / Hide All** pour une navigation rapide.
- Les catégories LLM et le post-traitement utilisent des **sélecteurs de modèles en menu déroulant** (peuplés à partir des modèles découverts) — pas des champs de texte bruts.
- **Sync from AWS** : Scanne toutes les régions AWS supportées par Bedrock (découvertes dynamiquement), auto-enregistre les nouveaux modèles d'image, vidéo et **chat**, met à jour la disponibilité régionale, récupère les tarifs par modèle depuis l'API AWS Pricing, et désactive les modèles qui ne sont plus disponibles. Une **superposition de progression en direct** streame chaque région au fur et à mesure de son scan. C'est la **seule** action qui appelle les API de découverte AWS — toutes les autres opérations lisent depuis le registre en cache.
- **Toujours sur le Claude le plus récent** : Chaque Sync fait automatiquement rouler votre **Fast LLM** vers le Claude Sonnet le plus récent et votre **Complex LLM** vers le Claude Opus le plus récent disponible dans votre compte, pour que vous ne soyez jamais bloqué sur un modèle déprécié — aucune config manuelle nécessaire. Si vous choisissez manuellement un modèle spécifique pour une catégorie, il est **épinglé** et le roulement automatique le laisse tranquille (il vous notifie simplement quand un plus récent apparaît).
- **Découverte de modèles personnalisés** : Le Sync découvre aussi les **modèles personnalisés fine-tunés** (`ListCustomModels`), les **modèles importés** (`ListImportedModels`), et les modèles avec **déploiements on-demand** (`ListCustomModelDeployments`) ou **throughput provisionné** (`ListProvisionedModelThroughputs`). Les modèles personnalisés héritent automatiquement de leur famille de format du modèle de base.
- **Auto-découverte** : Les nouveaux modèles de fondation sont enregistrés avec `enabled=true` — l'administrateur peut les désactiver. Les modèles existants voient leurs `available_regions` et métadonnées Bedrock (modalités, cycle de vie, ARN) mis à jour automatiquement.
- **Boîtes de dialogue de confirmation stylisées** : Toutes les actions destructrices (Sync, delete, reset) utilisent des modales personnalisées stylisées — pas de popups `confirm()` du navigateur.
- Les changements sont persistés immédiatement dans `model_registry.json` via l'Admin API.
- Le registre est rétrocompatible — les assets existants référencent des clés de modèles (par ex. `sd35_large`), pas des IDs de modèles Bedrock bruts.

### 📝 6.12 Modèles auto-hébergés (Custom Models sur Amazon SageMaker)

ArtSmoker peut déployer des modèles d'IA open source sur **Amazon SageMaker** dans votre propre compte AWS, étendant vos capacités au-delà de ce qu'offre Amazon Bedrock. Ceux-ci fonctionnent aux côtés des modèles Bedrock et apparaissent dans les mêmes menus déroulants des studios.

**Catalogue de modèles extensible :** Livré avec un catalogue intégré de modèles open source couvrant la génération d'images, l'upscaling, la suppression d'arrière-plan, l'estimation de profondeur, la segmentation et la vidéo. Ajouter un nouveau modèle ne nécessite qu'une entrée de catalogue — aucun changement de code. Vous pouvez aussi ajouter des modèles personnalisés via l'UI (+ Add Model). Le catalogue et les modèles disponibles évoluent au fil du temps.

**Options de déploiement :**
- **Async (scale-to-zero)** — payez uniquement quand vous générez. Se met à l'échelle à zéro en veille (0$ de coût), monte en charge automatiquement à la nouvelle requête. Démarrage à froid ~5-10 min.
- **Always-On** — réponses instantanées, ~$1.41/h (ml.g5.xlarge)

**Comment déployer :** Model Settings → onglet Custom Models → cliquez sur Deploy. Le conteneur SageMaker télécharge les poids du modèle directement depuis HuggingFace au démarrage — aucun téléchargement local de plusieurs Go requis.

**CPU offloading :** Les grands modèles de diffusion utilisent un offloading CPU intelligent pour tenir sur des instances GPU plus petites. L'entrée de catalogue de chaque modèle spécifie la stratégie — `model_cpu_offload` (garde les couches actives sur le GPU) ou `sequential_cpu_offload` (offload agressif couche par couche pour les très grands modèles). Appliqué automatiquement par le gestionnaire d'inférence.

**Génération asynchrone avec Pending Jobs :** Les modèles auto-hébergés génèrent de manière asynchrone. Un panneau **Pending Jobs** apparaît dans le 2D Image Studio montrant les jobs actifs avec des indicateurs de progression. Les images terminées arrivent dans la Galerie automatiquement — aucun polling ni rafraîchissement de page nécessaire.

**Gestion des jetons HuggingFace :** Les modèles à accès restreint nécessitent un jeton HuggingFace en lecture seule. Le jeton est stocké chiffré dans **AWS Secrets Manager** de votre compte, géré via l'UI (définir/mettre à jour/supprimer), et partagé entre tous les modèles qui en ont besoin. Les jetons sont automatiquement nettoyés lorsque vous démantelez tous les modèles.

**Pré-vérification d'accès restreint :** Avant un déploiement à accès restreint, la boîte de dialogue sonde **chaque** dépôt HuggingFace que le modèle télécharge (ses propres poids plus toute dépendance) à l'aide de votre jeton stocké, et affiche un ✓/✗ par dépôt avec l'étape suivante exacte — accepter la licence de *ce* dépôt sur HuggingFace, ou ajouter un jeton. Le déploiement reste bloqué tant que chaque dépôt requis n'est pas accessible, de sorte qu'une acceptation de licence oubliée échoue rapidement dans la boîte de dialogue au lieu de plusieurs minutes après le début d'un démarrage à froid.

**Configuration :** Ajoutez les permissions Amazon SageMaker et Secrets Manager au **même rôle IAM** que vous utilisez déjà pour Bedrock — aucun rôle séparé ni variable d'environnement nécessaire. ArtSmoker découvre automatiquement votre rôle sur EC2/ECS, ou auto-crée un `ArtSmokerSageMakerRole` si besoin.

```bash
# Add Amazon SageMaker permissions to your existing ArtSmoker role (one command)
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
```

**Dépendance Python :** `huggingface_hub>=0.23` (installer avec `pip install huggingface_hub`)

### 📝 6.13 Modèles de génération d'images et de vidéos

Tous les modèles sont **découverts dynamiquement** depuis le registre — pas codés en dur. Le menu déroulant de l'Image Studio est peuplé depuis `GET /api/admin/models/image-options` et celui du Video Studio depuis `GET /api/admin/models/video-options` au chargement de la page. Tout modèle enregistré et activé dans le registre apparaît automatiquement.

Le menu déroulant **Image Model** est la sélection principale. En dessous, une ligne de résumé intelligente affiche la région active, le niveau de qualité et le coût par image. Une section **Advanced** extensible permet de surcharger :

- **Quality** — les modèles qui supportent des niveaux de qualité (une répartition de prix Standard/Premium) affichent un menu déroulant ; les modèles sans niveaux affichent « Default ». Les niveaux sont déclarés par modèle dans le registre via `quality_options`.
- **Region** — affiche les régions où le modèle sélectionné est disponible, triées du moins cher au plus cher avec les tarifs. « Auto » sélectionne la région la moins chère.

Une **estimation des coûts** se met à jour dynamiquement en fonction de toutes les sélections (modèle × qualité × région × options × variations).

**Familles de format** : Les modèles sont invoqués via un invocateur générique qui lit les templates de requête depuis le registre (`format_families`) — génération, édition, post-traitement et vidéo sont entièrement pilotés par templates. Ajouter un nouveau modèle d'image Bedrock ne nécessite **aucun changement de code** : enregistrez-le simplement (via l'auto-découverte ou l'Admin API) avec la bonne famille de format. Le catalogue complet des familles se trouve dans [SPEC.md](SPEC.md).

**Ingénierie de prompts optimisée par modèle** : Les prompts sont automatiquement structurés en légendes descriptives (pas en commandes) selon la [documentation AWS](https://docs.aws.amazon.com/nova/latest/userguide/prompting-image-generation.html). Les mots de négation sont retirés du prompt principal et les termes d'exclusion sont envoyés comme un **prompt négatif** distinct. Le prompt est tronqué au `prompt_limit` spécifique de chaque modèle depuis le registre.

> [!NOTE]
> **La sensibilité de modération varie selon le modèle** et est suivie dans le registre (`moderation_strictness`). Les modèles Amazon Bedrock Stability (SD 3.5 Large, Stable Image Ultra, Stable Image Core) appliquent la modération de la plateforme AWS et sont réglés en « moderate » ; les modèles auto-hébergés (FLUX, HunyuanImage, Qwen-Image) s'exécutent dans votre propre compte sans filtre de contenu imposé par la plateforme. ArtSmoker gère les blocages automatiquement — quand un prompt est rejeté, le système essaie des modèles alternatifs ordonnés par sévérité avant de suggérer une réécriture.

## 📌 7. Stack technique

| Couche | Technologie |
|--------|-------------|
| Backend | FastAPI (Python 3.11+), boto3, Pydantic |
| Frontend | Vanilla JS, Tailwind CSS (CDN) |
| IA (LLM) | Claude Sonnet (tâches rapides), Claude Opus (tâches complexes) |
| IA (Image) | Stable Diffusion 3.5 Large, Stable Image Ultra, Stable Image Core (Amazon Bedrock) ; FLUX.2/FLUX.1, HunyuanImage 3.0, Qwen-Image (auto-hébergés sur SageMaker) |
| IA (Post-traitement) | Stability AI (Remove Background, Creative Upscale) |
| IA (Chat) | 80+ LLM de 16 fournisseurs via Bedrock ConverseStream (Claude, Nova, Llama, Mistral, etc.) |
| IA (Vidéo) | Nova Reel v1.0/v1.1 (jusqu'à 2 min), Luma AI Ray v2 (jusqu'à 9 s) |
| IA (Voix) | Nova Sonic (voix vers texte via streaming bidirectionnel) |
| i18n | Fonction t() personnalisée, ~1 500 clés × 9 langues, traduction DOM par recherche inversée |
| Conversion SVG | vtracer (principal), potrace (fallback), Pillow (dernier recours) |
| Rendu texte | Pillow (ombre, contour, effets de lueur) |
| Stockage | Système de fichiers local (interface compatible S3) |
| Dev | Middleware no-cache pour les fichiers statiques ; journalisation d'erreurs côté client via `POST /api/log` |

Aucune étape de build requise pour le frontend.

## 📌 8. Modèle de sécurité

ArtSmoker est conçu comme un **outil de développement local/réseau de confiance** — il fonctionne sur la machine du développeur ou sur une instance EC2 privée. Le modèle de sécurité reflète cela :

- **Pas d'authentification** — tous les endpoints API sont ouverts. Approprié pour le développement local et les déploiements d'équipe privés.
- **Explorateur de système de fichiers** — l'endpoint `GET /api/browse/local` permet de parcourir n'importe quel répertoire accessible par le processus serveur. Ceci est intentionnel pour l'importation d'art de référence depuis votre machine.
- **Service de polices** — la protection contre le path traversal valide que les requêtes de fichiers de police restent dans les répertoires attendus.
- **Accès S3** — La navigation et l'importation S3 utilisent les identifiants AWS du serveur. L'utilisateur peut accéder à n'importe quel bucket S3 que son rôle IAM permet.

> [!WARNING]
> N'exposez pas ArtSmoker à des réseaux non fiables sans ajouter l'authentification et les restrictions de chemins. Consultez la [feuille de route de déploiement dans SPEC.md](SPEC.md#16-deployment--scaling-roadmap) pour les recommandations de durcissement en production (la Phase 4 ajoute l'authentification Cognito).

## 📌 9. API

Docs interactives sur **http://localhost:8000/docs** (Swagger UI).

Endpoints clés :

| Endpoint | But |
|----------|-----|
| **Generation** | |
| `POST /api/generate/` | Générer des assets (options × variations) avec streaming SSE |
| `POST /api/generate/post-process` | Appliquer un traitement aux assets existants |
| `POST /api/generate/edit` | Édition d'image : inpaint, outpaint, erase, search-replace, etc. Accepte l'image source, le masque, le prompt, le modèle. |
| `POST /api/generate/suggest-edit-prompt` | IA « Generate Prompt » pour l'onglet Edit : lit l'image + le prompt original et renvoie un prompt d'édition pour un mode donné, formaté pour le modèle d'édition cible (légende vs. instruction) |
| `POST /api/generate/analyze-moderation` | Analyser un prompt bloqué par la modération et suggérer une réécriture sûre |
| **Styles** | |
| `POST /api/styles/` | Créer un profil de style |
| `POST /api/styles/{id}/import` | Importer en masse des références depuis un dossier local ou un URI S3 |
| `POST /api/styles/{id}/analyze` | Déclencher l'analyse de style par l'IA |
| **Prompt** | |
| `POST /api/refine-prompt/` | Aperçu d'un prompt affiné |
| `POST /api/transcribe/` | Voix vers texte (Nova Sonic) |
| **Gallery** | |
| `GET /api/gallery/` | Parcourir les assets générés (supporte la pagination limit/offset) |
| `GET /api/gallery/batch/{batch_id}` | Reconstruire la structure complète options × variations d'un lot |
| `DELETE /api/gallery/` | Supprimer des assets en masse |
| **Type Studio** | |
| `POST /api/type-studio/preview` | Rendre l'aperçu de la superposition de texte |
| `POST /api/type-studio/suggest` | Suggestion de mise en page IA pour le texte |
| `GET /api/type-studio/fonts` | Lister les polices disponibles |
| **Browse** | |
| `GET /api/browse/local?path=~` | Parcourir le contenu d'un répertoire local |
| `GET /api/browse/s3/buckets` | Lister les buckets S3 disponibles |
| `GET /api/browse/s3?bucket=name&prefix=path` | Parcourir le contenu d'un bucket S3 |
| **Chat** | |
| `POST /api/chat/stream` | Streamer la réponse LLM via SSE (Bedrock ConverseStream) |
| `GET /api/chat/models` | Lister tous les modèles de chat disponibles (foundation + custom + imported) |
| `POST /api/chat/sessions` | Créer une nouvelle session de chat |
| `GET /api/chat/sessions` | Lister les sessions de chat |
| `GET /api/chat/sessions/{id}` | Charger une session complète (messages + métadonnées) |
| `PUT /api/chat/sessions/{id}` | Mettre à jour une session (titre, messages, modèle, température) |
| `DELETE /api/chat/sessions/{id}` | Supprimer une session |
| `POST /api/chat/sessions/{id}/duplicate` | Dupliquer une session |
| `GET /api/chat/sessions/{id}/export` | Exporter une session en Markdown |
| `GET /api/chat/sessions/{id}/search?q=` | Rechercher dans les messages d'une session |
| `POST /api/chat/compact` | Compacter les messages anciens via résumé LLM |
| `POST /api/chat/generate-title` | Auto-générer un titre de session à partir du premier échange |
| **Video** | |
| `POST /api/video/generate` | Démarrer un job de génération vidéo asynchrone |
| `GET /api/video/status/{job_id}` | Interroger le statut d'un job de génération vidéo |
| `GET /api/video/jobs` | Lister tous les jobs de génération vidéo |
| `GET /api/video/{id}/mp4` | Servir le fichier vidéo MP4 |
| `GET /api/video/{id}/thumbnail` | Servir la vignette vidéo |
| `DELETE /api/video/{id}` | Supprimer une vidéo |
| **Admin** | |
| `GET /api/admin/models` | Obtenir le registre complet des modèles (LLMs, modèles d'image, post-traitement) |
| `GET /api/admin/models/image-options` | Modèles text-to-image activés pour le menu déroulant (avec tarifs, niveaux de qualité, régions). Accepte le filtre `?region=`. |
| `GET /api/admin/regions` | Liste en cache des régions AWS supportées par Bedrock (aucun appel AWS) |
| `PATCH /api/admin/models/category/{name}` | Mettre à jour la config d'une catégorie LLM |
| `PATCH /api/admin/models/image/{key}` | Mettre à jour la config d'un modèle d'image |
| `POST /api/admin/models/image` | Ajouter un nouveau modèle d'image |
| `POST /api/admin/discover/refresh-all` | Rafraîchissement complet : découvrir régions + scanner modèles + récupérer tarifs + purger données obsolètes. Le SEUL endpoint qui appelle les API de découverte AWS. |
| `POST /api/admin/discover/{region}/auto-register` | Scanner une seule région pour les modèles, enregistrer les nouveaux, mettre à jour les régions des existants |
| `GET /api/admin/discover/{region}` | Découvrir les modèles Bedrock disponibles dans une région (listing brut) |
| `GET /api/admin/templates` | Obtenir les 28 prompt templates éditables |
| `PATCH /api/admin/templates/{name}` | Mettre à jour un template (valide les variables requises) |
| `POST /api/admin/templates/{name}/reset` | Réinitialiser un template par défaut |
| `POST /api/admin/templates/{name}/enhance` | Améliorer un template avec l'IA |
| **System** | |
| `POST /api/log` | Journalisation d'erreurs/avertissements côté client (enregistrée en `[CLIENT]` dans la console serveur) |
| `GET /api/health` | Health check + validation des identifiants AWS/Bedrock |

## 📌 10. Structure du projet

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
│       │   ├── en.json          # Anglais (base) — ~1 500 clés
│       │   └── ja/zh/ko/hi/ru/fr/es/de.json   # 8 traductions
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

## 📌 11. Limites configurables

Les paramètres de `backend/config.py` peuvent être surchargés via des variables d'environnement (préfixe `ARTSMOKER_`) :

| Paramètre | Variable d'env | Défaut | But |
|-----------|----------------|--------|-----|
| `max_reference_images` | `ARTSMOKER_MAX_REFERENCE_IMAGES` | 100 | Nombre max d'images importées par style |
| `max_analysis_images` | `ARTSMOKER_MAX_ANALYSIS_IMAGES` | 20 | Nombre max d'images envoyées à l'IA par appel d'analyse |
| `aws_region_models` | `ARTSMOKER_AWS_REGION_MODELS` | us-west-2 | Région pour les modèles Claude + Stability AI |
| `aws_region_images` | `ARTSMOKER_AWS_REGION_IMAGES` | us-east-1 | Région pour Amazon (voix Nova Sonic, vidéo Nova Reel) |
| `aws_profile` | `ARTSMOKER_AWS_PROFILE` | None | Nom du profil AWS (utilise la chaîne par défaut si non défini) |
| `auto_update` | `ARTSMOKER_AUTO_UPDATE` | true | Git pull au démarrage + vérification périodique 24h, redémarrage auto après mise à jour |

Réduire `max_analysis_images` réduit les coûts de vision IA par analyse. Réduire `max_reference_images` limite le stockage. Les deux peuvent être ajustés selon le budget.

## 📌 12. Tarification Amazon Bedrock et ventilation des coûts

> [!IMPORTANT]
> **Les modèles sont dépréciés et changent rapidement.** De nouveaux modèles sortent et les anciens sont retirés fréquemment, si bien que tout nom de modèle ou tarif codé en dur dans la documentation devient vite obsolète. ArtSmoker gère cela automatiquement — chaque **Sync from AWS** redécouvre la gamme de modèles actuelle, bascule automatiquement les emplacements LLM partagés vers les Claude Sonnet/Opus les plus récents, et rafraîchit les tarifs en direct par modèle depuis l'API AWS Pricing dans `model_registry.json`. **L'application fait autorité** — à la fois sur les modèles qui existent et sur leur coût (affiché en direct dans la barre latérale de l'Image Studio selon le modèle sélectionné, le niveau de qualité, la région et la taille du lot). Les noms de modèles et tous les chiffres ci-dessous ne sont que des **exemples illustratifs** — confirmez toujours les modèles/tarifs actuels dans l'application ou sur la [page de tarification Amazon Bedrock](https://aws.amazon.com/bedrock/pricing/) officielle.

Les **régions par défaut** de l'application sont `us-west-2` (Claude, Stability AI) et `us-east-1` (Amazon Nova Sonic, Nova Reel) ; les prix diffèrent selon la région. Consultez également [SPEC.md](SPEC.md#14-amazon-bedrock-pricing--cost-breakdown) pour le modèle de coût.

### 📝 12.1 Tarification à l'unité

Ce qui génère des coûts, et son unité de facturation (voir l'application pour le tarif unitaire actuel) :

| Service | Facturé | Notes |
|---------|---------|-------|
| **Ingénierie de prompts LLM et chat** (Claude Sonnet / Opus, basculés vers les plus récents à la synchro) | par token entrée / sortie | Affinage de prompts, concepts, chat, analyse de style, modération |
| **Génération d'images Bedrock** (Stable Diffusion 3.5 Large, Stable Image Ultra, Stable Image Core) | par image | Ultra ≫ SD 3.5 ≫ Core en prix ; chiffre en direct affiché dans l'application |
| **Images/3D auto-hébergés** (FLUX, HunyuanImage, Qwen-Image, TripoSG, TRELLIS.2) | par seconde-GPU de votre instance SageMaker | Scale-to-zero à l'inactivité (0$) ; non facturé par image |
| **Post-traitement** (Remove Background, Creative Upscale) | par image | Services Stability AI |
| **Conversion SVG** | gratuit | Local (vtracer/potrace) — $0.00 |

> [!NOTE]
> Tarifs issus de la [page de tarification Amazon Bedrock](https://aws.amazon.com/bedrock/pricing/) officielle en date de mars 2026. Les tarifs peuvent changer — vérifiez toujours auprès de la source officielle avant de budgéter.

### 📝 12.2 Coûts LLM additionnels (par utilisation)

Ces appels LLM sont inclus dans le workflow de génération mais ne sont pas détaillés séparément dans les tableaux de coûts par lot ci-dessous :

| Appel | Modèle | Quand | Coût approx. |
|-------|--------|-------|--------------|
| **Prompt Pre-Check** | Claude Sonnet | Avant la génération (si le toggle est activé) | ~$0.005 |
| **Moderation Rewrite** | Claude Sonnet | Uniquement quand tous les modèles rejettent un prompt | ~$0.005 |
| **Type Studio Layout** | Claude Opus | Chaque demande de suggestion de mise en page IA | ~$0.02–$0.05 |

Ceux-ci sont faibles — la pré-vérification et la réécriture de modération coûtent une fraction de centime chacune. La mise en page Type Studio est comparable à un affinage de prompt à option unique.

### 📝 12.3 Coût de l'analyse de style (unique par style)

~**$0.14** par style (20 images envoyées à Claude Opus + vérification de cohésion de 8 images avec Claude Sonnet). La vérification de cohésion ajoute ~$0.01 (Sonnet avec 8 images est très bon marché).

### 📝 12.4 Coût de génération selon la taille du lot

Inclut l'affinage de prompts/la génération de concepts + la génération d'images :

| Scénario | Stable Image Core | Stable Diffusion 3.5 Large | Stable Image Ultra |
|----------|-------------------|----------------------------|--------------------|
| 1 option × 1 variation | ~$0.05 | ~$0.09 | ~$0.15 |
| 1 option × 5 variations | ~$0.21 | ~$0.41 | ~$0.71 |
| 5 options × 5 variations | ~$1.05 | ~$2.05 | ~$3.55 |

Les modèles SageMaker auto-hébergés (FLUX, HunyuanImage, Qwen-Image) sont facturés au temps GPU sur votre propre instance (scale-to-zero à l'inactivité), pas par image — voir [SPEC.md](SPEC.md#14-amazon-bedrock-pricing--cost-breakdown) pour le modèle de coût de calcul.

### 📝 12.5 Options de post-traitement (par image)

| Option | Par image | 1 image | 5 images | 25 images |
|--------|-----------|---------|----------|-----------|
| Remove Background | $0.07 | $0.07 | $0.35 | $1.75 |
| Creative Upscale | $0.60 | $0.60 | $3.00 | $15.00 |
| Convert to SVG | $0.00 | $0.00 | $0.00 | $0.00 |

> [!TIP]
> **Note Creative Upscale** : Gère automatiquement la limite de charge utile de réponse de 16 Mo de Stability AI en utilisant le format de sortie JPEG en interne, puis en reconvertissant en PNG. Inclut un réessai avec backoff exponentiel pour la limitation d'API.

### 📝 12.6 Exemples chiffrés

| Exemple | Configuration | Coût total |
|---------|---------------|------------|
| **Le moins cher** | 1×1, Stable Image Core, aucun traitement | ~$0.05 |
| **Standard** | 1×5, Stable Diffusion 3.5 Large, Remove BG | ~$0.76 |
| **Exploration complète** | 5×5, Stable Diffusion 3.5 Large, Remove BG + SVG | ~$3.80 |
| **Premium** | 5×5, Stable Image Ultra, Remove BG + Upscale + SVG | ~$20.30 |

> [!TIP]
> **Point clé** : La génération d'images en elle-même est peu coûteuse ($0.01–$0.14/image). **Le Creative Upscale à $0.60/image est le coût dominant** — utilisez-le sélectivement sur vos assets finaux choisis, pas sur l'ensemble du lot. Le Remove Background à $0.07/image est raisonnable. La conversion SVG est gratuite (exécution locale).

<a id="disclaimer"></a>

## 📌 13. Clause de non-responsabilité

> [!IMPORTANT]
> **Qualité du contenu généré** : Toutes les images, vidéos et autres assets générés par ArtSmoker sont produits par des modèles d'IA disponibles via Amazon Bedrock, incluant à la fois des modèles AWS de première partie et des modèles tiers. La qualité, la précision et l'adéquation du contenu généré dépendent entièrement des prompts fournis, des modèles sélectionnés et des références de style téléchargées par l'utilisateur. Les auteurs et contributeurs d'ArtSmoker ne garantissent en aucun cas la qualité, l'adéquation ou l'aptitude à un usage particulier du contenu généré.
>
> **Propriété intellectuelle** : Les utilisateurs sont seuls responsables de s'assurer que leurs prompts, images de référence et productions générées ne portent pas atteinte aux droits de propriété intellectuelle de tiers, y compris mais sans s'y limiter les droits d'auteur, les marques déposées et les droits à l'image. ArtSmoker est un outil — il ne filtre, ne valide ni n'évalue le statut de propriété intellectuelle des entrées ou des sorties. Les auteurs et contributeurs de l'outil déclinent toute responsabilité pour toute atteinte à la propriété intellectuelle résultant de l'utilisation de ce logiciel.
>
> **Modèles d'IA et conditions de service** : Le contenu généré est soumis aux conditions d'utilisation et aux politiques d'utilisation acceptable des fournisseurs de modèles d'IA sous-jacents accessibles via Amazon Bedrock. Les utilisateurs doivent consulter les [AWS Service Terms](https://aws.amazon.com/service-terms/), le [Amazon Bedrock SLA](https://aws.amazon.com/bedrock/sla/), et les conditions des fournisseurs de modèles individuels avant d'utiliser des assets générés dans des contextes de production ou commerciaux.
>
> **Licences de modèles et usage commercial** : Les modèles auto-hébergés déployés via ArtSmoker sont régis par les conditions de licence de leurs créateurs, qui **vous** lient directement. ArtSmoker affiche la licence et la ventilation des dépendances de chaque modèle au moment du déploiement et enregistre votre acceptation, mais il ne vérifie, n'impose ni ne garantit **en aucun cas** votre droit d'usage commercial — rester dans les limites de la licence (seuils de chiffre d'affaires/d'utilisateurs, restrictions territoriales, obligations d'attribution, rapports d'utilisation) relève de votre seule responsabilité. Les indications sur les licences commerciales de la [section 1.9.3](#-193-utiliser-un-modèle-commercialement--qui-payer-et-comment) sont fournies à titre informatif uniquement, reflètent les conditions des éditeurs au moment de la rédaction et ne constituent **pas un avis juridique** ; les conditions de licence changent fréquemment — confirmez toujours les conditions actuelles de l'éditeur et consultez un juriste avant tout lancement commercial. ArtSmoker n'a aucune affiliation avec les éditeurs de modèles et ne reçoit rien d'eux.
>
> **Coûts fournis à titre d'estimation — surveillez vos propres dépenses** : Tous les coûts affichés dans ArtSmoker (par image, par vidéo, par token, calcul 3D, déploiement et totaux de session/asset) sont des **estimations fournies à titre indicatif**, calculées à partir des tarifs publiés par AWS et de l'usage prévu. Ce ne sont **ni une facture ni une garantie** de vos frais réels. Les coûts réels dépendent des tarifs de votre compte AWS, de la région, des remises, des taxes, du transfert de données, du temps de fonctionnement des endpoints (y compris les instances SageMaker inactives/maintenues au chaud), du comportement de l'auto-scaling et de facteurs indépendants de cet outil. **Vous êtes seul responsable du suivi et du contrôle de vos propres dépenses AWS** — utilisez la [console de facturation AWS](https://console.aws.amazon.com/billing/), [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/) et les [budgets/alertes de facturation](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html) pour suivre et plafonner les frais réels. Les endpoints SageMaker auto-hébergés en particulier continuent d'être facturés tant qu'ils sont déployés ou maintenus au chaud, même inactifs — pensez à les supprimer une fois terminé. Les auteurs et contributeurs déclinent toute responsabilité pour les frais AWS engagés par l'utilisation de ce logiciel.
>
> **Aucune garantie** : Ce logiciel est fourni « tel quel » sans garantie d'aucune sorte. Consultez la [LICENSE](LICENSE) pour les conditions complètes.

## 📌 14. Spécification complète

Consultez **[SPEC.md](SPEC.md)** pour la spécification technique complète — architecture, conception des composants, configuration des modèles, référence API, modèle de sécurité, tarification, feuille de route de déploiement, et suffisamment de détails pour reconstruire le projet de zéro.
