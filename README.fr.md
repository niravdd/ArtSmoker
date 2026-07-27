> Ce document est une traduction du README anglais. Pour les informations les plus récentes, consultez le [English README](README.md).

# ArtSmoker
> *Le smoke-test de vos créations artistiques !*

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green?logo=fastapi&logoColor=white)
![Amazon Bedrock](https://img.shields.io/badge/Amazon-Bedrock-orange?logo=amazonaws&logoColor=white)
![License](https://img.shields.io/badge/License-MIT--0-yellow)

## 📌 0. Présentation

Une interface simple et conviviale pour les artistes, dédiée aux modèles de génération d'images et de vidéos d'Amazon Bedrock. ArtSmoker permet aux équipes créatives d'utiliser Bedrock efficacement — sans avoir à apprendre l'API, le CLI ou l'ingénierie de prompts.

### 📝 Le problème

Les équipes créatives et les studios de jeux veulent utiliser l'IA pour la génération d'assets, mais font face à de véritables obstacles :

- **Pas d'interface simple** — les artistes ne devraient pas avoir à se connecter à la console Bedrock ou à écrire des appels API pour générer des images
- **L'ingénierie de prompts est difficile** — composer des prompts efficaces avec les bons prompts négatifs, les directives de style et le formatage spécifique à chaque modèle demande une expertise que la plupart des artistes n'ont pas
- **Les équipes ne construisent/entraînent pas leurs propres modèles** — elles ont besoin d'accéder aux nombreux modèles déjà disponibles sur Bedrock, via un outil qu'elles peuvent réellement utiliser
- **L'édition d'images est inaccessible** — l'inpainting, l'outpainting, la recherche et remplacement, et le transfert de style nécessitent tous des connaissances API
- **Le passage 2D-vers-3D est un pipeline séparé** — obtenir un modèle 3D texturé prêt pour le moteur de jeu à partir d'un concept 2D nécessite habituellement de la modélisation manuelle, du dépliage UV et de la peinture de textures — ou des outils tiers coûteux

### 📝 La solution

ArtSmoker est une application web auto-hébergée qui enveloppe Amazon Bedrock dans une interface créative épurée. Conçu spécifiquement pour la production d'assets de jeux vidéo, il est également applicable à d'autres industries créatives telles que la publicité, le e-commerce, l'édition et les médias numériques où le contenu visuel généré par l'IA a de la valeur.

- **Les artistes décrivent simplement ce dont ils ont besoin** en langage naturel — ArtSmoker gère la décomposition des prompts, l'amélioration, l'optimisation spécifique aux modèles et l'application des styles en coulisses. Un Prompt Designer guidé permet aux utilisateurs d'affiner individuellement les éléments visuels (sujet, scène, éclairage, couleurs) avec des contrôles verrouiller/varier pour des options créatives véritablement distinctes
- **Génération guidée par le style** — téléchargez l'art existant de votre jeu, et les modèles de vision d'ArtSmoker apprennent votre identité visuelle. Chaque asset généré correspond à l'apparence et à l'atmosphère de votre jeu
- **Tous les modèles Bedrock, toutes les régions** — entièrement configurable. Choisissez vos modèles text-to-image, modèles vidéo et régions. Le système découvre dynamiquement les modèles disponibles via l'API Bedrock
- **Modèles open source auto-hébergés — déploiement en 1 clic** — parcourez un catalogue organisé de modèles pré-testés (HunyuanImage 3.0, FLUX.2, et plus), choisissez une instance GPU, et déployez sur Amazon SageMaker en un clic. Tout est pris en charge : empaquetage de l'inférence, quantification, configuration CUDA, mise à l'échelle automatique et suivi des tâches. Chaque modèle du catalogue est validé de bout en bout avant publication
- **Image vers 3D en un clic** — générez un modèle 3D texturé (GLB) directement à partir de n'importe quel asset 2D ou image de personnage. La synthèse multi-vues et le baking de textures produisent des meshes prêts pour le moteur de jeu, importables directement dans Unity, Unreal ou Blender — sans modélisation manuelle
- **Votre compte AWS, votre IP** — tout s'exécute dans votre propre compte AWS privé. Toutes les oeuvres, prompts, styles et assets générés restent dans votre environnement isolé — aucune donnée ne sort vers des services tiers. Vous conservez la pleine propriété et le contrôle de votre IP créative

**Modèles Amazon Bedrock** : Claude Sonnet/Opus (ingénierie de prompts et chat), Stable Diffusion 3.5 Large, Stable Image Ultra, Stable Image Core, services Stability AI (édition d'images), Nova Reel, Luma AI Ray (génération vidéo), plus 80+ LLM de 16 fournisseurs pour Chat Studio. **Modèles auto-hébergés** : HunyuanImage 3.0 (BF16/NF4), FLUX.2, FLUX.1, TripoSG, et plus via Amazon SageMaker — avec un catalogue extensible pour ajouter de nouveaux modèles.

**[Commencer maintenant — aller aux prérequis et installation ▸](#get-started)**

### Language / 言語 / 语言 / 언어 / हिन्दी / Язык / Langue / Idioma

ArtSmoker prend en charge 8 langues. Changez la langue de l'interface via les boutons de langue dans la barre de navigation supérieure (EN | 日 | 中 | 한 | हिं | РУ | FR | ES). Votre sélection est automatiquement sauvegardée.

| Langue | README |
|--------|--------|
| English | [README.md](README.md) |
| 日本語 (Japanese) | [README.ja.md](README.ja.md) |
| 中文 (Chinese) | [README.zh.md](README.zh.md) |
| 한국어 (Korean) | [README.ko.md](README.ko.md) |
| हिन्दी (Hindi) | [README.hi.md](README.hi.md) |
| Русский (Russian) | [README.ru.md](README.ru.md) |
| Français | Ce document |
| Español (Spanish) | [README.es.md](README.es.md) |
| Deutsch (German) | [README.de.md](README.de.md) |

**Prise en charge multilingue des prompts :**
- Les prompts non anglais (japonais, chinois, coréen, hindi, russe, français, espagnol, et plus) sont automatiquement détectés et traduits en anglais avant la génération
- Un aperçu bilingue apparaît dans la zone de prompt : basculez entre votre texte original et la traduction anglaise pour voir exactement ce que le modèle recevra
- Le prompt original, la langue détectée et la traduction anglaise sont tous conservés dans les métadonnées de l'asset
- Les noms de fichiers sont générés à partir du prompt traduit en anglais (par exemple « un bâtiment d'hôpital » → `hospital-building_opt1_var1.png`)
- Chat Studio transmet les prompts directement au LLM (sans traduction) — les modèles comme Claude sont nativement multilingues
- Le texte de Type Studio reste dans votre langue (il est rendu tel quel sur l'image)
- Toutes les vérifications de modération et le filtrage de contenu s'appliquent sur le prompt traduit en anglais, par souci de cohérence

## 📌 1. Fonctionnalités

ArtSmoker fonctionne en deux modes — **autonome** (aucune configuration de style ou de thème nécessaire, décrivez et générez simplement) et **guidé par le style** (téléchargez votre art existant, et chaque génération correspond à votre identité visuelle). Les deux modes utilisent les mêmes studios et le même pipeline de génération.

### 📝 Mode autonome (démarrage rapide)

Aucune configuration de style ou de thème nécessaire — ouvrez le 2D Image Studio, le Video Studio ou le Type Studio et commencez à créer immédiatement.

1. **Décrivez ce dont vous avez besoin** — saisissez un prompt comme « hospital building » ou « fire mage character », ou utilisez l'entrée vocale. L'IA décompose votre idée en composants visuels, l'améliore avec des optimisations spécifiques au modèle, et respecte votre intention créative grâce à des contrôles intelligents verrouiller/varier. Écrivez dans n'importe quelle langue — les prompts non anglais sont traduits automatiquement.
2. **Choisissez vos modèles et paramètres** — multi-sélection parmi tous les modèles text-to-image disponibles (Amazon Bedrock + auto-hébergés sur SageMaker), choisissez les dimensions, le niveau de qualité et la région. Cochez plusieurs modèles pour une comparaison côte à côte, ou un seul pour une génération ciblée. L'estimation des coûts se met à jour en temps réel.
3. **Obtenez des options véritablement différentes** — le système génère jusqu'à 5 concepts créatifs distinctement différents (variant la tenue, l'ambiance, l'éclairage, la composition — pas seulement l'angle de caméra), chacun avec jusqu'à 5 variations de seed (25 images au total). Les détails spécifiés par l'utilisateur sont verrouillés ; les détails inférés par l'IA sont variés audacieusement.
4. **Éditez et affinez** — utilisez l'inpainting, l'outpainting, l'effacement, la recherche et remplacement ou la recoloration directement dans l'Asset Viewer. Chaque modification crée une nouvelle version — l'original est toujours préservé.
5. **Téléchargez des fichiers prêts pour le jeu** — PNG avec fond transparent + SVG, nommés de manière descriptive (par exemple `hospital-building_opt2_var3.png`). Les vidéos s'exportent en MP4.

### 📝 Mode guidé par le style (correspondre à votre style artistique et thème)

Pour les équipes qui veulent que chaque asset généré corresponde à un style artistique existant — téléchargez des images de référence et laissez l'IA apprendre d'abord votre identité visuelle.

1. **Téléchargez l'art de votre jeu** — importez des images de référence depuis des répertoires locaux (scan récursif, liens symboliques pour éviter la duplication) ou des buckets S3 (listing récursif avec pagination). **La dédoublonnage intelligent** s'exécute automatiquement — supprime les variantes de rotation (barrel_N/E/S/W.png ne conserve que barrel_S.png) et les frames d'animation (Idle0-Idle8 ne conserve que Idle). Par exemple, un pack d'assets isométriques de 747 fichiers est dédupliqué à environ 99 objets uniques. Formats supportés : .png, .jpg, .jpeg, .gif, .bmp, .webp, .tiff, .tif, .tga, .ico, .svg, plus extraction automatique de textures depuis les modèles 3D (.glb, .gltf).
2. **L'IA apprend votre style** — analyse en deux phases avec détection de cohésion : d'abord, une vérification rapide détermine si votre collection est unifiée, structurellement cohérente ou diverse. Ensuite, une analyse approfondie de l'ensemble complet de références produit un profil de style riche en métadonnées — palettes de couleurs, épaisseurs de traits, motifs d'éclairage, règles de composition et conventions de production. Si vous fournissez des indications de génération, l'IA les reçoit comme « Artist's Guidance » afin que l'analyse comprenne votre intention, pas seulement ce qui est visible.
3. **Générez avec le style appliqué** — lorsque vous sélectionnez un style dans l'Image Studio, chaque prompt est automatiquement enrichi avec les directives visuelles de votre style. Un prompt comme « hospital building » devient une instruction de génération détaillée incluant la palette de couleurs, les conventions de perspective et le style de rendu de votre jeu.
4. **Tout du mode autonome s'applique** — options multiples, comparaison de modèles, édition, versionnement et téléchargements prêts pour le jeu fonctionnent de la même manière, guidés par votre style artistique.

> [!NOTE]
> Tout le contenu généré est produit par des modèles d'IA et dépend des prompts et des références que vous fournissez. Veuillez consulter la [clause de non-responsabilité](#disclaimer) concernant la qualité du contenu, la propriété intellectuelle et les conditions de service applicables avant d'utiliser des assets générés en production.

### 📝 1.1 Aperçu des fonctionnalités

- 🎨 **Style Library** — Téléchargez votre art, l'IA apprend votre identité visuelle
- 🖼️ **2D Image Studio** — Génération d'images avec options x variations, workflow guidé en 3 étapes
- 🎨 **Prompt Designer** — L'IA décompose votre prompt en composants visuels éditables (sujet, scène, éclairage, couleurs) avec bascules verrouiller/varier par champ, intégration du style et classification intelligente du type d'asset. Photorealistic, Character, Environment, et plus
- 🎬 **Video Studio** — Text-to-video avec guidance de prompt spécifique au modèle (contrôles caméra Nova Reel, langage naturel Luma Ray), multi-shot, image-to-video
- ✍️ **Type Studio** — Superpositions de texte conçues par l'IA avec sélecteur de polices
- 💬 **Chat Studio** — Chat LLM multi-modèle avec streaming, Markdown, coloration syntaxique, vision, sessions, compactage de contexte
- 📁 **Galerie unifiée** — Parcourez images + vidéos, filtre par média, recherche, téléchargement, suppression
- 📥 **Importer une image** — Intégrez une image existante (tout format) dans la galerie comme un asset à part entière. Convertie automatiquement en PNG, associée au type d'asset que vous choisissez, et immédiatement éditable et prête pour la 3D — tout (versionnage, édition, image-vers-3D) fonctionne comme pour une image générée
- ✏️ **Édition d'images** — Inpainting, outpainting, effacement, recherche et remplacement, recoloration (dans l'AssetViewer)
- 🔄 **Progression en temps réel** — Streaming SSE avec visibilité des tentatives/limitations
- 🛡️ **Modération intelligente** — Test canari, changement automatique de modèle, réécriture assistée par l'IA
- ⚙️ **Model Registry** — Interface d'administration organisée par studio (Image, Video, Chat, Type, Shared), découverte Bedrock, support des modèles personnalisés
- 📝 **Prompt Templates** — 19 prompts directifs LLM éditables, amélioration assistée par l'IA, validation de variables avec correction automatique
- 📦 **Versionnement des assets** — Édition sur place avec historique des versions (v1, v2, ...) et navigation entre versions
- 💰 **Suivi des coûts** — Dépenses AWS estimées par requête, par session, par asset — envoyées à la télémétrie PulseBoard
- 🌐 **i18n en 8 langues** — Traduction complète de l'UI (EN, JA, ZH, KO, HI, RU, FR, ES), détection automatique des prompts non anglais, aperçu bilingue
- 🔍 **Support des modèles personnalisés** — Découverte automatique des modèles Bedrock fine-tunés, importés et déployés
- 🔧 **Modèles auto-hébergés — Déploiement en 1 clic** — Parcourez un catalogue organisé de modèles open source pré-testés (HunyuanImage 3.0, FLUX.2, FLUX.1, TripoSG, et plus), choisissez une instance GPU, et cliquez sur Deploy. ArtSmoker gère tout : empaquetage du gestionnaire d'inférence, configuration de la quantification, sélection du bon toolkit CUDA, mise en place de l'auto-scaling, enregistrement des alarmes CloudWatch, et câblage du suivi asynchrone des tâches. Chaque modèle du catalogue est validé de bout en bout — du démarrage à froid à la génération jusqu'à la livraison en galerie. Supporte BF16 + FlashInfer pour la meilleure qualité, NF4 pour l'efficacité des coûts, détection automatique multi-GPU, mise à l'échelle automatique à zéro (0$ en veille), et le même modèle fonctionne sur différents types d'instances sans reconfiguration
- 🧊 **Génération Image-to-3D** — Convertissez n'importe quelle image Game Asset ou Character en un maillage 3D texturé (GLB) en un clic. La synthèse multi-vues + le baking de textures produit des assets prêts pour les moteurs de jeu. Visionneuse 3D interactive avec orbite/zoom/panoramique
- 🩹 **Complétion intelligente de la source pour la 3D** — l'image-to-3D ne peut construire que ce qui est visible ; un personnage recadré (jambes coupées) donne un maillage sans jambes. Avant la génération, ArtSmoker vérifie l'image source par vision et, si elle est recadrée, **propose de la compléter par outpainting** (invite suggérée par l'IA, entièrement modifiable) — affiche l'avant/après, réexamine le résultat, permet d'étendre encore ou d'abandonner, et l'enregistre comme nouvelle version d'image. Optionnel et non bloquant ; les images bien cadrées sont générées directement
- 🔄 **Auto-Update** — Git pull avec contrôle de version au démarrage, redémarrage automatique après mise à jour, vérification périodique toutes les 24h (`ARTSMOKER_AUTO_UPDATE=false` pour désactiver)

### 📝 1.2 Captures d'écran

**2D Image Studio** — Paramètres à gauche avec liste déroulante multi-sélection de modèles, type d'asset, dimensions et options de post-traitement. Workflow de prompt en 3 étapes à droite avec les boutons Prompt Designer et Generate Enhanced Prompt. Déclaration IP et estimation des coûts en bas.

![2D Image Studio — Paramètres, workflow de prompt et contrôles de génération](docs/images/image-studio-top.png)

**2D Image Studio — Résultats de génération** — Le prompt amélioré est affiché au-dessus, les résultats de comparaison multi-modèle en dessous. Chaque modèle génère indépendamment avec une optimisation du prompt spécifique à chaque modèle. Les résultats affichent le nom du modèle, les dimensions et le coût de génération.

![2D Image Studio — Prompt amélioré et résultats de génération](docs/images/image-studio-results.png)

**2D Image Studio — Comparaison de modèles** — Grille de comparaison côte à côte de tous les modèles sélectionnés (7 modèles affichés). Les variations de l'option sélectionnée sont affichées en dessous. Bascules de post-traitement à gauche (Supprimer l'arrière-plan, Convertir en SVG, Agrandir).

![2D Image Studio — Grille de comparaison multi-modèle avec variations](docs/images/image-studio-comparison.png)

**Prompt Designer** — L'IA décompose votre prompt en composants visuels éditables (Sujet, Scène, Composition, Éclairage, Style et Couleurs). Chaque champ peut être édité individuellement avec des contrôles verrouiller/varier pour des options créatives véritablement distinctes.

![Prompt Designer — Décomposition visuelle structurée avec champs éditables](docs/images/prompt-designer-top.png)

**Prompt Designer — Palette de couleurs** — Palettes de couleurs nommées avec échantillons hexadécimaux, mots-clés de style et contrôles de niveau de qualité. L'IA apprend votre identité visuelle et l'applique de manière cohérente à toutes les générations.

![Prompt Designer — Palette de couleurs, mots-clés de style et contrôles de qualité](docs/images/prompt-designer-bottom.png)

**Style Library** — Téléchargez l'art existant de votre jeu, l'IA analyse le style visuel et produit un guide de prompts riche en métadonnées. Les images de référence sont affichées avec l'analyse IA complète et le profil de style JSON.

![Style Library — Analyse de style IA avec images de référence](docs/images/style-library-top.png)

![Style Library — Images de référence, options d'importation et données d'analyse](docs/images/style-library-bottom.png)

**Galerie** — Vue unifiée de toutes les images et vidéos générées avec filtre par type de média, filtre par style, recherche et tri. Cliquez sur n'importe quel asset pour ouvrir la vue complète. Le bouton **Importer une image** ajoute une image existante à la galerie — choisissez un type d'asset (Personnage／Asset de jeu activent la 3D), elle est convertie en PNG et immédiatement éditable et prête pour la 3D.

![Galerie — Grille d'assets générés avec filtres](docs/images/gallery.png)

**Asset Viewer** — Aperçu en taille réelle avec interface à onglets (PNG, Édition, SVG, Métadonnées, Modèle 3D). Téléchargement direct des PNG et SVG. Compositing sur fond transparent affiché avec motif en damier.

![Asset Viewer — Aperçu en taille réelle avec options de téléchargement](docs/images/asset-viewer.png)

**Asset Viewer — Édition d'images** — Onglet Édition avec inpainting : peignez un masque sur la zone à modifier, décrivez ce que vous souhaitez, sélectionnez un modèle d'édition et appliquez. L'historique des versions est préservé — les originaux ne sont jamais écrasés.

![Asset Viewer — Inpainting avec masque et prompt](docs/images/asset-viewer-edit.png)

**Génération de modèle 3D** — Convertissez n'importe quelle image Game Asset ou Character en un maillage 3D texturé (GLB). Configurez la résolution des marching cubes, le ratio de premier plan et les paramètres de génération directement dans l'onglet Modèle 3D de l'Asset Viewer.

![Génération de modèle 3D — Paramètres et génération dans l'Asset Viewer](docs/images/3d-model-generation.png)

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

Chaque modèle s'exécute indépendamment : si des modèles plus stricts bloquent le prompt, vous obtenez quand même les résultats des modèles qui l'ont accepté. L'estimation des coûts se met à jour en temps réel au fur et à mesure que vous cochez/décochez les modèles.

Le toggle optionnel **« Model-optimized prompts »** adapte le prompt aux forces de chaque modèle — les prompts sont réécrits par modèle (ex : boosters de qualité pour SD 3.5, langage naturel pour FLUX.2, légendes concises pour Qwen-Image).

### 📝 1.5 Video Studio

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
# Créer un bucket S3 pour le stockage vidéo (remplacez REGION et YOUR_ORG)
aws s3api create-bucket --bucket artsmoker-video-YOUR_ORG --region us-east-1

# Pour les régions autres que us-east-1, ajoutez le LocationConstraint :
aws s3api create-bucket --bucket artsmoker-video-YOUR_ORG --region us-west-2 \
  --create-bucket-configuration LocationConstraint=us-west-2
```

Mode de stockage : téléchargement local (par défaut) ou streaming depuis S3 à la demande.

**Amélioration des prompts vidéo** : Le LLM ajoute des mouvements de caméra (panoramique, zoom, dolly, tracking), des détails d'éclairage et des repères temporels. Comme les modèles vidéo ne supportent pas les prompts négatifs, les concepts à éviter sont intégrés naturellement dans le prompt positif.

### 📝 1.6 Chat Studio

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
- **Régénérer** — relancer la réponse de l'IA avec le même prompt
- **Éditer et renvoyer** — modifier n'importe quel message utilisateur et rejouer à partir de ce point
- **Forker** — créer une branche de conversation depuis n'importe quel message vers une nouvelle session

**Transparence tarifaire :** Le sélecteur de modèle affiche le coût par 1K tokens, la barre d'information tarifaire affiche le coût estimé pour des conversations de 10K et 100K tokens.

### 📝 1.7 Sensibilité au type d'asset

Le **type d'asset** sélectionné change fondamentalement la façon dont l'IA interprète votre prompt — pas seulement le modèle d'image, mais chaque étape du pipeline. Quand vous tapez « hospital » et sélectionnez différents types d'assets, vous obtenez des résultats complètement différents :

| Type | Composition | Cadrage | Approche technique |
|------|-------------|---------|-------------------|
| **Game Asset** | Objet unique isolé sur fond transparent. Pas de scène, pas de texte, pas d'UI. | Vue frontale ou isométrique, l'objet remplit 70-80% du cadre. | Bords nets et propres pour la suppression de fond, éclairage cohérent depuis le haut-gauche, pas d'ombres au sol. Conçu pour être composé avec d'autres assets de jeu à différentes échelles. |
| **Character** | Figure en pied ou 3/4, isolée sur fond propre. Un seul personnage. | Le personnage remplit 60-75% de la hauteur, de la tête aux pieds, légèrement décentré. | Silhouette lisible et forte (identifiable par la silhouette seule), pose expressive transmettant la personnalité, traits du visage et détails du costume clairs. |
| **Icon** | Symbole unique, gras et reconnaissable, centré avec un padding généreux. Simplicité maximale. | Vue frontale ou légère inclinaison 3/4, espace respirant aux bords. | Doit être clairement lisible à 64x64 pixels. Contraste élevé, 3-5 couleurs maximum, formes audacieuses, pas de lignes fines ni de détails fins. |
| **Marketing Banner** | Illustration scénique complète avec composition dramatique. Zone de texte propre réservée sur un côté — pas de texte rendu ni de typographie. | Sensation cinématique large, caméra reculée pour montrer la scène. | Couleurs riches et saturées, éclairage dramatique (rim light, rayons volumétriques), profondeur de champ. L'IA est explicitement instruite de NE PAS rendre de texte ; la zone de texte est laissée propre pour la superposition en post-production dans les outils de design (Figma, Canva, etc.). |
| **Environment** | Paysage complet avec couches de profondeur avant-plan/milieu/arrière-plan et lignes directrices. | Plan d'ensemble large, horizon au tiers supérieur ou inférieur. | Perspective atmosphérique (objets distants plus clairs/brumeux), narration environnementale par les détails, éclairage d'ambiance. |

Cela compte à chaque étape :

- **Bouton « Preview Enhanced Prompt »** — Quand vous cliquez sur Compose, l'IA utilise le type d'asset pour reformuler votre brief en un prompt de génération détaillé, combinant vos mots avec les directives de style et les directives du type d'asset. Votre intention explicite prévaut toujours sur les paramètres par défaut du style. Vous pouvez examiner la version composée avant de générer.
- **Génération de concepts** — Lors de la génération d'options multiples, l'IA crée N interprétations de design différentes qui respectent toutes les règles structurelles du type d'asset. Une option Character a toujours une silhouette lisible ; une option Marketing Banner a toujours une zone de texte sans texte rendu.
- **Le résultat** — Deux images du même prompt mais de types d'assets différents ne se ressembleront en rien. Un Game Asset « warrior » est un sprite de personnage unique centré. Un Marketing Banner « warrior » est une scène de bataille épique avec une zone propre pour la superposition du titre.

### 📝 1.8 Génération de modèles 3D (Image-to-3D)

Générez des maillages 3D entièrement texturés et prêts pour la production à partir de n'importe quelle image 2D — directement dans l'Asset Viewer. Sélectionnez une image **Game Asset** ou **Character**, ouvrez l'onglet **3D Model**, et cliquez sur Generate. Le résultat est un GLB prêt pour le moteur de jeu que vous pouvez orbiter, zoomer et télécharger — sans modélisation manuelle, dépliage UV ni peinture de texture.

**Le modèle généré — orbitez, inspectez, téléchargez :**

![Génération de modèle 3D — le maillage du soldat généré vu sous plusieurs angles dans le visualiseur 3D interactif](docs/images/3d-model-result.png)

Une seule image 2D de personnage (à gauche, dans l'onglet PNG) devient un maillage 3D entièrement texturé que vous pouvez faire pivoter librement dans le navigateur. L'onglet **3D Model** liste désormais aussi les **modèles et outils** exacts utilisés pour produire chaque asset (modèle de géométrie, backend de texturation, type de sortie, instance et paramètres de génération) — persistés dans les métadonnées de l'asset pour une traçabilité complète.

**Deux pipelines — à vous de choisir.** ArtSmoker propose deux façons de transformer une image en modèle 3D texturé. Déployez l'un (ou les deux) depuis Custom Models ; lorsque les deux sont actifs, vous choisissez par génération dans l'Asset Viewer — chacun affiche son coût est., son temps et sa licence pour que vous décidiez en connaissance de cause :

| Pipeline | Fonctionnement | Licence | Usage commercial | Idéal pour |
|----------|----------------|---------|------------------|------------|
| TripoSG + backend de texturation | TripoSG construit le maillage ; un backend de texturation choisi (TRELLIS.2 / Hunyuan3D-Paint) le peint | selon le backend (ci-dessous) | selon le backend | Combiner géométrie + un texturateur précis |
| TRELLIS.2 (Full) | Un seul modèle génère à la fois la géométrie et la texture PBR (SLAT) | MIT | ✅ Oui — attribution « Built with DINOv3 » | Production, assets commerciaux, voie la plus simple |

**Fonctionnement du pipeline TripoSG :**

1. **Extraction de géométrie** — TripoSG (1,5 milliard de paramètres, MIT) convertit une seule image 2D en un maillage 3D haute fidélité (SDF). La densité du maillage s'adapte au préréglage de qualité (jusqu'à ~1M de faces).
2. **Texturation** — peint par un backend de texturation que vous choisissez au moment du déploiement (par défaut TRELLIS.2, Microsoft, MIT — conditionné par SLAT/voxels, PBR complet sur un atlas 4096²).
3. **Sortie PBR** — exporté en GLB avec des cartes PBR intégrées, prêt pour n'importe quel moteur moderne.

Le pipeline TRELLIS.2 (Full) fait la même chose de bout en bout dans un seul modèle — sans étape de texturation séparée.

**La licence bien en vue — au déploiement ET à la génération.** Chaque option déployable affiche son détail complet de licence et de dépendances dans la boîte de dialogue de déploiement (chaque modèle qu'elle télécharge, sa licence, exploitable commercialement ou restreint) — à lire et accepter avant de déployer. Au moment de la génération, l'Asset Viewer rappelle la licence et confirme « accepté au déploiement le <date> » (sans second clic) :

| Backend de texturation | Licence | Usage commercial | Idéal pour |
|------------------------|---------|------------------|------------|
| **TRELLIS.2** *(par défaut)* | MIT | ✅ Oui — nécessite une attribution « Built with DINOv3 » dans votre produit | Production, assets commerciaux, qualité maximale |
| **Hunyuan3D-Paint** | Tencent Community | ❌ Non / Non commercial | Recherche / non commercial, visages exceptionnels |
La suppression d'arrière-plan utilise **BiRefNet (MIT)** par défaut — entièrement saine pour un usage commercial — avec une alternative non commerciale (RMBG) disponible en option déclarée. ArtSmoker ne télécharge jamais silencieusement une dépendance restreinte : tout ce qui est restreint ou non commercial est nommé, badgé et conditionné à une acceptation explicite.

**Sortie :** Format GLB standard avec textures PBR intégrées — s'importe dans Unity, Unreal Engine, Blender, etc. La visionneuse 3D interactive supporte l'orbite, le zoom et le panoramique, et l'onglet **3D Model** liste les modèles et outils exacts utilisés pour une traçabilité complète.

**Infrastructure :** Les deux pipelines se déploient via le même flux Custom Models en 1 clic, le sélecteur au moment du déploiement affichant pour chaque option sa licence, son tableau de dépendances, son instance de base et le coût/temps estimés. L'instance de base optimale du pipeline TRELLIS.2 complet est **`ml.g6e.xlarge`** (~$2,61/h ; pic mesuré ~6,5 Go de VRAM + ~22 Go de RAM hôte — c'est la RAM hôte qui constitue la contrainte limitante, pas le GPU). Les tailles `g6e` supérieures sont proposées comme montées en gamme offrant davantage de marge en RAM. Les endpoints se mettent à l'échelle à zéro en veille — $0 entre les tâches. Le premier démarrage à froid compile les extensions CUDA une seule fois (puis mises en cache sur S3). Avant de déployer un modèle à accès restreint, la boîte de dialogue **pré-vérifie l'accès HuggingFace pour chaque dépôt qu'il télécharge** et affiche un ✓/✗ par dépôt avec l'étape suivante exacte — vous ne découvrez ainsi jamais une acceptation de licence manquante plusieurs minutes après le début d'un démarrage à froid. Les modèles de pointe (OpenAI GPT-5.x, Claude Mythos, GLM, Grok, etc.) sont servis via l'endpoint Amazon Bedrock Mantle, qui requiert la permission IAM AmazonBedrockMantleInferenceAccess — consultez le README.md en anglais pour la liste complète des permissions requises.

> Visionner le GLB : les textures sont en **WebP** (**EXT_texture_webp**) pour garder des fichiers compacts — rendu parfait dans la visionneuse intégrée, Blender 4.x, three.js et les importateurs Unity/Unreal modernes. Preview/QuickLook de macOS ne prend pas en charge le WebP dans le glTF et affiche le modèle en noir ; utilisez la visionneuse intégrée ou tout outil glTF moderne.

| Métrique | Valeur |
|----------|--------|
| Qualité du maillage | Jusqu'à ~1M de faces, normales de sommets complètes |
| Résolution de texture | Atlas PBR 4096² (couleur de base + métallique-rugosité + alpha) |
| Licence | Exploitable commercialement par défaut (TRELLIS.2 MIT + BiRefNet MIT) ; backends non commerciaux proposés avec divulgation complète |
| Types d'assets supportés | Game Asset, Character |

<a id="get-started"></a>

## 📌 2. Prérequis

- **Python 3.11+** (3.12, 3.13, 3.14 fonctionnent aussi)
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

Pour les permissions IAM détaillées, les instructions d'installation, les options de configuration et les informations tarifaires, consultez les sections Prerequisites (IAM permissions), Installation, Running, Configurable Limits et Pricing du [README anglais](README.md).

## 📌 5. Architecture

```
┌─────────────────────────────────────────────┐
│  Navigateur (SPA)                           │
│  Vanilla JS + Tailwind CSS                  │
└──────────────────────┬──────────────────────┘
                       │ HTTP / SSE
                       ▼
┌─────────────────────────────────────────────┐
│  Backend FastAPI (Python)                   │
│                                             │
│  /api/styles      CRUD styles + import      │
│  /api/generate    Génération à deux niveaux │
│  /api/type-studio Superposition texte + polices │
│  /api/video       Génération vidéo + jobs   │
│  /api/chat        Chat LLM + sessions       │
│  /api/gallery     Navigation assets + export │
│  /api/browse      Explorateur fichiers/S3   │
│  /api/admin       Registre modèles + modèles│
│  /api/refine-prompt  Prompt + traduction    │
│  /api/transcribe  Voix vers texte           │
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
│  Stability AI (post) │  │                          │
└──────────────────────┘  └──────────────────────────┘ ... (autres régions)
             │
             ▼
┌──────────────────────┐
│  Stockage local       │
│  data/styles/         │
│  data/generated/      │
│  data/video/          │
│  data/chat/           │
└──────────────────────┘
```

## 📌 7. Stack technique

| Couche | Technologie |
|--------|-------------|
| Backend | FastAPI (Python 3.11+), boto3, Pydantic |
| Frontend | Vanilla JS, Tailwind CSS (CDN) |
| IA (LLM) | Claude Sonnet (tâches rapides), Claude Opus (tâches complexes) |
| IA (Image) | Stable Diffusion 3.5 Large, Stable Image Ultra, Stable Image Core |
| IA (Post-traitement) | Stability AI (Remove Background, Creative Upscale) |
| IA (Chat) | 80+ LLM de 16 fournisseurs via Bedrock ConverseStream |
| IA (Vidéo) | Nova Reel v1.0/v1.1 (jusqu'à 2 min), Luma AI Ray v2 (jusqu'à 9 s) |
| IA (Voix) | Nova Sonic (voix vers texte via streaming bidirectionnel) |
| i18n | Fonction t() personnalisée, 817 clés × 8 langues, traduction DOM par recherche inversée |
| Conversion SVG | vtracer (principal), potrace (fallback), Pillow (dernier recours) |
| Rendu texte | Pillow (ombre, contour, effets de lueur) |
| Stockage | Système de fichiers local (interface compatible S3) |
| Développement | Middleware no-cache pour fichiers statiques, journalisation d'erreurs côté client via `POST /api/log` |

Aucune étape de build requise pour le frontend.

## 📌 8. Modèle de sécurité

ArtSmoker est conçu comme un **outil de développement local/réseau de confiance** — il fonctionne sur la machine du développeur ou sur une instance EC2 privée.

- **Pas d'authentification** — tous les endpoints API sont ouverts. Approprié pour le développement local et les déploiements d'équipe privés.
- **Explorateur de système de fichiers** — l'endpoint `GET /api/browse/local` permet de parcourir n'importe quel répertoire accessible par le processus serveur. Ceci est intentionnel pour l'importation d'art de référence.
- **Accès S3** — La navigation et l'importation S3 utilisent les identifiants AWS du serveur.

> [!WARNING]
> N'exposez pas ArtSmoker à des réseaux non fiables sans ajouter l'authentification et les restrictions de chemins. Consultez le [plan de déploiement dans SPEC.md](SPEC.md#16-deployment--scaling-roadmap) pour les recommandations de durcissement en production.

## 📌 12. Tarification Amazon Bedrock et ventilation des coûts

> [!NOTE]
> Les tableaux ci-dessous sont des **tarifs de référence à des fins de planification**. L'application elle-même affiche les **tarifs en direct par modèle** dans la barre latérale de l'Image Studio — récupérés depuis l'API AWS Pricing lors du rafraîchissement du registre et stockés dans `model_registry.json`.

Les tarifs de référence proviennent de la [page de tarification Amazon Bedrock](https://aws.amazon.com/bedrock/pricing/) officielle, pour les régions par défaut de l'application — us-west-2 (Claude, Stability AI) et us-east-1 (Amazon Nova Sonic). Les tarifs peuvent varier dans les autres régions AWS ; l'application affiche toujours les tarifs en direct correspondant à la région que vous avez réellement configurée, dans la barre latérale de l'Image Studio. Consultez également [SPEC.md](SPEC.md#14-amazon-bedrock-pricing--cost-breakdown) pour les projections mensuelles par équipe et les estimations de coût de déploiement.

| Service | Modèle | Coût | Unité |
|---------|--------|------|-------|
| **Claude Sonnet** | (dernière version) | $3.00 entrée / $15.00 sortie | par million de tokens |
| **Claude Opus** | (dernière version) | $5.00 entrée / $25.00 sortie | par million de tokens |
| **Stable Diffusion 3.5 Large** | `stability.sd3-5-large-v1:0` | $0.08 | par image |
| **Stable Image Ultra** | `stability.stable-image-ultra-v1:1` | $0.14 | par image |
| **Stable Image Core** | `stability.stable-image-core-v1:1` | $0.04 | par image |
| **Remove Background** | Stability AI | $0.07 | par image |
| **Creative Upscale** | Stability AI | $0.60 | par image |
| **Conversion SVG** | Local (vtracer/potrace) | $0.00 | gratuit |

> [!TIP]
> **Point clé** : La génération d'images en elle-même est peu coûteuse ($0.01 à $0.14/image). **Le Creative Upscale à $0.60/image est le coût dominant** — utilisez-le sélectivement sur les assets finaux choisis, pas sur l'ensemble du lot. Le Remove Background à $0.07/image est raisonnable. La conversion SVG est gratuite (exécution locale).

<a id="disclaimer"></a>

## 📌 13. Clause de non-responsabilité

> [!IMPORTANT]
> **Qualité du contenu généré** : Toutes les images, vidéos et autres assets générés par ArtSmoker sont produits par des modèles d'IA disponibles via Amazon Bedrock. La qualité, la précision et l'adéquation du contenu généré dépendent entièrement des prompts fournis par l'utilisateur, des modèles sélectionnés et des références de style téléchargées. Les auteurs et contributeurs d'ArtSmoker ne garantissent en aucun cas la qualité, l'adéquation ou l'aptitude à un usage particulier du contenu généré.
>
> **Propriété intellectuelle** : Les utilisateurs sont seuls responsables de s'assurer que leurs prompts, images de référence et productions générées ne portent pas atteinte aux droits de propriété intellectuelle de tiers, y compris mais sans s'y limiter les droits d'auteur, les marques déposées et les droits à l'image. ArtSmoker est un outil — il ne filtre, ne valide ni n'évalue le statut de propriété intellectuelle des entrées ou des sorties.
>
> **Modèles d'IA et conditions de service** : Le contenu généré est soumis aux conditions d'utilisation et aux politiques d'utilisation acceptable des fournisseurs de modèles d'IA sous-jacents accessibles via Amazon Bedrock.
>
> **Coûts fournis à titre d'estimation — surveillez vos propres dépenses**: Tous les coûts affichés dans ArtSmoker (par image, par vidéo, par token, calcul 3D, déploiement et totaux de session/asset) sont des **estimations fournies à titre indicatif**, calculées à partir des tarifs publiés par AWS et de l'usage prévu. Ce ne sont **ni une facture ni une garantie** de vos frais réels. Les coûts réels dépendent des tarifs de votre compte AWS, de la région, des remises, des taxes, du transfert de données, du temps de fonctionnement des endpoints (y compris les instances SageMaker inactives/maintenues au chaud), du comportement de l'auto-scaling et de facteurs indépendants de cet outil. **Vous êtes seul responsable du suivi et du contrôle de vos propres dépenses AWS** — utilisez la [console de facturation AWS](https://console.aws.amazon.com/billing/), [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/) et les [budgets/alertes de facturation](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html) pour suivre et plafonner les frais réels. Les endpoints SageMaker auto-hébergés en particulier continuent d'être facturés tant qu'ils sont déployés ou maintenus au chaud, même inactifs — pensez à les supprimer une fois terminé. Les auteurs et contributeurs déclinent toute responsabilité pour les frais AWS engagés par l'utilisation de ce logiciel.
>
> **Aucune garantie** : Ce logiciel est fourni « tel quel » sans garantie d'aucune sorte. Consultez la [LICENSE](LICENSE) pour les conditions complètes.

## 📌 14. Spécification complète

Consultez **[SPEC.md](SPEC.md)** pour la spécification technique complète — architecture, conception des composants, configuration des modèles, référence API, modèle de sécurité, tarification, feuille de route de déploiement, et suffisamment de détails pour reconstruire le projet de zéro.
