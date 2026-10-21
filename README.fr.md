# ArtSmoker
> *Le smoke-test de vos créations artistiques !*

![Python](https://img.shields.io/badge/Python-3.12--3.14-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green?logo=fastapi&logoColor=white)
![Amazon Bedrock](https://img.shields.io/badge/Amazon-Bedrock-orange?logo=amazonaws&logoColor=white)
![License](https://img.shields.io/badge/License-MIT--0-yellow)

![Visite guidée d'ArtSmoker — du prompt texte à l'art 2D prêt pour la production, jusqu'au modèle 3D entièrement texturé et adapté au moteur de jeu](docs/images/artsmoker-walkthrough.gif)

<a id="quick-start"></a>

## 🚀 Démarrage rapide

**D'un clone tout neuf à votre premier asset généré en quelques minutes — sur macOS, Linux ou Windows.**

**Il vous faut :** Python **3.12, 3.13 ou 3.14** · Git · des identifiants AWS (`aws configure`, AWS SSO ou un rôle d'instance) avec accès à Amazon Bedrock. Le moyen le plus rapide de configurer les permissions : les politiques gérées `AmazonBedrockFullAccess` + `AmazonBedrockMantleInferenceAccess` — [détails](#iam-permissions).

> [!TIP]
> 🤖 **Vous préférez qu'on s'en charge pour vous ?** Ouvrez ce dépôt dans **[Kiro](https://kiro.dev)**, l'environnement de développement agentique d'AWS, et demandez : *« Installe et lance ArtSmoker en suivant la section Quick Start du README.md. »* L'agent de Kiro exécute les commandes à votre place.

**macOS · Linux**

```bash
git clone https://github.com/niravdd/ArtSmoker.git && cd ArtSmoker
python3 --version                                   # doit être 3.12, 3.13 ou 3.14 (sinon, utilisez p. ex. python3.14 ci-dessous)
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
python -m backend.main
```

**Windows (PowerShell)**

```powershell
git clone https://github.com/niravdd/ArtSmoker.git; cd ArtSmoker
python --version                                    # doit être 3.12, 3.13 ou 3.14 (sinon, utilisez p. ex. py -3.14 ci-dessous)
python -m venv .venv; .venv\Scripts\activate
pip install -r backend\requirements.txt
python -m backend.main
```

Ouvrez ensuite **http://localhost:8000**. Au premier lancement, ArtSmoker vérifie vos identifiants AWS et effectue une analyse unique des modèles que votre compte peut utiliser dans chaque région AWS (généralement quelques minutes) — un écran **Configuration d'ArtSmoker** affiche la progression — et vous êtes prêt à générer.

| Bloqué ? | Où aller |
|---|---|
| Votre `python3` n'est pas en 3.12–3.14 (p. ex. le `python3` système d'Amazon Linux 2023 est en 3.9 ; un `python3` Homebrew tout récent peut être en 3.15, qu'une dépendance ne prend pas encore en charge) | [3. Installation](#installation) |
| PowerShell refuse d'exécuter `.venv\Scripts\activate` | [3.3 Windows](#install-windows) |
| Erreurs d'identifiants AWS, de permissions ou de première utilisation de Claude | [2. Prérequis](#get-started) · [2.2 Permissions IAM](#iam-permissions) |
| Plusieurs utilisateurs, une machine EC2 ou la production | [4. Exécution](#running) |

## 📌 0. Présentation

**ArtSmoker transforme une idée en art adapté au moteur de jeu — en quelques minutes, sans aucun pipeline à gérer de votre côté.** Décrivez un personnage, un accessoire, un environnement ou une illustration clé en langage naturel et obtenez de l'art 2D prêt pour la production, des modèles 3D entièrement texturés et de la vidéo — le tout aligné sur l'identité visuelle de votre projet et conservé dans votre propre environnement. Les tout derniers modèles d'IA d'image, d'édition, de 3D et de vidéo se cachent derrière une interface unique, épurée et pensée avant tout pour les artistes, dotée de véritables contrôles créatifs : ArtSmoker exécute l'intégralité du pipeline de production pour vous, afin que votre équipe dirige le rendu au lieu de se débattre avec la mécanique.

### 📝 Le problème

Les équipes créatives des studios de jeux vidéo et de médias veulent tirer parti de l'IA générative — mais aujourd'hui cette puissance est enfermée derrière des outils pour développeurs qu'elles n'ont jamais été censées gérer :

- **C'est conçu pour les ingénieurs, pas pour les artistes** — les meilleurs modèles se trouvent derrière des consoles cloud, des lignes de commande, des SDK et des API REST. Aucun directeur artistique ni concept artist ne devrait avoir besoin d'un terminal pour créer une œuvre.
- **Des idées claires, des prompts obscurs** — les artistes savent exactement ce qu'ils veulent, mais les modèles ne comprennent pas les consignes formulées en langage créatif ordinaire ; des résultats cohérents et conformes au brief dépendent encore de la structure du prompt, des prompts négatifs et d'une formulation spécifique à chaque modèle qui s'interposent entre le brief et le résultat.
- **Les meilleurs modèles d'IA sont dispersés et difficiles à faire tourner** — de puissants modèles d'IA pour l'image, l'édition, la 3D et la vidéo sortent en permanence chez différents fournisseurs et dans différents formats ; mettre en place chacun d'eux (empaquetage, GPU, quantification, mise à l'échelle) constitue à lui seul un projet d'ingénierie complet.
- **L'édition et la 3D sont des mondes distincts** — l'inpainting, l'outpainting, la recoloration, les éditions guidées par référence et la transformation d'un concept 2D en modèle 3D texturé nécessitent normalement chacun leurs propres outils, API et spécialistes.
- **Rester fidèle à votre charte est un travail manuel** — faire en sorte que chaque asset respecte votre apparence établie implique généralement de surveiller chaque génération à la main.

### 📝 La solution

ArtSmoker est un studio créatif auto-hébergé qui place les meilleurs modèles génératifs d'aujourd'hui derrière une interface unique pensée pour les artistes — conçu spécifiquement pour la production d'assets de jeux vidéo, et tout aussi à l'aise dans le cinéma, la publicité, le e-commerce, l'édition et toute équipe qui vit de contenu visuel original.

- **Décrivez-le en langage naturel** — ArtSmoker gère la décomposition des prompts, leur amélioration et l'optimisation spécifique à chaque modèle en coulisses. Un **Concepteur de prompts** guidé vous permet de façonner chaque élément visuel — sujet, scène, éclairage, couleur — avec des contrôles verrouiller/varier pour explorer des directions véritablement différentes sans perdre ce qui fonctionne déjà.
- **Fidèle à votre charte par défaut** — fournissez à ArtSmoker votre art existant et ses modèles de vision apprennent votre identité visuelle, de sorte que chaque asset produit correspond à l'apparence et à l'atmosphère de votre projet.
- **2D, édité et en 3D — de bout en bout** — générez, puis affinez sur place avec l'inpainting, l'outpainting, la recoloration, le rechercher-remplacer et les éditions guidées par référence ; transformez n'importe quel asset 2D en un **modèle 3D entièrement texturé et adapté au moteur de jeu** qui s'intègre directement dans Unity, Unreal ou Blender — sans modélisation manuelle, dépliage UV ni peinture de textures. Plus de la vidéo cinématique et un studio de chat multi-modèle pour l'idéation.
- **Chaque modèle, en un clic** — utilisez les derniers modèles hébergés à travers les régions, ou déployez des modèles open source sélectionnés (p. ex. Qwen-Image, FLUX.2, HunyuanImage, TripoSG, TRELLIS.2) sur vos propres GPU en un seul clic — empaquetage, quantification, mise à l'échelle automatique et suivi des tâches entièrement pris en charge, chaque modèle validé de bout en bout avant sa publication.
- **Fonctionne où vous le voulez — et votre IP reste la vôtre** — installez-le sur le poste d'un seul artiste ou sur une instance partagée pour toute l'équipe ; **aucun GPU personnel requis** (les calculs lourds s'exécutent sur des services AWS managés, ou sur des endpoints à mise à l'échelle automatique qu'ArtSmoker démarre et ramène à zéro pour vous). Il ne se connecte qu'à votre propre compte AWS — œuvres, prompts, styles et assets générés restent dans votre environnement, rien ne part vers des services tiers, et vous conservez la pleine propriété de votre IP créative.

**Modèles Amazon Bedrock** — tout ce que **Synchroniser depuis AWS** trouve dans votre compte, p. ex. Claude Sonnet/Opus pour l'ingénierie de prompts et le chat, Stable Diffusion 3.5 Large, Stable Image Ultra et Stable Image Core pour les images, les services Stability AI pour l'édition d'images, Luma AI Ray pour la vidéo, et un large éventail de LLM de chat de nombreux fournisseurs pour le Studio de Chat. **Modèles auto-hébergés** — un catalogue sélectionné, livré avec chaque version et déployé sur Amazon SageMaker, p. ex. Qwen-Image (text-to-image) et Qwen-Image-Edit (édition guidée par référence + par instruction, Apache-2.0), HunyuanImage 3.0 (BF16/NF4), FLUX.2, FLUX.1, TripoSG et TRELLIS.2 (image-vers-3D) — et il est extensible, vous pouvez donc ajouter les vôtres.

<a id="about-model-names"></a>
> [!NOTE]
> **À propos des noms de modèles.** ArtSmoker propose tous les modèles que **Synchroniser depuis AWS** trouve dans votre compte et vos Régions, plus le catalogue auto-hébergé livré avec chaque version. Les noms de modèles de ce README sont des **exemples en date d'octobre 2026** — AWS lance et retire fréquemment des modèles, et ce que vous pouvez utiliser dépend de votre compte, de vos Régions et de vos accès aux modèles. L'application fait autorité sur ce qui est disponible aujourd'hui.

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
- Le Studio de Chat transmet les prompts directement au LLM (sans traduction), car des modèles comme Claude sont nativement multilingues
- Le texte du Studio de Texte reste dans votre langue (il est rendu tel quel sur l'image)
- Toutes les pré-vérifications de modération et le filtrage de contenu s'appliquent sur le prompt traduit en anglais, par souci de cohérence

## 📌 1. Fonctionnalités

ArtSmoker fonctionne en deux modes — **autonome** (aucune configuration de style ou de thème nécessaire, décrivez et générez simplement) et **guidé par le style** (téléchargez votre art existant, et chaque génération correspond à votre identité visuelle). Les deux modes utilisent les mêmes studios et le même pipeline de génération.

### 📝 Mode autonome (démarrage rapide)

Aucune configuration de style ou de thème nécessaire — ouvrez le Studio Image, le Studio Vidéo ou le Studio de Texte et commencez à créer immédiatement.

1. **Décrivez ce dont vous avez besoin** — saisissez un prompt comme « hospital building » ou « fire mage character », ou utilisez l'entrée vocale. L'IA décompose votre idée en composants visuels, l'améliore avec des optimisations spécifiques au modèle, et respecte votre intention créative grâce à des contrôles intelligents verrouiller/varier. Écrivez dans n'importe quelle langue — les prompts non anglais sont traduits automatiquement.
2. **Choisissez vos modèles et paramètres** — multi-sélection parmi tous les modèles text-to-image disponibles (Amazon Bedrock + auto-hébergés sur SageMaker), choisissez les dimensions, le niveau de qualité et la région. Cochez plusieurs modèles pour une comparaison côte à côte, ou un seul pour une génération ciblée. L'estimation des coûts se met à jour en temps réel.
3. **Obtenez des options véritablement différentes** — le système génère jusqu'à 5 concepts créatifs distinctement différents (variant la tenue, l'ambiance, l'éclairage, la composition — pas seulement l'angle de caméra), chacun avec jusqu'à 5 variations de graine (25 images au total). Les détails spécifiés par l'utilisateur sont verrouillés ; les détails inférés par l'IA sont variés audacieusement. Un contrôle **Graine (seed)** visible rend les lots reproductibles — la même graine, avec le même prompt final et les mêmes réglages, régénère les mêmes images, et cliquer sur un résultat reprend sa graine pour ne modifier qu'un paramètre et bifurquer depuis un favori.
4. **Éditez et affinez** — utilisez l'inpainting, l'outpainting, l'effacement, la recherche et remplacement ou la recoloration directement dans la visionneuse d'assets. Chaque modification crée une nouvelle version — l'original est toujours préservé.
5. **Téléchargez des fichiers prêts pour le jeu** — PNG avec fond transparent + SVG, nommés de manière descriptive (par exemple `hospital-building_opt2_var3.png`). Les vidéos s'exportent en MP4.

### 📝 Mode guidé par le style (correspondre à votre style artistique et thème)

Pour les équipes qui veulent que chaque asset généré corresponde à un style artistique existant — téléchargez des images de référence et laissez l'IA apprendre d'abord votre identité visuelle.

1. **Téléchargez l'art de votre jeu** — importez des images de référence depuis des répertoires locaux (scan récursif, liens symboliques pour éviter la duplication) ou des buckets S3 (listing récursif avec pagination). **Le dédoublonnage intelligent** s'exécute automatiquement — supprime les variantes de rotation (barrel_N/E/S/W.png ne conserve que barrel_S.png) et les frames d'animation (Idle0-Idle8 ne conserve que Idle). Par exemple, un pack d'assets isométriques de 747 fichiers est dédupliqué à environ 99 objets uniques. Formats supportés : .png, .jpg, .jpeg, .gif, .bmp, .webp, .tiff, .tif, .tga, .ico, .svg, plus extraction automatique de textures depuis les modèles 3D (.glb, .gltf).
2. **L'IA apprend votre style** — analyse en deux phases avec détection de cohésion : d'abord, une vérification rapide détermine si votre collection est unifiée, structurellement cohérente ou diverse. Ensuite, une analyse approfondie de l'ensemble complet de références produit un profil de style riche en métadonnées — palettes de couleurs, épaisseurs de traits, motifs d'éclairage, règles de composition et conventions de production. Si vous fournissez des indications de génération, l'IA les reçoit comme « Artist's Guidance » afin que l'analyse comprenne votre intention, pas seulement ce qui est visible.
3. **Générez avec le style appliqué** — lorsque vous sélectionnez un style dans le Studio Image, chaque prompt est automatiquement enrichi avec les directives visuelles de votre style. Un prompt comme « hospital building » devient une instruction de génération détaillée incluant la palette de couleurs, les conventions de perspective et le style de rendu de votre jeu.
4. **Tout du mode autonome s'applique** — options multiples, comparaison de modèles, édition, versionnement et téléchargements prêts pour le jeu fonctionnent de la même manière, désormais guidés par votre style artistique.

> [!NOTE]
> Tout le contenu généré est produit par des modèles d'IA et dépend des prompts et des références que vous fournissez. Veuillez consulter la [clause de non-responsabilité](#disclaimer) concernant la qualité du contenu, la propriété intellectuelle et les conditions de service applicables avant d'utiliser des assets générés en production.

### 📝 1.1 Aperçu des fonctionnalités

- 🎨 **Bibliothèque de styles** — Téléchargez votre art, l'IA apprend votre identité visuelle
- 🖼️ **Studio Image** — Génération d'images avec options x variations, workflow de prompt guidé en 3 étapes
- 🎨 **Concepteur de prompts** — L'IA décompose votre prompt en composants visuels éditables (sujet, scène, éclairage, couleurs) avec bascules verrouiller/varier par champ, intégration du style et classification intelligente du type d'asset. Image photoréaliste, Personnage, Environnement, et plus
- 🗂️ **Collections (génération d'ensembles)** — transformez UN prompt **ou une image de référence** en un **ensemble cohérent d'assets distincts** (« un jeu d'échecs de style viking », « 20 personnages JRPG »). Activez le sélecteur **Collection** dans le Studio Image — depuis l'onglet **Inspiration texte** (piloté par votre prompt) ou l'onglet **Inspiration image** (le *look* de l'image de référence pilote la direction artistique) — et un **Concepteur de collection** dédié décompose votre brief en une **direction artistique** partagée plus un **roster** de sujets distincts dans le thème — chacun étant un **lot** avec son propre prompt éditable et indépendant du modèle. Modifiez la direction artistique pour recomposer tout l'ensemble ; verrouillez, régénérez, ajoutez ou supprimez des lots individuels ; puis générez-les tous d'un coup (options × variations chacun), avec une estimation en direct du design et du coût projeté. **Choisissez un seul modèle pour un ensemble homogène, ou plusieurs pour rendre chaque lot sur chacun** (comparaison inter-modèles). Une cohésion optionnelle **Ancrage héros** / **Ancrage référence** verrouille le style de l'ensemble sur une image choisie/fournie. Les collections apparaissent comme **une seule carte** dans la Galerie ; le visualiseur de collection permet à chaque lot d'ouvrir la visionneuse d'assets habituelle (options / variations / versions, retouches, exports et 3D — exactement comme pour une image seule, plus la **lignée de collection** du lot) ; vous pouvez **épingler la version** représentant chaque lot, **passer tout l'ensemble en 3D** d'un coup (ou seulement les lots ou images choisis) et voir chaque modèle arriver dans la vue **Modèles 3D** propre à la collection, **télécharger** tout l'ensemble ou une sélection en un seul zip — les mêmes fichiers qu'une image seule (PNG, SVG et détourages sans arrière-plan) ou ses modèles 3D avec les mêmes presets moteur, LOD, collisions et packing de textures — ou **recharger toute la collection dans le Studio Image** pour la revoir et la régénérer. Les modèles 3D d'une collection restent à l'intérieur de celle-ci — le **filtre 3D** de la Galerie affiche la carte de la collection avec son badge « 3D n/m ». Une collection chargée s'affiche **directement dans la zone de résultats du Studio Image** (mêmes cartes, aperçu et panneau de prompt qu'une image seule, regroupés par lot), et rouvrir le Concepteur de collection montre **le design enregistré à l'identique** (direction artistique, prompt de chaque lot et prompts réellement reçus par chaque modèle) — rien n'est régénéré sans votre demande, et **avant toute dépense** le type d'asset est vérifié par rapport à votre prompt (un ensemble = Personnages ou Ressources de jeu) — pour ne jamais payer un ensemble entier dans le mauvais cadrage
- 🎬 **Studio Vidéo** — Text-to-video avec guidance de prompt spécifique au modèle (p. ex. direction en langage naturel pour Luma Ray), image-to-video, boucle
- ✍️ **Studio de Texte** — Superpositions de texte conçues par l'IA avec sélecteur de polices
- 💬 **Studio de Chat** — Chat LLM multi-modèle avec streaming, Markdown, coloration syntaxique, vision, sessions, compactage de contexte
- 📁 **Galerie unifiée** — Disposition en maçonnerie (masonry) qui affiche chaque asset à son véritable ratio (portrait, carré, paysage — jamais recadré). Parcourez images + vidéos, filtre par média (Tous les médias / Images 2D / Modèles 3D / Vidéo), recherche, horodatages complets date-heure-fuseau, téléchargement, suppression. Les assets qui possèdent déjà un modèle 3D généré portent un **badge 3D**, et le filtre **Modèles 3D** ne fait remonter que ceux-là
- 📥 **Importer une image** — Intégrez une image existante (tout format) dans la galerie comme un asset à part entière. Convertie automatiquement en PNG, associée au type d'asset que vous choisissez, et immédiatement éditable et prête pour la 3D — tout (versionnage, édition, image-vers-3D) fonctionne exactement comme pour une image générée
- ✏️ **Édition d'images** — Inpainting, outpainting, effacement, rechercher-remplacer, recoloration (dans la visionneuse d'assets). Chaque mode dispose d'un bouton IA **Générer un prompt** : un modèle de vision lit l'image + son prompt d'origine et propose un prompt d'édition adapté à ce mode et au modèle d'édition sélectionné (p. ex. une légende descriptive pour les éditeurs Stability, une instruction pour Qwen-Image-Edit). Extension/Outpaint affiche un aperçu en direct de l'agrandissement du cadre avec des règles en pixels pour voir exactement de combien le canevas s'étendra avant de valider. Les éditeurs à instructions (p. ex. Qwen-Image-Edit) prennent en charge **les cinq modes sans masque** — y compris une véritable extension du canevas : ArtSmoker pré-remplit le canevas, fait compléter uniquement la nouvelle zone par le modèle, puis réintègre vos pixels d'origine intacts. Chaque version éditée affiche **les deux étiquettes de modèle** — le générateur d'origine et l'éditeur qui a produit cette version
- 📤 **Export et découpes** — Artefacts d'export par version dans la visionneuse d'assets : un détourage PNG transparent (fond supprimé) plus de vraies vectorisations SVG (avec et sans fond). La suppression d'arrière-plan se choisit à chaque exécution : **gratuite sur l'appareil** (rembg/u2net, aucun coût cloud) ou le suppresseur **payant Amazon Bedrock** — le même choix est proposé lors de la préparation des images pour la génération 3D
- 🔄 **Progression en temps réel** — Streaming SSE avec visibilité des tentatives/limitations
- 🛡️ **Modération intelligente** — Test canari, changement automatique de modèle, réécriture assistée par l'IA
- ⚙️ **Registre des modèles** — Interface d'administration organisée par studio (Image, Vidéo, Chat, Texte, Partagé), découverte Bedrock, support des modèles personnalisés
- 📝 **Modèles de Prompt** — 28 prompts directifs LLM éditables, amélioration assistée par l'IA, validation de variables avec correction automatique
- 📦 **Versionnage des assets** — Édition sur place avec historique des versions (v1, v2…), navigation entre versions et suppression par version : ne supprimez qu'une seule version (les autres gardent leurs numéros), la visionneuse bascule sur la version précédente — supprimer la dernière version retire tout l'asset
- 💰 **Suivi des coûts** — Dépenses AWS estimées par requête, par session, par asset, calculées à partir des tarifs AWS en direct par région ; les modèles auto-hébergés affichent le tarif horaire de fonctionnement de l'instance GPU + le temps de génération typique (et non un prix par image trompeur)
- 🌐 **i18n en 9 langues** — Traduction complète de l'UI (EN, JA, ZH, KO, HI, RU, FR, ES, DE), détection automatique des prompts non anglais (l'UI anglaise saute entièrement la détection), aperçu bilingue
- 🔍 **Support des modèles personnalisés** — Découverte automatique des modèles Bedrock fine-tunés, importés et déployés
- 🔧 **Modèles auto-hébergés — Déploiement en 1 clic** — Parcourez un catalogue organisé de modèles open source pré-testés (dans cette version, p. ex. Qwen-Image, Qwen-Image-Edit, HunyuanImage 3.0, FLUX.2, FLUX.1, TripoSG, TRELLIS.2), choisissez une instance GPU, et cliquez sur Déployer. ArtSmoker gère tout : empaquetage du gestionnaire d'inférence, configuration de la quantification, sélection du bon toolkit CUDA, mise en place de l'auto-scaling, enregistrement des alarmes CloudWatch, et câblage du suivi asynchrone des tâches. Chaque modèle du catalogue est validé de bout en bout — du démarrage à froid à la génération jusqu'à la livraison en galerie — pour que vous n'ayez pas à déboguer les pilotes GPU, les dépassements de mémoire ou la compatibilité des conteneurs. Supporte BF16 + FlashInfer pour la meilleure qualité, NF4 pour l'efficacité des coûts, détection automatique multi-GPU, mise à l'échelle automatique à zéro (0$ en veille), et le même modèle fonctionne sur différents types d'instances sans reconfiguration
- 🧊 **Génération Image-to-3D** — Convertissez n'importe quelle image de type Ressource de jeu ou Personnage en un maillage 3D texturé (GLB) en un clic. La synthèse multi-vues + le baking de textures produit des assets entièrement texturés, adaptés au moteur de jeu. Visionneuse 3D interactive avec orbite/zoom/panoramique
- 🩹 **Complétion intelligente de la source pour la 3D** — l'image-to-3D ne peut construire que ce qui est visible ; un personnage recadré (jambes coupées) donne un maillage sans jambes. Avant la génération, ArtSmoker vérifie l'image source par vision et, si elle est recadrée, **propose de la compléter** par outpainting (invite suggérée par l'IA, entièrement modifiable) — affiche l'avant/après, réexamine le résultat, permet d'étendre encore ou d'abandonner, et l'enregistre comme nouvelle version d'image. Optionnel et non bloquant ; les images bien cadrées sont générées directement
- 🔄 **Auto-Update** — Contrôle de version au démarrage + vérification périodique toutes les 24h ; mise à jour via `git` (checkout) ou par **téléchargement-et-remplacement d'une archive tarball** pour les installations sans git, puis redémarrage sur place (relance supervisée / rechargement gunicorn) ou proposition d'un bouton **Redémarrer maintenant** en un clic — n'écrase jamais vos `data/` ni votre `.env` (`ARTSMOKER_AUTO_UPDATE=false` pour désactiver)

### 📝 1.2 Captures d'écran

**Studio Image** — Paramètres à gauche avec liste déroulante multi-sélection de modèles, type d'asset, dimensions et options de post-traitement. Workflow de prompt en 3 étapes à droite avec les boutons Concepteur de prompts et Générer le Prompt Amélioré. Déclaration IP et estimation des coûts en bas.

![Studio Image — Paramètres, workflow de prompt et contrôles de génération](docs/images/image-studio-top.png)

**Studio Image — Résultats de génération** — Le prompt amélioré est affiché au-dessus, les résultats de comparaison multi-modèle en dessous. Chaque modèle génère indépendamment avec une optimisation du prompt spécifique à chaque modèle. Les résultats affichent le nom du modèle, les dimensions et le coût de génération.

![Studio Image — Prompt amélioré et résultats de génération](docs/images/image-studio-results.png)

**Studio Image — Comparaison de modèles** — Grille de comparaison côte à côte de tous les modèles sélectionnés (8 affichés — Amazon Bedrock et auto-hébergés à égalité). Chaque carte d'option porte sa propre bande de variations ; le prompt négatif propre au modèle est affiché pour l'option sélectionnée. Les bascules de post-traitement (Supprimer l'arrière-plan, Convertir en SVG, Agrandir (créatif)) s'appliquent aux résultats existants sans régénération.

![Studio Image — Grille de comparaison multi-modèle avec variations](docs/images/image-studio-comparison.png)

**Inspiration image (guidée par référence)** — Déposez 1 à 3 images de référence, dites ce que vous voulez, et choisissez leur usage : **Fidèle à la référence** (édition fidèle au pixel sur un modèle d'édition d'images déployé) ou **Inspiré de la référence** (une IA de vision écrit le prompt enrichi — fonctionne avec n'importe quelle sélection de modèles, options et variations). Le prompt dérivé est prévisualisé et entièrement modifiable avant la génération.

![Inspiration image — images de référence, instruction et prévisualisation modifiable du prompt enrichi](docs/images/image-inspiration.png)

**Inspiration image — Résultats** — La référence devient une nouvelle création (ici, une caricature dessinée à partir de la photo de référence), avec le prompt exact envoyé au modèle et le coût par image enregistrés.

![Inspiration image — caricatures générées à partir d'une image de référence](docs/images/image-inspiration-results.png)

**Concepteur de prompts** — L'IA décompose votre prompt en composants visuels éditables (Sujet, Scène, Composition, Éclairage, Style & Couleurs). Chaque champ peut être édité individuellement avec des contrôles verrouiller/varier pour des options créatives véritablement distinctes.

![Concepteur de prompts — Décomposition visuelle structurée avec champs éditables](docs/images/prompt-designer-top.png)

**Concepteur de prompts — Palette de couleurs** — Palettes de couleurs nommées avec échantillons hexadécimaux, mots-clés de style et contrôles de niveau de qualité. L'IA apprend votre identité visuelle et l'applique de manière cohérente à toutes les générations.

![Concepteur de prompts — Palette de couleurs, mots-clés de style et contrôles de qualité](docs/images/prompt-designer-bottom.png)

**Bibliothèque de styles** — Téléchargez l'art existant de votre jeu, l'IA analyse le style visuel et produit un guide de prompts riche en métadonnées. Les images de référence sont affichées avec l'analyse IA complète et le profil de style JSON.

![Bibliothèque de styles — Analyse de style IA avec images de référence](docs/images/style-library-top.png)

![Bibliothèque de styles — Images de référence, options d'importation et données d'analyse](docs/images/style-library-bottom.png)

**Galerie** — Vue unifiée de toutes les images et vidéos générées avec filtre par type de média, filtre par style, recherche et tri. Cliquez sur n'importe quel asset pour ouvrir la vue complète. Le bouton **Importer une image** ajoute une image existante à la galerie — choisissez un type d'asset (Personnage/Ressource de jeu activent la 3D), elle est convertie en PNG et rendue instantanément éditable et prête pour la 3D.

![Galerie — Grille d'assets générés avec filtres](docs/images/gallery.png)

**Visionneuse d'assets** — Aperçu en taille réelle avec interface à onglets (PNG, Modifier, Export et découpes, Métadonnées, Modèle 3D), barre de versions de l'image et téléchargement direct PNG/SVG. Contrôles zoom/ajustement/mesure sur l'image composée en damier.

![Visionneuse d'assets — Aperçu en taille réelle avec options de téléchargement](docs/images/asset-viewer.png)

**Visionneuse d'assets — Édition d'images** — Cinq modes d'édition : Retouche, Effacer, Extension, Remplacer, Recolorier. Ici : **Extension**, avec la règle de mesure, les valeurs en pixels par côté et le bouton ✨ Générer un prompt, qui lit l'image et écrit le prompt d'édition pour vous. L'historique des versions est préservé — les originaux ne sont jamais écrasés.

![Visionneuse d'assets — Extension avec règle de mesure et prompt suggéré par l'IA](docs/images/asset-viewer-edit.png)

**Visionneuse d'assets — Export et découpes** — Des artefacts par version, prêts pour votre jeu, moteur ou outil de design : SVG vectoriel de l'image complète, découpe PNG sans arrière-plan et découpe SVG. La suppression d'arrière-plan s'exécute gratuitement sur votre machine (un traitement payant Amazon Bedrock est optionnel).

![Visionneuse d'assets — Export et découpes avec SVG vectoriel et découpes sans arrière-plan](docs/images/asset-viewer-export-cutouts.png)

Après un passage d'outpainting (v3 ci-dessous), le même onglet régénère les trois artefacts pour la version corps entier améliorée.

![Visionneuse d'assets — Export et découpes pour la version corps entier après outpainting](docs/images/asset-viewer-export-cutouts-outpainted.png)

**Visionneuse d'assets — Métadonnées** — La généalogie complète du prompt (votre prompt → décomposition du Concepteur de prompts → prompt recomposé → prompt raffiné adapté au modèle), les détails de génération, la ventilation des coûts et l'historique complet des versions.

![Visionneuse d'assets — Métadonnées avec généalogie complète du prompt et historique des versions](docs/images/asset-viewer-metadata.png)

*Les captures d'écran du pipeline 3D — génération, vérification de la source, export adapté au moteur de jeu et variantes — sont présentées plus bas, dans la section 1.9 (Génération de modèle 3D), aux côtés des fonctionnalités qu'elles illustrent.*

**Studio Vidéo** — Paramètres à gauche (modèle, mode de génération, durée, région, estimation des coûts), prompt à droite. Propose les modèles vidéo que **Synchroniser depuis AWS** découvre dans votre compte — p. ex. Luma AI Ray (rapports d'aspect, boucle).

![Studio Vidéo — Paramètres et prompt](docs/images/video-studio.png)

![Studio Vidéo — Génération en cours avec prompt amélioré par l'IA](docs/images/video-studio-generating.png)

![Studio Vidéo — Vidéo terminée avec vignette et vidéos récentes](docs/images/video-studio-completed.png)

**Lecteur vidéo** — Cliquez sur une vidéo pour la lire en ligne avec toutes les métadonnées (prompt original, prompt amélioré par l'IA, modèle, durée, région).

![Lecteur vidéo — Lecture d'une vidéo générée avec métadonnées](docs/images/video-player.png)

### 📝 1.3 Génération à deux niveaux

Pour chaque prompt, l'IA crée des **Options** — des interprétations de design fondamentalement différentes (par exemple pour « a warrior » : berserker viking, samouraï japonais, guerrier tribal, cyber-soldat, hoplite grec). Pour chaque option, le modèle d'image produit des **Variations** — différentes graines aléatoires donnant des différences visuelles subtiles. Cela offre aux artistes une large palette créative pour faire leur choix.

### 📝 1.4 Sélection multi-modèle

Le menu déroulant des modèles prend en charge la **multi-sélection par cases à cocher** — choisissez n'importe quelle combinaison de modèles pour une seule génération :

- **Modèle unique** — cochez un modèle pour une génération ciblée (le plus rapide, le moins cher)
- **Plusieurs modèles** — cochez 2-3 modèles spécifiques pour une comparaison ciblée (ex : SD 3.5 + FLUX.2 uniquement)
- **Tous les modèles disponibles** — le toggle en bas sélectionne/désélectionne tous les modèles activés pour une comparaison côte à côte complète

Chaque modèle s'exécute indépendamment : si des modèles plus stricts bloquent le prompt, vous obtenez quand même les résultats des modèles qui l'ont accepté, avec des étiquettes de statut claires (succès, bloqué par la modération, ou échec) sur chaque carte d'option. L'estimation des coûts se met à jour en temps réel au fur et à mesure que vous cochez/décochez les modèles.

Un toggle optionnel **« Prompts optimisés par modèle »** adapte le prompt aux forces de chaque modèle — les prompts sont réécrits par modèle (ex : boosters de qualité pour SD 3.5, langage naturel pour FLUX.2, repères de rendu de texte de premier plan pour Qwen-Image).

### 📝 1.5 Génération guidée par référence

Au-delà de l'écriture d'un prompt à partir de zéro, vous pouvez générer **à partir de 1 à 3 images de référence plus une instruction** — choisissez le mode avec le contrôle segmenté en haut de la zone de prompt du Studio Image :

- **Fidèle à la référence** — conservez le sujet, le produit ou le personnage de votre référence et changez le reste (thème, arrière-plan, tenue, éclairage) exactement comme le dit votre instruction. Idéal pour des personnages cohérents ou des photos de produit à travers plusieurs scènes. Ce mode s'exécute sur un éditeur à instructions auto-hébergé (dans cette version, Qwen-Image-Edit) et apparaît **une fois qu'il est déployé** — s'il ne l'est pas, ArtSmoker vous dirige directement pour le déployer depuis l'onglet Modèles Personnalisés (un clic, même flux que les pipelines 3D). Sûr pour un usage commercial (Apache-2.0).
- **Inspiré de la référence** — l'IA de vision d'ArtSmoker lit vos référence(s) et votre instruction, rédige un prompt amélioré (montré d'abord), puis génère avec vos modèles text-to-image habituels. **Toujours disponible** — aucun déploiement nécessaire. Idéal pour emprunter une apparence, une palette ou une composition sans copier le sujet.

- **Remixer la référence** — l'image-to-image classique piloté par la force : les *pixels* de votre référence vont directement dans un modèle Bedrock que le registre signale comme compatible (p. ex. Stable Diffusion 3.5 Large, Stable Image Ultra), avec un **curseur de force** : subtil conserve presque intacts la composition, la palette et l'ambiance ; audacieux la traite comme une inspiration libre. Avec plus d'une Option, cela devient une **échelle de forces** — une carte par force, du subtil à l'audacieux, côte à côte. *Conserve la mise en page, pas l'identité* (les visages et produits dérivent — utilisez Fidèle à la référence pour un travail exact). La taille de sortie suit l'image de référence. **Toujours disponible** — aucun déploiement, aucun appel d'analyse visuelle.

Les trois modes requièrent une instruction pour que vous gardiez le contrôle de ce à quoi sert la référence. La génération guidée par référence est distincte de la Bibliothèque de styles (qui analyse de nombreuses images en un profil de style réutilisable) — utilisez-la pour des générations ponctuelles pilotées par l'image.

### 📝 1.6 Studio Vidéo

Générez des vidéos et animations propulsées par l'IA à partir de prompts textuels. Le Studio Vidéo propose les modèles vidéo que **Synchroniser depuis AWS** découvre dans votre compte (voir [À propos des noms de modèles](#about-model-names)). Par exemple, **Luma AI Ray v2** :

| Fonctionnalité | Luma Ray v2 |
|----------------|-------------|
| **Durée max** | 9 secondes |
| **Résolution** | 720p / 540p |
| **Rapports d'aspect** | 7 options (1:1, 16:9, 9:16, etc.) |
| **Image-to-video** | Oui (frame de départ + de fin) |
| **Vidéo en boucle** | Oui |
| **Prix** | ~$1.50/s |

**Fonctionnement :**
1. Sélectionnez un modèle vidéo et configurez la durée, le rapport d'aspect, la région
2. Saisissez un prompt — l'IA l'enrichit avec un vocabulaire cinématographique, des mouvements de caméra et des repères de cohérence temporelle
3. Cliquez sur Générer — la tâche s'exécute de manière asynchrone via `StartAsyncInvoke`, la sortie va dans votre bucket S3 configuré
4. Interrogation du statut toutes les 5 secondes — à l'achèvement, la vignette est extraite (via ffmpeg) et le MP4 est téléchargé localement (ou streamé depuis S3)
5. Les vidéos apparaissent à la fois dans la section « Vidéos récentes » du Studio Vidéo et dans la galerie unifiée

**Bucket S3 requis** : La génération vidéo envoie ses sorties vers S3. Vous pouvez configurer via Paramètres vidéo dans l'UI (parcourir les buckets existants ou en créer un nouveau), ou en créer un via CLI :

```bash
# Créer un bucket S3 pour le stockage vidéo (remplacez REGION et YOUR_ORG)
aws s3api create-bucket --bucket artsmoker-video-YOUR_ORG --region us-east-1

# Pour les régions autres que us-east-1, ajoutez le LocationConstraint :
aws s3api create-bucket --bucket artsmoker-video-YOUR_ORG --region us-west-2 \
  --create-bucket-configuration LocationConstraint=us-west-2
```

Mode de stockage : téléchargement local (par défaut) ou streaming depuis S3 à la demande.

**Amélioration des prompts vidéo** : Le LLM ajoute des mouvements de caméra (panoramique, zoom, dolly, tracking), des détails d'éclairage et des repères temporels. Comme les modèles vidéo ne supportent pas les prompts négatifs, les concepts à éviter sont intégrés naturellement dans le prompt positif.

### 📝 1.7 Studio de Chat

Une interface de chat LLM complète — comme une IA conversationnelle auto-hébergée, fonctionnant sur votre propre compte AWS sans accès tiers aux données.

**Tous les modèles de chat que trouve « Synchroniser depuis AWS » dans votre compte** (voir [À propos des noms de modèles](#about-model-names)) — p. ex. Claude (Sonnet, Opus, Haiku), Amazon Nova, Meta Llama, Mistral, Cohere, Qwen, DeepSeek, Google Gemma et NVIDIA Nemotron — plus tous les modèles personnalisés/importés de votre compte.

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
- **Modèles de prompts système** — Assistant général, Expert en programmation, Rédacteur créatif, Concepteur de jeux, Analyste de données, Rédacteur technique
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
| **Image photoréaliste** *(par défaut)* | Cadrage naturel, de type photographique — le sujet dans un environnement réel adapté au contexte. | Perspective de caméra réelle : hauteur d'œil, faible profondeur de champ pour les portraits, grand angle pour les paysages. | Dirigé dans le langage de la photographie (heure dorée, softbox de studio, sensation de focale) avec des imperfections naturelles — texture de peau, plis de tissu, patine. Jamais de vocabulaire d'illustration ni de jargon de moteur de rendu. |
| **Ressource de jeu** | Objet unique isolé sur fond transparent. Pas de scène, pas de texte, pas d'UI. | Vue frontale ou isométrique, l'objet remplit 70-80% du cadre. | Bords nets et propres pour la suppression de fond, éclairage cohérent depuis le haut-gauche, pas d'ombres au sol. Conçu pour être composé avec d'autres assets de jeu à différentes échelles. |
| **Personnage** | Figure en pied ou 3/4, isolée sur fond propre. Un seul personnage. | Le personnage remplit 60-75% de la hauteur, de la tête aux pieds, légèrement décentré. | Silhouette lisible et forte (identifiable par la silhouette seule), pose expressive transmettant la personnalité, traits du visage et détails du costume clairs. |
| **Icône** | Symbole unique, gras et reconnaissable, centré avec un padding généreux. Simplicité maximale. | Vue frontale ou légère inclinaison 3/4, espace respirant aux bords. | Doit être clairement lisible à 64x64 pixels. Contraste élevé, 3-5 couleurs maximum, formes audacieuses, pas de lignes fines ni de détails fins. |
| **Bannière marketing** | Illustration scénique complète avec composition dramatique. Zone de texte propre réservée sur un côté — pas de texte rendu ni de typographie. | Sensation cinématique large, caméra reculée pour montrer une scène. | Couleurs riches et saturées, éclairage dramatique (rim light, rayons volumétriques), profondeur de champ. L'IA est explicitement instruite de NE PAS rendre de texte ; la zone réservée au texte est laissée propre pour la superposition en post-production dans les outils de design (Figma, Canva, etc.). |
| **Environnement** | Paysage complet avec couches de profondeur avant-plan/milieu/arrière-plan et lignes directrices. | Plan d'ensemble large, horizon au tiers supérieur ou inférieur. | Perspective atmosphérique (objets distants plus clairs/brumeux), narration environnementale par les détails, éclairage d'ambiance. |

Cela compte à chaque étape :

- **Bouton « Générer le Prompt Amélioré »** — Quand vous cliquez dessus, l'IA utilise le type d'asset pour reformuler votre brief en un prompt de génération détaillé, combinant vos mots avec les directives de style et les directives du type d'asset. Votre intention explicite prévaut toujours sur les paramètres par défaut du style. Vous pouvez examiner la version composée avant de générer.
- **Génération de concepts** — Lors de la génération d'options multiples, l'IA crée N interprétations de design différentes qui respectent toutes les règles structurelles du type d'asset. Une option Personnage a toujours une silhouette lisible ; une option Bannière marketing a toujours une zone de texte sans texte rendu.
- **Le résultat** — Deux images du même prompt mais de types d'assets différents ne se ressembleront en rien. Une Ressource de jeu « warrior » est un sprite de personnage unique centré. Une Bannière marketing « warrior » est une scène de bataille épique avec une zone propre pour la superposition du titre.

### 📝 1.9 Génération de modèles 3D (Image-to-3D)

Générez des maillages 3D entièrement texturés à partir de n'importe quelle image 2D — directement dans la visionneuse d'assets. Sélectionnez une image **Ressource de jeu** ou **Personnage**, ouvrez l'onglet **Modèle 3D**, et cliquez sur Générer. Le résultat est un GLB adapté au moteur de jeu que vous pouvez orbiter, zoomer et télécharger — sans modélisation manuelle, dépliage UV ni peinture de texture.

**Le résultat final, d'abord :** un personnage généré par ArtSmoker, exporté en FBX adapté au moteur de jeu et ouvert dans un Blender standard — la chaîne de LOD (LOD0–LOD3) intacte dans l'Outliner, textures liées, sans re-rigging ni correction manuelle. Tout ce qui suit montre comment y parvenir à partir d'un prompt texte.

![FBX ArtSmoker ouvert dans Blender — hiérarchie du groupe LOD intacte avec textures liées](docs/images/fbx-in-blender.png)

**Le modèle généré — orbitez, inspectez, téléchargez :**

![Génération de modèle 3D — le maillage du soldat généré vu sous plusieurs angles dans la visionneuse 3D interactive](docs/images/3d-model-result.png)

Une seule image 2D de personnage (à gauche, dans l'onglet PNG) devient un maillage 3D entièrement texturé que vous pouvez faire pivoter librement dans le navigateur. L'onglet **Modèle 3D** liste désormais aussi les **modèles et outils** exacts utilisés pour produire chaque asset (modèle de géométrie, backend de texturation, type de sortie, instance et paramètres de génération) — persistés dans les métadonnées de l'asset pour une traçabilité complète.

**Génération** — L'onglet Modèle 3D de la visionneuse d'assets : choisissez l'endpoint du pipeline déployé, le niveau de qualité (avec temps et coût estimés) et les paramètres avancés. Le panneau de licence affiche les conditions de chaque pipeline, et **Améliorer la source** vérifie visuellement l'image avant de consommer du temps GPU.

![Génération de modèle 3D — Paramètres et génération dans la visionneuse d'assets](docs/images/3d-model-generation.png)

**Améliorer la source** — Avant la génération, ArtSmoker mesure la silhouette du sujet et signale les recadrages (ici : coupé au bord inférieur), en suggérant les valeurs d'extension et un prompt d'outpainting écrit par l'IA — étendez, remplissez, ou utilisez l'image telle quelle.

![Vérification de la source 3D — détection automatique de recadrage avec extension suggérée](docs/images/3d-source-review.png)

**Deux pipelines — à vous de choisir.** ArtSmoker propose deux façons de transformer une image en modèle 3D texturé. Déployez l'un (ou les deux) depuis l'onglet Modèles Personnalisés ; lorsque les deux sont actifs, vous choisissez par génération dans la visionneuse d'assets — chacun affiche son coût est., son temps et sa licence pour que vous décidiez en connaissance de cause :

| Pipeline | Fonctionnement | Licence | Usage commercial | Idéal pour |
|----------|----------------|---------|------------------|------------|
| **TripoSG + backend de texture** | TripoSG construit le maillage ; un backend de texturation choisi (TRELLIS.2 / Hunyuan3D-Paint) le peint | selon le backend (ci-dessous) | selon le backend | Combiner géométrie + un texturateur précis |
| **TRELLIS.2 (pipeline complet)** | Un seul modèle génère **à la fois** la géométrie et la texture PBR (SLAT) | Modèle MIT + poids | ⚠️ **Bake non commercial** — l'export du maillage importe en dur `nvdiffrast` (NVIDIA 1-Way Commercial) ; à examiner avant tout usage commercial | Voie la plus simple ; prototypes et travaux non commerciaux |

> **Usage commercial :** la voie **TripoSG + backend de texture** est la route sûre pour un usage commercial — son bake utilise **Kaolin (Apache-2.0)**. Le pipeline **TRELLIS.2 complet** est sous licence MIT pour le modèle lui-même, mais son bake de maillage `o_voxel` importe en dur `nvdiffrast` (NVIDIA Source Code License, non commercial pour les utilisateurs généraux) et ne peut être remplacé sans patcher l'amont — traitez donc la sortie du pipeline complet comme non commerciale tant que vous n'avez pas levé cette dépendance. La licence + chaque dépendance sont affichées dans la boîte de dialogue de déploiement et à nouveau au moment de la génération.

**Variantes 3D** — Conservez plusieurs rendus 3D par version d'image (ici TripoSG contre le pipeline complet TRELLIS.2), basculez entre eux ou définissez le défaut à tout moment ; chaque variante enregistre les modèles et outils exacts qui l'ont produite.

![Variantes 3D — TripoSG et TRELLIS.2 côte à côte avec provenance complète](docs/images/3d-model-variants.png)

**Fonctionnement du pipeline TripoSG :**

1. **Extraction de géométrie** — un rectified flow transformer (TripoSG, 1,5 milliard de paramètres, sous licence MIT) convertit une seule image 2D en un maillage 3D haute fidélité à l'aide d'une représentation par champ de distance signée (SDF). La densité du maillage s'adapte au préréglage de qualité (jusqu'à ~1M de faces à la résolution d'octree la plus élevée) pour des détails nets sur les visages et l'équipement.
2. **Texturation** — le maillage est peint par un **backend de texturation que vous choisissez au moment du déploiement** (par défaut **TRELLIS.2**, Microsoft, MIT — un texturateur conditionné par SLAT/voxels produisant des matériaux PBR complets sur un atlas 4096²).
3. **Sortie PBR** — exporté en GLB avec des cartes PBR intégrées, prêt pour le rendu physiquement réaliste dans n'importe quel moteur moderne.

Le **TRELLIS.2 (pipeline complet)** fait la même chose de bout en bout dans un seul modèle — sans étape de texturation séparée.

**La licence bien en vue — au déploiement ET à la génération.** Chaque option déployable affiche son **détail complet de licence et de dépendances** dans la boîte de dialogue de déploiement — chaque modèle qu'elle télécharge, la licence de ce modèle, et s'il est exploitable commercialement ou restreint — et vous lisez et acceptez avant de déployer. Au moment de la génération, la visionneuse d'assets rappelle la licence et confirme *« accepté au déploiement le `<date>` »* (sans second clic nécessaire) :

| Backend de texturation | Licence | Usage commercial | Idéal pour |
|------------------------|---------|------------------|------------|
| **TRELLIS.2** *(par défaut)* | MIT | ✅ Oui — nécessite une attribution « Built with DINOv3 » dans votre produit | Production, assets commerciaux, qualité maximale |
| **Hunyuan3D-Paint** | Tencent Community | ❌ Non commercial | Recherche / non commercial, visages exceptionnels |

La suppression d'arrière-plan (l'étape de détourage) utilise **BiRefNet (MIT)** par défaut — entièrement saine pour un usage commercial — avec une alternative non commerciale (RMBG) disponible en option déclarée. ArtSmoker ne télécharge jamais silencieusement une dépendance restreinte : tout ce qui est restreint ou non commercial est nommé, badgé et conditionné à une acceptation explicite.

**Sortie :** GLB standard avec textures PBR intégrées — s'importe directement dans Unity, Unreal Engine, Blender et d'autres moteurs de jeu. La visionneuse 3D interactive supporte l'orbite, le zoom et le panoramique pour une inspection immédiate, et l'onglet **Modèle 3D** liste les modèles et outils exacts utilisés (modèle de géométrie, backend de texturation, dépendances, instance, paramètres) pour une traçabilité complète.

**Infrastructure :** Les deux pipelines se déploient via le même flux Modèles Personnalisés en 1 clic, le sélecteur au moment du déploiement affichant pour chaque option sa licence, son tableau de dépendances, son instance de base et le coût/temps estimés. L'instance de base ajustée au plus juste du pipeline TRELLIS.2 complet est **`ml.g5.2xlarge`** (~$1,52/h ; une exécution réelle a mesuré un pic de ~4,78 Go de VRAM sur les 24 Go du GPU A10G et s'est terminée proprement — préférée au L40S `g6e.xlarge`, largement surdimensionné pour cette charge et plus coûteux). Les tailles `g6e` supérieures restent disponibles comme montées en gamme offrant de la marge. Les endpoints se mettent à l'échelle à zéro en veille — $0 entre les tâches. Le premier démarrage à froid compile les extensions CUDA une seule fois (puis mises en cache sur S3 pour des redémarrages rapides). Avant de déployer un modèle à accès restreint, la boîte de dialogue **pré-vérifie l'accès HuggingFace pour chaque dépôt qu'il télécharge** et affiche un ✓/✗ par dépôt avec l'étape suivante exacte — vous ne découvrez ainsi jamais une acceptation de licence manquante plusieurs minutes après le début d'un démarrage à froid.

> **Visionner le GLB :** les textures sont encodées en WebP (`EXT_texture_webp`) pour garder des fichiers compacts — rendu parfait dans la visionneuse intégrée, Blender 4.x, three.js et les importateurs Unity/Unreal modernes. Preview/QuickLook de macOS ne prend pas en charge le WebP dans le glTF et affiche le modèle en noir ; utilisez la visionneuse intégrée ou tout outil glTF moderne.

| Métrique | Valeur |
|----------|--------|
| Qualité du maillage | Jusqu'à ~1M de faces, normales de sommets complètes |
| Résolution de texture | Atlas PBR 4096² (couleur de base + métallique-rugosité + alpha) |
| Licence | Exploitable commercialement par défaut (TRELLIS.2 MIT + BiRefNet MIT) ; backends non commerciaux proposés avec divulgation complète |
| Types d'assets supportés | Ressource de jeu, Personnage |

### 📝 1.9.1 Exports prêts pour le moteur (GLB · FBX · USD)

![Visionneuse 3D avec outils par variante et options d'export FBX/USD adaptées au moteur de jeu](docs/images/3d-model-viewer-export.png)

Chaque modèle 3D généré peut être exporté **préparé pour votre moteur de jeu**, directement depuis l'onglet 3D de la visionneuse d'assets :

- **Moteur cible** — choisissez Générique (glTF, Y vers le haut), Unreal Engine (axe Z vers le haut), Unity, Godot, Maya ou 3ds Max. Les exports FBX et USD sont orientés avec les bons axes haut/avant pour ce moteur, si bien que les modèles s'importent droits — sans corrections de rotation manuelles.
- **Préparation optionnelle, à votre convenance** (chacune via un menu déroulant indépendant — rien n'est imposé) :
  - **Packing de textures** — jeux de textures par moteur : **ORM** Unreal (AO/Roughness/Metallic), **Métallique + lissage** dans l'alpha pour Unity, **Mask Map HDRP** pour Unity. Une fois sélectionné, l'export devient un ZIP contenant le modèle plus un dossier `textures/`.
  - **LOD** — une **chaîne LOD0–LOD3** décimée (100/50/20/5 %) avec un véritable groupe de LOD FBX qu'Unreal importe automatiquement ; le nommage `_LOD0…_LOD3` correspond aussi à la convention d'Unity.
  - **Collision** — une enveloppe convexe ou une **décomposition convexe CoACD**, nommée selon la convention du moteur (`UCX_*` pour l'import automatique d'Unreal, suffixes `-convcolonly` pour Godot).
  - **UV2 lightmap** — un second canal UV, déplié par projection intelligente, pour l'éclairage précalculé.
- **Flux en deux étapes** — les boutons affichent **Générer FBX/USD/GLB** pour une combinaison qui n'existe pas encore ; un clic déclenche la conversion côté serveur (une ligne de statut vous tient informé — les gros modèles peuvent prendre une minute ou deux). Une fois généré, le bouton passe à **Télécharger** avec un ✓ et livre instantanément. Chaque combinaison distincte est mise en cache — rien n'est jamais régénéré.
- **Pastilles « prêt à télécharger »** — l'onglet 3D liste toutes les combinaisons déjà générées pour la version courante, un clic pour retélécharger n'importe laquelle.
- **Le GLB original est sacré** — « Télécharger GLB (original) » renvoie toujours la sortie intacte, identique à l'octet près, du pipeline de génération. Les exports traités (y compris un GLB traité avec LOD/collision intégrés) sont des fichiers nommés séparément à côté de lui.
- **Zéro installation** — les conversions s'exécutent côté serveur via un Blender headless géré : une installation existante est réutilisée si présente, sinon une copie portable se télécharge automatiquement à la première utilisation (voir Paramètres des modèles → onglet Maintenance pour la version et les mises à jour). Les utilisateurs finaux n'installent rien.

### 📝 1.9.2 À quoi s'attendre de la 3D générée par IA — Un guide honnête

L'image-to-3D est une technologie jeune, et il vaut la peine de savoir ce que les meilleurs modèles actuels (y compris ceux qu'exécute ArtSmoker) livrent réellement — et ce qu'ils ne livrent pas. La sortie est un **maillage dense de type objet scanné** : jusqu'à ~1M de triangles non structurés avec des textures PBR précalculées. De près, vous remarquerez une surface au grain irrégulier caractéristique, et les éléments fins (mèches de cheveux, sangles, franges de tissu) sont là où la géométrie IA est la plus faible. Il n'y a **ni topologie propre en quads, ni boucles d'arêtes adaptées à l'animation, ni rig** — c'est l'état de l'art dans toute l'industrie, pas une limitation propre à un outil en particulier.

**Là où ces assets excellent — et là où il faut un artiste :**

| Cas d'usage | Prêt à l'emploi ? |
|-------------|-------------------|
| Props, éléments de décor, habillage de scène | ✅ Oui — utilisable tel quel |
| Personnages d'arrière-plan / de moyenne distance, foules | ✅ Oui — à distance, le bruit de surface disparaît ; utilisez la chaîne de LOD |
| Prototypage, blockouts, préviz, démos de pitch | ✅ Oui — sans doute le cas d'usage le plus fort |
| Jeux mobiles / stylisés | ✅ Souvent — les LOD décimés aident |
| Personnages héros, gros plans, personnages animés | ⚠️ Un point de départ — prévoyez retopologie, nettoyage et rigging par un artiste |

Ce qu'ArtSmoker ajoute par-dessus le maillage brut, c'est que tout arrive **correctement empaqueté pour votre moteur** — bon axe vertical par cible, chaîne de LOD, proxys de collision, packing de textures spécifique au moteur — pour que le travail restant soit créatif, pas de la plomberie.

**Vous inspectez les exports dans Blender (ou un autre outil DCC) ? Deux choses paraîtront étranges — les deux sont normales :**

- **Généré avec des LOD ?** Le fichier contient **4 copies empilées** du modèle (LOD0–3). Vues ensemble, elles scintillent (z-fighting) et paraissent bruitées — masquez LOD1–3 dans l'Outliner et jugez la qualité sur LOD0 seul. Les moteurs de jeu n'affichent qu'un seul LOD à la fois, donc cela n'arrive jamais en moteur.
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

- **Python 3.12, 3.13 ou 3.14** — le SDK vocal Nova Sonic (`aws_sdk_bedrock_runtime`) requiert la 3.12 ou une version ultérieure, et `numba` (utilisé par la suppression d'arrière-plan locale via `rembg`) ne prend pas encore en charge la 3.15
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
# Test 1 : pouvez-vous lister les modèles ? (nécessite bedrock:ListFoundationModels)
aws bedrock list-foundation-models --region us-east-1 --query "modelSummaries[0].modelId" --output text

# Test 2 : pouvez-vous invoquer un modèle d'image ? (nécessite bedrock:InvokeModel)
# (p. ex. Stable Diffusion 3.5 Large — remplacez-le par n'importe quel ID de modèle
#  d'image de la liste du test 1 s'il n'est pas proposé dans votre compte ou Région.)
aws bedrock-runtime invoke-model --region us-west-2 \
  --model-id stability.sd3-5-large-v1:0 \
  --content-type application/json --accept application/json \
  --body '{"prompt":"test","aspect_ratio":"1:1"}' \
  /dev/null 2>&1 && echo "InvokeModel: OK" || echo "InvokeModel: FAILED"

# Test 3 : pouvez-vous utiliser l'API Converse ? (autorisée via bedrock:InvokeModel)
# (Remplacez par n'importe quel ID de modèle Claude auquel vous avez accès — p. ex. le
#  profil d'inférence Sonnet actuel de la liste du test 1 ; la version exacte évolue.)
aws bedrock-runtime converse --region us-west-2 \
  --model-id us.anthropic.claude-sonnet-5 \
  --messages '[{"role":"user","content":[{"text":"hi"}]}]' \
  --inference-config '{"maxTokens":1}' \
  --query "output.message.content[0].text" --output text 2>&1 && echo "Converse: OK" || echo "Converse: FAILED"

# Test 4 : pouvez-vous lister les modèles personnalisés ? (nécessite bedrock:ListCustomModels)
aws bedrock list-custom-models --region us-east-1 \
  --query "modelSummaries[0].modelName" --output text 2>&1 && echo "ListCustomModels: OK" || echo "ListCustomModels: no custom models (or permission denied)"
```

Si les tests 1 à 3 réussissent, vos permissions de base sont en place. Le test 4 n'est nécessaire que pour la découverte des modèles personnalisés. Si le test 1 réussit mais que les tests 2-3 échouent, votre politique IAM autorise le listing mais pas l'invocation — mettez-la à jour à l'aide du tableau de permissions ci-dessous.

<a id="iam-permissions"></a>

### 📝 2.2 Permissions IAM

Votre utilisateur IAM, votre rôle ou votre instance profile a besoin de ces permissions :

| Permission | Utilisée pour |
|------------|---------------|
| `bedrock:InvokeModel` | Génération d'images, édition d'images, post-traitement (tous les modèles d'image) |
| `bedrock:InvokeModelWithResponseStream` | Réponses LLM en streaming (Studio de Chat) — l'API ConverseStream s'autorise via cette action. L'API Converse non-streaming (affinage de prompts, analyse de style, génération de concepts) s'autorise via `bedrock:InvokeModel` — il n'existe pas d'action `bedrock:Converse` distincte |
| `bedrock:InvokeModelWithBidirectionalStream` | Transcription vocale (optionnel — l'app fonctionne sans) |
| `bedrock:StartAsyncInvoke` | Génération vidéo (invocation asynchrone ; l'opération elle-même est autorisée via `bedrock:InvokeModel`, également accordée) |
| `bedrock:GetAsyncInvoke` | Interroger le statut des tâches de génération vidéo |
| `bedrock:ListAsyncInvokes` | Lister les tâches de génération vidéo |
| `bedrock:ListFoundationModels` | Découverte des modèles de fondation (Synchroniser depuis AWS) |
| `bedrock:ListCustomModels` | Découverte des modèles personnalisés fine-tunés de votre compte |
| `bedrock:ListImportedModels` | Découverte des modèles importés de votre compte |
| `bedrock:GetCustomModel` | Lire les détails d'un modèle personnalisé (modèle de base, statut) |
| `bedrock:GetImportedModel` | Lire les détails d'un modèle importé (architecture, statut) |
| `bedrock:ListProvisionedModelThroughputs` | Trouver les modèles personnalisés invocables avec throughput provisionné |
| `bedrock:ListCustomModelDeployments` | Trouver les modèles personnalisés avec déploiements on-demand |
| `bedrock:CreateInference` *(ou la politique `AmazonBedrockMantleInferenceAccess`)* | **Amazon Bedrock Mantle** — modèles de pointe accessibles uniquement via l'endpoint Mantle (p. ex. OpenAI GPT‑5.x, Claude Mythos, GLM, Grok, Qwen, Gemma). Son absence n'affecte que ces modèles ; Claude via Converse continue de fonctionner. |
| `account:ListRegions` | Scanner uniquement les régions **activées** de votre compte pendant le Sync (rapide, pas d'erreurs sur les régions opt‑in). Optionnel — se rabat sur le scan de toutes les régions. |
| `account:GetRegionOptStatus` | Lire le statut opt‑in par région (complément de `account:ListRegions`). Optionnel. |
| `s3:CreateBucket` | Créer un bucket S3 pour le stockage vidéo (optionnel, via l'UI) |
| `s3:PutObject` / `s3:GetObject` / `s3:DeleteObject` / `s3:ListBucket` | Stockage et récupération des sorties vidéo ; entrées/sorties des tâches asynchrones et artefacts 3D pour les Modèles Personnalisés |
| `s3:ListAllMyBuckets` | Le navigateur de buckets S3 dans Paramètres vidéo / l'import de styles (optionnel) |
| `s3:GetLifecycleConfiguration` / `s3:PutLifecycleConfiguration` | Règles d'expiration automatique des fichiers temporaires des tâches asynchrones sur le bucket de déploiement (Modèles Personnalisés) |
| `aws-marketplace:Subscribe` | Auto-abonnement à la première utilisation de modèles tiers (y compris les modèles Mantle tiers) |
| `aws-marketplace:ViewSubscriptions` | Vérifier les abonnements aux modèles existants |
| `sts:GetCallerIdentity` | Validation des identifiants au démarrage ; sous-tend également le jeton porteur Mantle signé localement |
| `pricing:GetProducts` | Récupérer les tarifs des modèles pendant « Synchroniser depuis AWS » (optionnel) |
| `sagemaker:*` | Modèles personnalisés auto-hébergés sur Amazon SageMaker (optionnel — uniquement si vous utilisez les Modèles Personnalisés) |
| `application-autoscaling:*` (enregistrer/désenregistrer des cibles, créer/supprimer/décrire des politiques) | Mise à l'échelle vers zéro + depuis zéro des endpoints des Modèles Personnalisés (optionnel — uniquement pour les Modèles Personnalisés) |
| `cloudwatch:PutMetricAlarm` / `DeleteAlarms` / `DescribeAlarms` | L'alarme de backlog pour la mise à l'échelle depuis zéro des endpoints des Modèles Personnalisés (optionnel) |
| `logs:DescribeLogStreams` / `FilterLogEvents` / `GetLogEvents` / `PutRetentionPolicy` | Détection de disponibilité des endpoints + rétention des journaux pour les Modèles Personnalisés (optionnel) |
| `servicequotas:GetServiceQuota` / `RequestServiceQuotaIncrease` | Vérification du quota d'instances GPU / demande d'augmentation en un clic dans la boîte de dialogue de déploiement (optionnel) |
| `ecr:DescribeRepositories` | Résolution de l'image SageMaker Deep Learning Container au déploiement (optionnel) |
| `iam:CreateServiceLinkedRole` (limité à `sagemaker.application-autoscaling.amazonaws.com`) | La toute première mise à l'échelle automatique d'un endpoint dans le compte crée automatiquement `AWSServiceRoleForApplicationAutoScaling_SageMakerEndpoint` (optionnel — inutile si ce rôle existe déjà) |
| `iam:PassRole` | Autoriser Amazon SageMaker à utiliser votre rôle (optionnel — uniquement pour les Modèles Personnalisés) |
| `iam:CreateRole` / `iam:AttachRolePolicy` / `iam:PutRolePolicy` | Auto-création du rôle d'exécution Amazon SageMaker au premier déploiement (optionnel — uniquement pour les Modèles Personnalisés) |
| `iam:GetRole` / `iam:UpdateAssumeRolePolicy` | Auto-configuration d'un rôle existant pour la relation de confiance Amazon SageMaker (optionnel) |
| `secretsmanager:CreateSecret` / `UpdateSecret` / `GetSecretValue` / `DescribeSecret` / `DeleteSecret` | Stockage chiffré des jetons HuggingFace pour les modèles à accès restreint (optionnel — nettoyé automatiquement au teardown) |

**Configuration la plus rapide** (politiques managées — accès le plus large) :

```bash
# Option A : attacher des politiques managées à votre utilisateur IAM (le plus simple en développement local)
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

# Endpoint Amazon Bedrock Mantle — requis pour les modèles de pointe (p. ex. OpenAI GPT-5.x,
# Claude Mythos, GLM, Grok). À omettre uniquement si vous n'utilisez aucun modèle exclusif à Mantle.
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockMantleInferenceAccess

# Ajouter l'accès S3 pour le stockage vidéo
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

**Configuration à portée restreinte** (permissions plus strictes — recommandée pour la production) :

```bash
# Créer une politique IAM ciblée avec uniquement les permissions dont ArtSmoker a besoin
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

# Attacher à votre utilisateur IAM (remplacez YOUR_ACCOUNT_ID et YOUR_USERNAME)
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/ArtSmokerAccess
```

> [!NOTE]
> **Deux points à ajuster pour votre compte :** (1) La déclaration S3 est limitée aux buckets nommés `artsmoker-*` — si vous pointez ArtSmoker vers un bucket portant un autre nom (Paramètres vidéo permet de choisir n'importe quel bucket existant), élargissez ce `Resource` à l'ARN de votre bucket. (2) Les ressources SageMaker créées par ArtSmoker sont nommées `artsmoker-*`, donc le `Resource` ciblé fonctionne tel quel ; les actions `sagemaker:List*` ne prennent pas en charge le ciblage par ressource et figurent dans une déclaration séparée.
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
# Vérifier les outils de conversion SVG
which vtracer && echo "vtracer: OK" || echo "vtracer: not installed (optional)"
which potrace && echo "potrace: OK" || echo "potrace: not installed (optional)"
```

### 📝 2.4 Optionnel : outils de vignettes et métadonnées vidéo

Le Studio Vidéo génère des vidéos MP4 via les modèles vidéo d'Amazon Bedrock (p. ex. Luma AI Ray). Pour extraire les vignettes (première frame en JPEG) et les métadonnées vidéo (durée, résolution, FPS), **ffmpeg** et **ffprobe** doivent être installés sur la machine qui exécute le backend ArtSmoker.

Sans ffmpeg :
- Les vidéos se génèrent et se lisent toujours correctement (streamées depuis S3 ou téléchargées en MP4)
- Les vignettes seront manquantes — la Galerie et le Studio Vidéo affichent un placeholder noir au lieu d'une image d'aperçu
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

<a id="installation"></a>

## 📌 3. Installation

### 📝 3.1 macOS

```bash
git clone https://github.com/niravdd/ArtSmoker.git && cd ArtSmoker

# Option A : avec un environnement virtuel (recommandé)
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Option B : sans environnement virtuel (installation au niveau du système)
pip3 install -r backend/requirements.txt
```

> [!NOTE]
> Sur macOS, installez Python depuis [python.org](https://www.python.org/downloads/) ou via Homebrew. Le `python3` par défaut de Homebrew peut être plus récent que la 3.14 (p. ex. la 3.15, pas encore prise en charge) — si `python3 --version` affiche une telle version, exécutez `brew install python@3.14` et créez le venv avec `python3.14 -m venv .venv`. Le `python3` des Xcode command-line tools est trop ancien.

### 📝 3.2 Linux (Debian/Ubuntu)

```bash
# Installer Python si nécessaire
sudo apt update && sudo apt install python3 python3-pip python3-venv

git clone https://github.com/niravdd/ArtSmoker.git && cd ArtSmoker

# Option A : avec un environnement virtuel (recommandé)
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Option B : sans environnement virtuel
pip3 install --user -r backend/requirements.txt
```

> [!NOTE]
> Sur certaines distributions Linux, `pip install` en dehors d'un venv nécessite le flag `--user` ou `--break-system-packages` (PEP 668). Utiliser un venv évite entièrement ce problème.

> [!IMPORTANT]
> ArtSmoker nécessite **Python 3.12, 3.13 ou 3.14** — vérifiez avec `python3 --version`. Si le `python3` de votre distribution sort de cette plage (Ubuntu 24.04 fournit la 3.12 ; Ubuntu 22.04 fournit la 3.10, trop ancienne), installez une version prise en charge en parallèle et créez le venv avec celle-ci. Sur **Amazon Linux 2023**, le `python3` système reste en 3.9, mais des versions plus récentes sont disponibles sous forme de paquets : `sudo dnf install -y python3.12`, puis `python3.12 -m venv .venv`.

<a id="install-windows"></a>

### 📝 3.3 Windows

```powershell
git clone https://github.com/niravdd/ArtSmoker.git
cd ArtSmoker

# Option A : avec un environnement virtuel (recommandé)
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt

# Option B : sans environnement virtuel
pip install -r backend\requirements.txt
```

> [!NOTE]
> Sur Windows, utilisez `python` (pas `python3`). Installez Python 3.12, 3.13 ou 3.14 depuis [python.org](https://www.python.org/downloads/) — cochez « Add to PATH » pendant l'installation. Si plusieurs versions sont installées, choisissez-en une avec le lanceur : `py -3.14 -m venv .venv`. Si PowerShell refuse d'exécuter `.venv\Scripts\activate` (« running scripts is disabled »), autorisez-le une fois avec `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, ou utilisez `.venv\Scripts\activate.bat` depuis cmd. Le sélecteur de polices du Studio de Texte détecte les polices depuis `C:\Windows\Fonts` (la détection des polices système n'est actuellement disponible que sur macOS/Linux — les utilisateurs Windows peuvent utiliser des polices personnalisées globales ou spécifiques au style).

<a id="running"></a>

## 📌 4. Exécution

### 📝 4.1 Développement solo (toutes plateformes)

Processus unique avec rechargement automatique à chaque modification de fichier — idéal pour un seul développeur travaillant localement :

```bash
# Avec venv (activez-le d'abord)
source .venv/bin/activate          # macOS / Linux
.venv\Scripts\activate             # Windows

uvicorn backend.main:app --reload
```

```bash
# Sans venv (si installé au niveau du système)
uvicorn backend.main:app --reload

# Ou si uvicorn n'est pas dans le PATH
python3 -m uvicorn backend.main:app --reload     # macOS / Linux
python -m uvicorn backend.main:app --reload       # Windows
```

Ouvrez **http://localhost:8000** — le frontend est servi par FastAPI, aucun serveur web séparé n'est nécessaire.

Au démarrage, la console affiche les résultats de la validation des identifiants AWS. Si quelque chose ne va pas, vous verrez une boîte d'erreur claire. Vous pouvez aussi consulter `http://localhost:8000/api/health` pour le statut.

**Logs.** En plus de la console, ArtSmoker écrit un journal complet en **ajout seul** (append-only) dans `logs/artsmoker.log` **par défaut**, afin que vous puissiez revoir une session passée après la fermeture de l'application. Chaque exécution est encadrée par une bannière de session (heure de lancement, version, pid, hôte) et clôturée par une bannière d'arrêt (heure d'arrêt, durée). Pour changer le chemin ou le désactiver :

```bash
ARTSMOKER_LOG_FILE=/var/log/artsmoker/app.log uvicorn backend.main:app   # chemin personnalisé
ARTSMOKER_LOG_TO_FILE=false uvicorn backend.main:app                      # désactiver la journalisation dans un fichier
```

(Ou définissez `log_to_file` / `log_file` dans un `.env` local. Avec plusieurs workers, chaque worker ajoute au même fichier.)

**Redémarrage automatique (optionnel, toutes les plateformes).** Les commandes ci-dessus fonctionnent telles quelles. Pour permettre en plus à ArtSmoker de **se redémarrer sur place** — de sorte qu'une mise à jour automatique, ou le bouton **Redémarrer maintenant** de l'application, recharge le nouveau code sans que vous ayez à le relancer — démarrez-le plutôt via le superviseur multiplateforme intégré :

```bash
python -m backend.main            # ajoutez --host / --port au besoin ; Ctrl-C l'arrête proprement
```

Cela fonctionne sur **tous les systèmes d'exploitation, y compris Windows**. Le superviseur exécute l'application dans un processus enfant et la relance sur demande de redémarrage. (L'exécution sous gunicorn ou via un gestionnaire de services comme systemd offre le même redémarrage sur place — voir §4.2 et §6.)

### 📝 4.2 Multi-utilisateur / machine de test partagée / production (macOS / Linux)

Pour tout environnement avec plus d'un utilisateur simultané — qu'il s'agisse d'une machine de dev/test partagée, d'un staging ou d'une production — utilisez **gunicorn** avec plusieurs workers :

```bash
# Installer gunicorn (une seule fois, en plus de requirements.txt)
pip install gunicorn

# Lancer avec gunicorn (multi-worker, gère les utilisateurs simultanés)
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
# Créer le rôle IAM avec une politique de confiance EC2
aws iam create-role --role-name ArtSmokerEC2Role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attacher la politique ArtSmoker (la politique ciblée de la section 2.2, ou la politique managée)
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# Créer un profil d'instance et y attacher le rôle
aws iam create-instance-profile --instance-profile-name ArtSmokerEC2Profile
aws iam add-role-to-instance-profile \
  --instance-profile-name ArtSmokerEC2Profile \
  --role-name ArtSmokerEC2Role
```

**Étape 2 : Lancer une instance EC2** (ou attacher le profil à une instance existante) :

```bash
# Attacher à une instance existante en cours d'exécution
aws ec2 associate-iam-instance-profile \
  --instance-id i-YOUR_INSTANCE_ID \
  --iam-instance-profile Name=ArtSmokerEC2Profile
```

**Étape 3 : Installer et exécuter sur l'instance** (SSH sur l'instance) :

```bash
# Installation (une seule fois)
sudo yum install -y python3 python3-pip git   # Amazon Linux
# sudo apt install -y python3 python3-pip python3-venv git   # Ubuntu

git clone https://github.com/niravdd/ArtSmoker.git && cd ArtSmoker
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install gunicorn

# Optionnel : installer ffmpeg pour les vignettes vidéo
sudo yum install -y ffmpeg   # Amazon Linux
# sudo apt install -y ffmpeg   # Ubuntu
```

**Étape 4 : Exécuter comme service systemd** (persistant, redémarrage automatique) :

```bash
# Créer le fichier de service
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

# Activer et démarrer
sudo systemctl daemon-reload
sudo systemctl enable artsmoker
sudo systemctl start artsmoker

# Vérifier que le service tourne
sudo systemctl status artsmoker

# Consulter les journaux
sudo journalctl -u artsmoker -f
```

Ouvrez **http://YOUR_INSTANCE_IP:8000** — assurez-vous que votre security group EC2 autorise le trafic TCP entrant sur le port 8000.

Si vous accédez à ArtSmoker par un nom DNS plutôt que par une adresse IP (p. ex. `artsmoker.example.com`), ajoutez ce nom : `ARTSMOKER_ALLOWED_HOSTS=artsmoker.example.com`. ArtSmoker refuse les noms d'hôte inconnus, ce qui le protège contre le DNS rebinding.

### 📝 4.4 Premières étapes après l'installation

Une fois ArtSmoker en cours d'exécution, effectuez ces étapes pour obtenir les meilleurs résultats :

**1. Synchroniser les modèles depuis AWS** — Ouvrez **Paramètres du modèle** (icône engrenage dans n'importe quel studio) → cliquez sur **Synchroniser depuis AWS**. Cela découvre tous les modèles d'image, vidéo et chat disponibles dans toutes les régions Bedrock. Prend 30-60 secondes. Nécessaire une seule fois, ou lorsqu'AWS ajoute de nouveaux modèles.

**2. Passer en revue et personnaliser les modèles de prompt** — C'est la configuration la plus impactante que vous puissiez faire. Ouvrez l'onglet **Paramètres des modèles → Modèles de Prompt**. ArtSmoker utilise 28 prompts directifs éditables qui contrôlent le comportement de l'IA :

| Template | Ce qu'il contrôle |
|----------|-------------------|
| Affinage du prompt | Comment vos descriptions textuelles sont transformées en prompts de génération d'images détaillés |
| Options créatives | Comment plusieurs options créatives sont générées à partir d'une seule idée |
| Analyse de style | Comment les images de référence sont analysées pour apprendre votre style artistique |
| Pré-filtrage / Réécriture | À quel point le système de pré-vérification et de réécriture est strict |
| Amélioration du prompt vidéo | Comment les prompts vidéo sont enrichis de mouvements de caméra et d'éclairage |
| Studio de Texte : mise en page du texte | Comment le Studio de Texte conçoit le positionnement du texte sur les images |

Chaque template peut être :
- **Édité directement** — modifiez les instructions pour correspondre aux besoins de votre équipe
- **Amélioré avec l'IA** — sélectionnez n'importe quel modèle LLM, ajoutez éventuellement des instructions (par ex. « optimiser pour le pixel art »), et cliquez sur « Améliorer avec l'IA ». Examinez la suggestion, puis cliquez sur Accepter ou Ignorer
- **Réinitialisé par défaut** — restaurez l'original à tout moment

Les templates sont organisés par studio (Studio Image, Bibliothèque de styles, Sécurité du contenu, Studio Vidéo, Studio de Texte, Studio de Chat, Traduction) avec des descriptions conviviales de ce que chacun contrôle.

**Sécurité des variables :** Les templates utilisent des variables `{curly_brace}` (par ex. `{user_prompt}`, `{model_name}`) qui sont substituées au runtime. Si vous supprimez accidentellement une variable requise, ArtSmoker va :
1. Bloquer la sauvegarde et indiquer quelles variables manquent
2. Proposer **« Corriger et enregistrer »** — un LLM réinsère automatiquement les variables manquantes aux bons endroits de votre texte édité
3. Vérifier la correction avant de sauvegarder

Les templates se chargent depuis `backend/prompt_templates.json` — la source de vérité au runtime. Vos modifications sont enregistrées dans `backend/prompt_templates.user.json` (gitignored) et superposées par-dessus, de sorte qu'une mise à jour ou un `git pull` n'écrase jamais vos personnalisations. Si le JSON est manquant ou corrompu, ou qu'un nouveau template arrive dans le code, il s'auto-répare : la semence de code intégrée régénère/complète uniquement les entrées manquantes, sans jamais écraser les existantes.

> [!TIP]
> Commencez par examiner les templates **Affinage du prompt** et **Options créatives**. Ce sont ceux qui ont le plus d'impact sur la qualité de sortie. Si votre équipe est spécialisée dans un style artistique particulier (par ex. pixel art, aquarelle, isométrique), ajoutez ces préférences directement dans les templates pour que chaque génération en bénéficie.

**3. Configurer un profil de style** (optionnel) — Allez dans **Bibliothèque de styles**, créez un nouveau style, téléchargez des images de référence, et cliquez sur **Analyser le style**. Cela apprend à ArtSmoker votre identité visuelle.

**4. Choisir votre langue** — Cliquez sur un bouton de langue dans la barre de navigation (EN | 日 | 中 | 한 | हिं | РУ | FR | ES | DE) si vous préférez une interface non anglaise.

## 📌 5. Architecture

```
┌──────────────────────────────────────────────────────┐
│  Navigateur (SPA)                                    │
│  Vanilla JS + Tailwind CSS                           │
└──────────────────────────┬───────────────────────────┘
                           │ HTTP / SSE
                           ▼
┌──────────────────────────────────────────────────────┐
│  Backend FastAPI (Python)                            │
│                                                      │
│  /api/styles        CRUD des styles + import         │
│  /api/generate      Génération à deux niveaux        │
│  /api/type-studio   Texte superposé + polices        │
│  /api/video         Génération vidéo + tâches        │
│  /api/chat          Chat LLM + sessions              │
│  /api/gallery       Navigation des assets + export   │
│  /api/browse        Explorateur fichiers/S3          │
│  /api/admin         Registre + modèles de prompt     │
│  /api/refine-prompt Prompt + traduction              │
│  /api/transcribe    Voix vers texte                  │
└───────────┬────────────────────────────┬─────────────┘
            │                            │
            ▼                            ▼
┌────────────────────────┐  ┌──────────────────────────┐
│  us-west-2             │  │  us-east-1               │
│                        │  │                          │
│  LLM (p. ex. Claude)   │  │  Voix (Nova Sonic)       │
│  Génération d'images   │  │                          │
│  Édition d'images      │  │                          │
│    p. ex. Stability AI │  │                          │
│  Vidéo (p. ex. Luma)   │  │                          │
└───────────┬────────────┘  └──────────────────────────┘ ... (autres régions)
            │
            ▼
┌────────────────────────┐
│  Stockage local        │
│  data/styles/          │
│  data/images/          │
│  data/video/           │
│  data/chat/            │
└────────────────────────┘
```

Les Régions indiquées sont celles par défaut ; Sync épingle chaque modèle à une Région où AWS le propose. Les noms de modèles sont des exemples — voir [À propos des noms de modèles](#about-model-names).

## 📌 6. Utilisation

### 📝 6.1 Aperçu du workflow

```
                         ┌─────────────────┐
                         │   ArtSmoker     │
                         └────────┬────────┘
                                  │
         ┌─────────────┬──────────┼────────────┬────────────┐
         │             │          │            │            │
         ▼             ▼          ▼            ▼            ▼
  ┌──────────────┐ ┌────────┐ ┌────────┐ ┌────────────┐ ┌────────┐
  │ Bibliothèque │ │ Studio │ │ Studio │ │   Studio   │ │ Studio │
  │  de styles   │ │ Image  │ │ Vidéo  │ │  de Texte  │ │ de Chat│
  │              │ │        │ │        │ │            │ │        │
  │ Importer     │ │ Générer│ │ Générer│ │ Ajouter du │ │ Chat   │
  │ Analyser     │ │ des    │ │ des    │ │ texte aux  │ │ LLM    │
  │ Définir les  │ │ images │ │ vidéos │ │ images     │ │ multi- │
  │ polices      │ │        │ │        │ │            │ │ modèle │
  └──────┬───────┘ └───┬────┘ └───┬────┘ └─────┬──────┘ └────────┘
         │             │          │            │
         │ ┌───────────┴──────────┴──────────┐ │
         │ │ Style sélectionné ? (optionnel) │ │
         └►│ Enrichit le résultat            │◄┘
           └───────────────────────┬─────────┘
                                   │
                                   ▼
                      ┌────────────────────────┐
                      │        Galerie         │
                      │                        │
                      │ Tout parcourir         │
                      │ Rechercher/filtrer     │
                      │ Sélectionner/supprimer │
                      └────────────┬───────────┘
                                   │
                    ┌──────────────┼─────────────────┐
                    │              │                 │
                    ▼              ▼                 ▼
            ┌──────────────┐ ┌────────────┐ ┌──────────────────┐
            │ Télécharger  │ │ Recharger  │ │ Ajouter du texte │
            │ PNG / SVG    │ │ dans le    │ │ dans le Studio   │
            │              │ │ Studio     │ │ de Texte         │
            │              │ │ Image      │ │ (superposition   │
            │              │ │ (affiner et│ │  de texte)       │
            │              │ │ régénérer) │ │                  │
            └──────────────┘ └────────────┘ └──────────────────┘
```

**Trois points d'entrée, une galerie unifiée :**

- **Commencer par un style** — téléchargez de l'art de référence dans la Bibliothèque de styles, laissez l'IA l'analyser, puis générez dans n'importe quel studio. Le style guide toutes les sorties.
- **Commencer sans style** — allez directement dans le Studio Image, le Studio Vidéo ou le Studio de Texte. L'IA use de son meilleur jugement.
- **Commencer depuis la Galerie** — choisissez n'importe quel asset précédemment généré et rechargez-le dans le studio approprié pour l'affiner, ajoutez-y du texte, lisez une vidéo, ou téléchargez en PNG/SVG/MP4.

Tous les assets générés (images, vidéos, superpositions de texte, texte autonome) atterrissent dans la Galerie unifiée. Rien n'est écrasé — chaque génération crée de nouveaux assets.

### 📝 6.2 Pipeline de génération

```
Prompt utilisateur : "hospital building"
         │
         ▼
┌──────────────────────────────────────────────────────────────────┐
│ 1. Composition du prompt                                         │
│    LLM rapide (1 option) ou LLM complexe (2 à 5 options)         │
│    (bouton optionnel « Générer le Prompt Amélioré »)             │
│    + style + type d'asset                                        │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│ 2. Test canari                                                   │
│    Une seule image teste la modération                           │
│    Réussi ? ──► Lot complet                                      │
│    Échec ?  ──► Changement de modèle                             │
│                 ou suggestion de réécriture                      │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. Génération d'images en parallèle                              │
│    Jusqu'à 5 options × 5 variations = 25 images                  │
│    ThreadPool (3 à 5 workers)                                    │
│    Réessais avec backoff exponentiel (3 tentatives)              │
│    Progression streamée en SSE vers le navigateur                │
│    Annulation coopérative en cas de blocage de modération        │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│ 4. Post-traitement (par image, optionnel)                        │
│    Supprimer l'arrière-plan ──► Stability AI ($0.07/img)         │
│    Agrandir (créatif) ──► Stability AI Creative Upscale ($0.60)  │
│    SVG ──► vtracer / potrace / Pillow (gratuit, local)           │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│ 5. Stockage                                                      │
│    data/images/{asset_id}/                                       │
│    ├── asset.png (fond transparent)                              │
│    ├── asset.svg (optionnel)                                     │
│    └── metadata.json (lignée complète du prompt)                 │
│    Noms de fichiers intelligents : prompt-slug_opt1_var2.png     │
└──────────────────────────────────────────────────────────────────┘
```

### 📝 6.3 Flux de modération de contenu

```
L'utilisateur clique sur Générer
         │
         ▼
┌────────────────────────────┐
│ Pré-vérification du prompt │
│ activée ? (interrupteur,   │
│ activé par défaut)         │
└───┬───────────────────┬────┘
   Oui                 Non
    │                   │
    ▼                   │
┌───────────────┐       │
│ Le LLM rapide │       │
│ analyse le    │       │
│ prompt        │       │
└───┬───────┬───┘       │
 Problème Aucun         │
    │       └──────────►│
    ▼                   │
┌─────────────────────┐ │
│ Dialogue indigo :   │ │
│ • Changer de modèle │ │
│ • Réécrire          │ │
│ • Continuer         │ │
│ • Annuler           │ │
└───┬─────────────────┘ │
    │◄──────────────────┘
    ▼
┌─────────────────────────────┐
│ Test canari                 │
│ (1 image envoyée au modèle) │
└───┬───────────────────┬─────┘
 Bloqué              Réussi
    │                   │
    ▼                   ▼
┌────────────┐    ┌────────────┐
│ Essayer    │    │ Le lot     │
│ d'autres   │    │ complet    │
│ modèles :  │    │ s'exécute  │
│ ça passe ? │    │            │
└───┬──────┬─┘    └────────────┘
   Oui    Non
    │      │
    ▼      ▼
Dialogue   Dialogue
émeraude   ambre
(changer   (réécriture →
 ou         zone du prompt
 réécrire)  amélioré)
```

### 📝 6.4 Studio Image (générer des assets)

Le Studio Image utilise un workflow guidé en 3 étapes :

**Étape 1 — Décrivez votre idée** : Saisissez un prompt dans la zone de texte. Le placeholder montre un exemple réaliste qui change selon le type d'asset sélectionné (par ex. « Une jeune guerrière en armure d'argent ouvragée, longs cheveux sombres tressés, tenant une épée lumineuse, debout au bord d'une falaise au coucher du soleil... » pour Personnage, ou « Un jardin japonais brumeux à l'aube, des lanternes de pierre bordant un sentier sinueux entre des rochers moussus, des pétales de cerisier flottant dans l'air immobile... » pour Environnement). Utilisez l'entrée vocale (bouton micro) pour dicter au lieu de taper.

**Étape 2 — Concepteur de prompts** *(optionnel)* : Cliquez sur **🎨 Concepteur de prompts** pour décomposer votre prompt en composants visuels structurés. L'IA analyse votre prompt et le décompose en sections éditables :

- **Sujet** — description du personnage, vêtements, accessoires, pose, expression
- **Scène** — décor, arrière-plan, accessoires, moment de la journée
- **Composition** — angle de caméra, cadrage, profondeur de champ
- **Éclairage** — lumière principale, lumière d'appoint/de contour, ambiance
- **Style & Couleurs** — style artistique, niveau de qualité, et une palette de couleurs nommée avec échantillons hexadécimaux

Chaque champ peut être édité individuellement. **Générer le Prompt Amélioré** recompose vos modifications en un prompt recomposé à plat (affiché en lecture seule à l'Étape 2) puis génère automatiquement le Prompt IA amélioré pour l'Étape 3.

Avant l'ouverture du Concepteur de prompts, une **classification IA du type d'asset** s'exécute — si votre prompt décrit une scène mais que vous avez sélectionné « Ressource de jeu », une boîte de dialogue suggère de basculer vers « Environnement » ou « Personnage ». Cela garantit que le Concepteur de prompts décompose avec le bon contexte.

**Étape 3 — Aperçu du prompt amélioré** *(optionnel)* : Cliquez sur **Générer le Prompt Amélioré** pour voir le prompt optimisé pour le modèle avant de générer. L'IA prend le prompt recomposé de l'Étape 2 et l'enrichit avec une guidance spécifique au modèle (anatomie, matériaux, éclairage, structure de prompt). Vous pouvez éditer le prompt amélioré avant de générer. Si vous avez utilisé le Concepteur de prompts à l'Étape 2, celui-ci est pré-rempli automatiquement.

**Pipeline de prompt** : Prompt utilisateur → Décomposer → Recomposer (`recomposed_prompt`) → Améliorer avec la guidance du modèle (`enhanced_prompt`) → Modèle d'image. Pour des options multiples, l'étape d'amélioration génère N interprétations distinctes à partir de la même base recomposée. Les trois niveaux sont stockés dans les métadonnées.

**Générer** : Cliquez sur Générer à tout moment — les étapes 2 et 3 sont optionnelles. Si vous les sautez, Générer décompose, recompose et améliore automatiquement votre prompt avant de continuer. **Pré-vérification du prompt** (activé par défaut) analyse le prompt pour détecter les problèmes de modération avant la génération.

**Contrôles additionnels :**
- **Type de ressource** — à sélectionner dans la barre latérale. Change le placeholder du prompt et affecte la façon dont l'IA interprète votre prompt. Le système suggère de basculer s'il détecte une incohérence.
- **Style artistique** — sélectionnez un profil de style pour guider la génération avec votre identité visuelle.
- **Dimensions, Options, Variations** — configurez la taille de sortie et le nombre de concepts créatifs à générer.
- **Post-traitement** — Supprimer l'arrière-plan, Agrandir (créatif), conversion SVG (appliqués après la génération).
- **Déclaration de propriété intellectuelle** — affirmez la propriété ou la licence pour la compatibilité avec les modèles stricts.
- **Paramètres du modèle** — consultez/modifiez la configuration des modèles, découvrez les modèles Amazon Bedrock disponibles.

La progression de la génération est streamée en temps réel via SSE — l'UI affiche quelle image est en cours de génération (par ex. « Génération des images... 12/25 »), le temps écoulé et l'étape actuelle du pipeline. Si l'API est limitée (throttled), vous verrez « API limitée — en attente de nouvelle tentative... » avec le délai, puis « Nouvelle tentative... (essai 2/3) » — chaque image réessaie jusqu'à 3 fois avec un backoff exponentiel afin que les gros lots ne perdent pas de variantes à cause d'une limitation transitoire.

Les résultats générés survivent à la navigation — passer d'un onglet à l'autre et revenir préserve l'état DOM du Studio Image. Seul le bouton de réinitialisation l'efface.

**Modération de contenu intelligente** : Lorsque votre prompt est bloqué par les filtres de modération d'un modèle, ArtSmoker le gère progressivement via trois boîtes de dialogue à code couleur :

- **Indigo (Pré-vérification)** — avant la génération, une IA pré-analyse votre prompt selon la sensibilité connue du modèle sélectionné. Si des problèmes sont détectés, vous voyez les préoccupations spécifiques et pouvez : basculer vers un modèle recommandé, **réécrire le prompt** pour le modèle actuel, procéder quand même, ou annuler.
- **Émeraude (changement de modèle)** — après un blocage de génération, si un modèle alternatif accepte votre prompt tel quel, ArtSmoker indique quel modèle fonctionne et pourquoi. Un clic pour basculer. Journal complet des tentatives disponible (« Voir N tests de modèles »).
- **Ambre (réécriture)** — quand tous les modèles refusent, une réécriture générée par l'IA est proposée dans une zone de texte éditable avec les problèmes spécifiques listés. Un badge vérifié/non vérifié indique si la réécriture a passé le test canari.

**Comportement de réécriture du prompt** : Dans les trois dialogues, choisir « Réécrire » n'écrase jamais votre prompt original. La version réécrite apparaît dans la **zone du prompt amélioré** sous votre texte original, avec un avertissement ambre persistant : *« Cette réécriture est une tentative de rendre le prompt compatible — il reste soumis à la propre évaluation de modération du modèle et peut être rejeté. »* Vous examinez et éditez le prompt amélioré, puis cliquez sur Générer quand vous êtes satisfait. Votre prompt original est toujours préservé dans l'historique et les métadonnées.

Les déclencheurs courants incluent les noms d'IP protégés et les références de personnages, le langage de violence/armes, et les références à du contenu adulte. Astuce : le bouton **« Générer le Prompt Amélioré »** produit souvent des prompts qui passent naturellement la modération, car l'IA reformule en termes descriptifs.

**Test canari intelligent** : Avant de générer le lot complet, ArtSmoker envoie une seule requête d'image « canari » pour tester le prompt contre les filtres de modération du modèle. Si le canari est bloqué, le lot s'arrête immédiatement (1 appel API gaspillé au lieu de N×M×3). Si le canari passe, les tâches restantes s'exécutent en parallèle avec annulation coopérative — si une tâche rencontre un blocage de modération, les autres sautent automatiquement leurs appels API.

### 📝 6.5 Utiliser un profil de style

1. Allez dans l'onglet **Bibliothèque de styles**.
2. Cliquez sur **Créer un nouveau style** — entrez un nom et ajoutez éventuellement des indications de génération. Dans la modale de création, utilisez la section **« Importer les références depuis »** avec les boutons de navigation **Local** et **S3** pour sélectionner un répertoire source ou un chemin de bucket. La navigation ouvre une modale d'explorateur de fichiers/répertoires côté serveur (un clic sélectionne un élément, un double-clic navigue dans les répertoires). Les références importées sont auto-analysées à la création.
3. Les imports de répertoires locaux scannent **récursivement** à travers tous les sous-répertoires pour les images (.png, .jpg, .jpeg, .gif, .bmp, .webp, .tiff, .tif, .tga, .ico, .svg) et les modèles 3D (.glb, .gltf). Les fichiers image sont **symlinkés** à l'aide de **liens symboliques relatifs** (pas de duplication, portables entre machines). Les fichiers de modèles 3D (.glb/.gltf) ont leurs textures intégrées **automatiquement extraites** — data URIs base64, chunks de buffer binaire et références de textures externes sont tous gérés. Les textures extraites sont enregistrées comme copies (préfixées du nom du modèle pour éviter les collisions). Les imports S3 listent récursivement avec pagination et **téléchargent** les fichiers localement. Jusqu'à **100 images de référence** sont importées par style. Les extensions supportées sont centralisées dans `backend/config.py` (`IMAGE_EXTENSIONS` et `MODEL_EXTENSIONS_WITH_TEXTURES`).
4. **Analyse en deux phases avec détection de cohésion** : La phase 1 envoie 8 images au LLM rapide pour déterminer le niveau de cohésion (élevé/moyen/faible) — élevé signifie un style unifié, moyen signifie une structure partagée avec des thèmes différents, faible signifie des styles divers. La phase 2 transmet l'évaluation de cohésion au LLM complexe avec les images de référence, le guidant pour analyser de manière appropriée selon le type de collection. Lorsqu'un style a plus de 20 références, l'analyseur sélectionne un sous-ensemble représentatif diversifié de 20 pour l'appel de vision Opus — garantissant une couverture entre les groupes de noms de fichiers et la diversité des tailles de fichiers. L'IA est informée du nombre total d'images qui existent par rapport à celles qu'elle voit. Le prompt d'analyse est spécifiquement conçu pour les assets de jeux sur fonds transparents — il demande des détails de rendu spécifiques aux matériaux, un système de proportions et des spécificités d'ombre/éclairage. Il extrait 9 attributs de style dont `materials` (comment la pierre, le bois, le métal sont rendus) et `detail_level` (quels détails de surface sont visibles vs simplifiés). Les indications de génération sont étendues à 200 mots couvrant 8 dimensions : perspective, rendu, matériaux, palette de couleurs, proportions, traitement des bords, ombre/éclairage, niveau de détail et arrière-plan — suffisamment spécifiques pour que les assets générés se fondent visuellement avec les références existantes.
5. Dans la vue de détail du style, utilisez **« Importer et analyser »** pour ajouter plus de références et déclencher l'analyse en une seule étape. Le téléchargement par glisser-déposer est aussi supporté et **relance automatiquement l'analyse** lorsque de nouvelles images sont ajoutées.
6. **« Réanalyser le style »** apparaît après l'analyse initiale, vous permettant de relancer manuellement l'analyse à tout moment.
7. **Les indications de génération** font partie du contexte d'analyse — l'IA reçoit à la fois les images de référence et vos indications comme « Artist's Guidance » lors de l'analyse, afin que le profil de style comprenne l'intention, pas seulement l'apparence visuelle. Modifier les indications de génération déclenche aussi une **réanalyse automatique**.
8. De retour dans le **Studio Image**, sélectionnez votre style dans le menu déroulant — tous les assets générés correspondront à son identité visuelle (palette, perspective, style de rendu, ambiance).

### 📝 6.6 Flux d'analyse de style

```
┌──────────────────────────────────────────────────┐
│ Créer / importer un style                        │
│ (images de référence téléversées ou importées)   │
└────────────────────────┬─────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────┐
│ Phase 1 : vérification de la cohésion            │
│ LLM rapide — 8 images — ~$0.01                   │
│ Détermine : élevée / moyenne / faible            │
│   élevée  = style unifié                         │
│   moyenne = structure partagée, thèmes variés    │
│   faible  = ensemble hétérogène                  │
└────────────────────────┬─────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────┐
│ Phase 2 : analyse complète                       │
│ LLM complexe — jusqu'à 20 images                 │
│ Guidée par le niveau de cohésion                 │
│ + « Artist's Guidance » (indications)            │
│ Extrait 9 attributs de style                     │
└────────────────────────┬─────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────┐
│ Phase 3 : génération des indications             │
│ LLM rapide — indications de 200 mots             │
│ 8 dimensions : perspective, rendu,               │
│ matériaux, palette, proportions, bords,          │
│ ombre/éclairage, niveau de détail                │
└────────────────────────┬─────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────┐
│ Enregistré dans profile.json                     │
│ ~$0.14 au total par analyse de style             │
│ Utilisé dans toutes les générations futures      │
└──────────────────────────────────────────────────┘
```

### 📝 6.7 Studio de Texte

Ajoutez du texte aux images ou générez des assets de texte autonomes avec une typographie conçue par l'IA.

- **Deux modes** : « Sur image » composite le texte sur une image de la galerie ; « Autonome » rend le texte sur un fond transparent.
- **Éditeur de texte multi-lignes** avec sélection de police par ligne, contrôles de positionnement, et **entrée vocale** (bouton micro par ligne — dictez le texte via la transcription Nova Sonic).
- **Mises en page conçues par l'IA** — l'IA suggère les couleurs, tailles, positions et effets (ombre, contour, lueur). Demandez 1 à 5 options de mise en page pour différentes directions créatives. Le **modèle LLM** utilisé pour la mise en page est configurable (« LLM complexe (meilleure qualité) » ou « LLM rapide (moins cher) ») — lit depuis les catégories du registre.
- **Sélecteur de polices avec aperçu en direct** — polices de style, 8 polices intégrées (Roboto, Open Sans, Lato, Montserrat, Playfair Display, Oswald, Raleway, Source Code Pro), polices système, et **polices détectées côté client** (via la Local Font Access API ou le sondage canvas).
- **Pré-traitement / Post-traitement** — même workflow que le Studio Image, avec un bouton « Appliquer » pour le post-traitement. La conversion SVG est activée par défaut.
- **Cliquer pour zoomer** — cliquer sur l'aperçu du résultat ouvre la visionneuse d'assets avec zoom/panoramique complet, métadonnées, téléchargement et outils d'édition d'image.
- Les résultats sont enregistrés comme de nouveaux assets de la galerie (les originaux ne sont jamais écrasés).

### 📝 6.8 Galerie

- **Vue unifiée** de toutes les images et vidéos générées dans une **disposition en maçonnerie (masonry)** (chaque asset affiché à son véritable ratio — portrait, carré ou paysage — jamais recadré au centre), avec un **filtre Média** (Tous les médias / Images 2D / Modèles 3D / Vidéo). Le filtre **Modèles 3D** n'affiche que les assets qui possèdent déjà un modèle 3D généré, et ces assets portent un **badge 3D** sur leur tuile.
- **Barre de recherche** pour un filtrage instantané sur tous les assets (prompts, styles, modèles).
- **Multi-sélection** par cases à cocher pour la suppression en masse (gère à la fois les assets image et vidéo). Les suppressions sont **conscientes du lot** — les frères et sœurs survivants suivent combien de variantes ont été retirées, de sorte que recharger un lot partiel dans le Studio Image affiche « X sur Y images restantes (Z supprimées de la galerie) ».
- Les assets se chargent immédiatement avec un cache de métadonnées en mémoire. Triés du plus récent au plus ancien.
- Support de la pagination (limit/offset) pour les grandes collections.
- La Galerie se rafraîchit automatiquement lorsque vous y revenez, et après toute édition ou génération vidéo terminée.
- **Les cartes vidéo** affichent une vignette avec une superposition de lecture, un badge VIDÉO et un indicateur de durée. Cliquez pour ouvrir la modale du lecteur vidéo.
- **Boutons d'action contextuels** par asset selon le type : **« Studio Image »** (indigo) pour recharger dans le Studio Image, **« Ajouter du texte »** (emerald) pour ouvrir dans le Studio de Texte, **« Modifier dans le Studio de Texte »** (purple) pour les assets de texte.
- Cliquez sur n'importe quelle image pour ouvrir la **visionneuse d'assets** (modale) avec :
  - **Zoom/panoramique** — molette de la souris pour zoomer, glisser pour se déplacer, boutons Ajuster/1:1 avec mise en évidence du mode actif.
  - **Onglet Modifier** — retouchez (inpainting), effacez, étendez (outpainting), recherchez et remplacez, ou recoloriez l'image directement. Deux types d'éditeurs sont proposés par mode : **basé sur masque** (p. ex. Stability) — peignez un masque avec l'outil pinceau, entrez un prompt, et appliquez ; et **éditeurs à instructions sans masque** (p. ex. Qwen-Image-Edit, une fois déployés) — décrivez simplement le changement en mots, aucun masque nécessaire. Les contrôles du pinceau se cachent automatiquement pour un modèle sans masque. Choisissez le modèle d'édition et appliquez — chaque édition crée une nouvelle version, et toutes les versions précédentes restent conservées et consultables.
  - **Précédent / Suivant** — boutons fléchés et gauche/droite au clavier pour naviguer dans la liste sans fermer la visionneuse.
  - **Métadonnées complètes** : prompt original, prompt amélioré par l'IA, prompt de génération, prompt négatif, style, type d'asset, modèle d'image (noms conviviaux), dimensions, graine, ID du lot, index option/variation, statut de déclaration IP, nom de fichier, et date de création.
- **Snapshot de style** : Chaque asset stocke un instantané du style utilisé au moment de la génération (nom, description, indications, analyse). Si le style original est supprimé plus tard, l'asset conserve le contexte complet. Rétrocompatible — les anciens assets sans snapshots s'affichent normalement.

### 📝 6.9 Entrée vocale

Cliquez sur le bouton microphone à côté de l'éditeur de prompt pour dicter votre prompt. L'audio est envoyé à Nova Sonic pour transcription.

> [!NOTE]
> La transcription vocale nécessite l'API de streaming bidirectionnel de Nova Sonic, qui dépend d'une version compatible de boto3 et de l'accès au modèle activé dans us-east-1. Si l'API de streaming n'est pas disponible, le service renvoie un accusé de réception placeholder. La transcription complète en temps réel fonctionne lorsque le streaming Nova Sonic est correctement configuré.

### 📝 6.10 Préservation de l'état des vues

Ordre de navigation : **Bibliothèque de styles → Studio Image → Studio de Texte → Studio Vidéo → Galerie**. Passer d'une vue à l'autre préserve l'état DOM de chaque vue. Les résultats générés, les saisies de formulaire et les positions de défilement survivent à la navigation. Le bouton de réinitialisation ambre dans le Studio Image et le Studio Vidéo est le seul moyen d'effacer leur état.

### 📝 6.11 Gestion des modèles

Toute la configuration des modèles d'IA est centralisée dans `backend/model_registry.json` — la source de vérité unique. Modèles, régions, tarifs, niveaux de qualité et templates de format sont tous stockés ici et gérés via l'UI ou l'API :

- Cliquez sur **« Paramètres du modèle »** dans la barre latérale de n'importe quel studio pour ouvrir la modale d'administration — elle s'ouvre sur l'onglet pertinent pour ce studio.
- **9 onglets** organisés par studio :
  - **Studio Image** — Modèles de génération d'images (p. ex. SD 3.5 Large, Stable Image Ultra, Stable Image Core, plus FLUX, HunyuanImage, Qwen-Image auto-hébergés), régions, niveaux de qualité, limites de prompt, sévérité de modération
  - **Studio Vidéo** — Modèles vidéo (p. ex. Luma Ray), paramètres de bucket S3, régions, tarifs
  - **Studio de Chat** — Modèles chat/LLM découverts, fenêtres de contexte, capacité vision, tarif par 1K tokens
  - **Studio de Texte** — Modèle LLM pour la génération de mise en page de texte (LLM complexe ou LLM rapide)
  - **Studio Partagé** — Catégories LLM inter-studios (LLM rapide, LLM complexe, LLM de secours, Transcription vocale), modèles de post-traitement (suppression de l'arrière-plan, agrandissement)
  - **Modèles Personnalisés** — le catalogue de modèles auto-hébergés : déployer, surveiller et démanteler les endpoints SageMaker (voir section 6.12)
  - **Modèles de Prompt** — 28 prompts directifs LLM éditables organisés en 6 sections de workflow (voir section 4.4)
  - **JSON du registre** — Éditeur JSON brut pour le registre complet des modèles
  - **Maintenance** — état des outils gérés (p. ex. le Blender headless utilisé pour l'export FBX/USD : chemin, version, mise à jour à la demande)
- Toutes les sections sont **repliables** avec des bascules **Tout afficher / Tout masquer** pour une navigation rapide.
- Les catégories LLM et le post-traitement utilisent des **sélecteurs de modèles en menu déroulant** (peuplés à partir des modèles découverts) — pas des champs de texte bruts.
- **Synchroniser depuis AWS** : Scanne toutes les régions AWS supportées par Bedrock (découvertes dynamiquement), auto-enregistre les nouveaux modèles d'image, vidéo et **chat**, met à jour la disponibilité régionale, récupère les tarifs par modèle depuis l'API AWS Pricing, et désactive les modèles qui ne sont plus disponibles. Une **superposition de progression en direct** streame chaque région au fur et à mesure de son scan. C'est la **seule** action qui appelle les API de découverte AWS — toutes les autres opérations lisent depuis le registre en cache.
- **Toujours sur le Claude le plus récent** : Chaque Sync fait automatiquement rouler votre **LLM rapide** vers le Claude Sonnet le plus récent et votre **LLM complexe** vers le Claude Opus le plus récent disponible dans votre compte, pour que vous ne soyez jamais bloqué sur un modèle déprécié — aucune config manuelle nécessaire. Si vous choisissez manuellement un modèle spécifique pour une catégorie, il est **épinglé** et le roulement automatique le laisse tranquille (il vous notifie simplement quand un plus récent apparaît).
- **Découverte de modèles personnalisés** : Le Sync découvre aussi les **modèles personnalisés fine-tunés** (`ListCustomModels`), les **modèles importés** (`ListImportedModels`), et les modèles avec **déploiements on-demand** (`ListCustomModelDeployments`) ou **throughput provisionné** (`ListProvisionedModelThroughputs`). Les modèles personnalisés héritent automatiquement de leur famille de format du modèle de base.
- **Auto-découverte** : Les nouveaux modèles de fondation sont enregistrés avec `enabled=true` — l'administrateur peut les désactiver. Les modèles existants voient leurs `available_regions` et métadonnées Bedrock (modalités, cycle de vie, ARN) mis à jour automatiquement.
- **Boîtes de dialogue de confirmation stylisées** : Toutes les actions destructrices (Sync, delete, reset) utilisent des modales personnalisées stylisées — pas de popups `confirm()` du navigateur.
- Les changements sont persistés immédiatement dans `model_registry.json` via l'Admin API.
- Le registre est rétrocompatible — les assets existants référencent des clés de modèles (par ex. `sd35_large`), pas des IDs de modèles Bedrock bruts.

### 📝 6.12 Modèles auto-hébergés (Modèles Personnalisés sur Amazon SageMaker)

ArtSmoker peut déployer des modèles d'IA open source sur **Amazon SageMaker** dans votre propre compte AWS, étendant vos capacités au-delà de ce qu'offre Amazon Bedrock. Ceux-ci fonctionnent aux côtés des modèles Bedrock et apparaissent dans les mêmes menus déroulants des studios.

**Catalogue de modèles extensible :** Livré avec un catalogue intégré de modèles open source couvrant la génération d'images, l'upscaling, la suppression d'arrière-plan, l'estimation de profondeur, la segmentation et la vidéo. Ajouter un nouveau modèle ne nécessite qu'une entrée de catalogue — aucun changement de code. Vous pouvez aussi ajouter des modèles personnalisés via l'UI (+ Ajouter un Modèle). Le catalogue et les modèles disponibles évoluent au fil du temps.

**Options de déploiement :**
- **Asynchrone (mise à zéro)** — payez uniquement quand vous générez. Se met à l'échelle à zéro en veille (0$ de coût), monte en charge automatiquement à la nouvelle requête. Démarrage à froid ~5-10 min.
- **Toujours actif** — réponses instantanées, ~$1.41/h (ml.g5.xlarge)

**Comment déployer :** Paramètres des modèles → onglet Modèles Personnalisés → cliquez sur Déployer. Le conteneur SageMaker télécharge les poids du modèle directement depuis HuggingFace au démarrage — aucun téléchargement local de plusieurs Go requis.

**CPU offloading :** Les grands modèles de diffusion utilisent un offloading CPU intelligent pour tenir sur des instances GPU plus petites. L'entrée de catalogue de chaque modèle spécifie la stratégie — `model_cpu_offload` (garde les couches actives sur le GPU) ou `sequential_cpu_offload` (offload agressif couche par couche pour les très grands modèles). Appliqué automatiquement par le gestionnaire d'inférence.

**Génération asynchrone avec Tâches en attente :** Les modèles auto-hébergés génèrent de manière asynchrone. Un panneau **Tâches en attente** apparaît dans le Studio Image montrant les tâches actives avec des indicateurs de progression. Les images terminées arrivent dans la Galerie automatiquement — aucun polling ni rafraîchissement de page nécessaire.

**Gestion des jetons HuggingFace :** Les modèles à accès restreint nécessitent un jeton HuggingFace en lecture seule. Le jeton est stocké chiffré dans **AWS Secrets Manager** de votre compte, géré via l'UI (définir/mettre à jour/supprimer), et partagé entre tous les modèles qui en ont besoin. Les jetons sont automatiquement nettoyés lorsque vous démantelez tous les modèles.

**Pré-vérification d'accès restreint :** Avant un déploiement à accès restreint, la boîte de dialogue sonde **chaque** dépôt HuggingFace que le modèle télécharge (ses propres poids plus toute dépendance) à l'aide de votre jeton stocké, et affiche un ✓/✗ par dépôt avec l'étape suivante exacte — accepter la licence de *ce* dépôt sur HuggingFace, ou ajouter un jeton. Le déploiement reste bloqué tant que chaque dépôt requis n'est pas accessible, de sorte qu'une acceptation de licence oubliée échoue rapidement dans la boîte de dialogue au lieu de plusieurs minutes après le début d'un démarrage à froid.

**Configuration :** Ajoutez les permissions Amazon SageMaker et Secrets Manager au **même rôle IAM** que vous utilisez déjà pour Bedrock — aucun rôle séparé ni variable d'environnement nécessaire. ArtSmoker découvre automatiquement votre rôle sur EC2/ECS, ou auto-crée un `ArtSmokerSageMakerRole` si besoin.

```bash
# Ajouter les permissions Amazon SageMaker à votre rôle ArtSmoker existant (une seule commande)
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
```

**Dépendance Python :** `huggingface_hub>=0.23` (installer avec `pip install huggingface_hub`)

### 📝 6.13 Modèles de génération d'images et de vidéos

Tous les modèles sont **découverts dynamiquement** depuis le registre — pas codés en dur. Le menu déroulant du Studio Image est peuplé depuis `GET /api/admin/models/image-options` et celui du Studio Vidéo depuis `GET /api/admin/models/video-options` au chargement de la page. Tout modèle enregistré et activé dans le registre apparaît automatiquement.

Le menu déroulant **Modèle d'image** est la sélection principale. En dessous, une ligne de résumé intelligente affiche la région active, le niveau de qualité et le coût par image. Une section **Avancé** extensible permet de surcharger :

- **Qualité** — les modèles qui supportent des niveaux de qualité (une répartition de prix Standard/Premium) affichent un menu déroulant ; les modèles sans niveaux affichent « Par défaut ». Les niveaux sont déclarés par modèle dans le registre via `quality_options`.
- **Région** — affiche les régions où le modèle sélectionné est disponible, triées du moins cher au plus cher avec les tarifs. « Auto » sélectionne la région la moins chère.

Une **estimation des coûts** se met à jour dynamiquement en fonction de toutes les sélections (modèle × qualité × région × options × variations).

**Familles de format** : Les modèles sont invoqués via un invocateur générique qui lit les templates de requête depuis le registre (`format_families`) — génération, édition, post-traitement et vidéo sont entièrement pilotés par templates. Ajouter un nouveau modèle d'image Bedrock ne nécessite **aucun changement de code** : enregistrez-le simplement (via l'auto-découverte ou l'Admin API) avec la bonne famille de format. Le catalogue complet des familles se trouve dans [SPEC.md](SPEC.md).

**Ingénierie de prompts optimisée par modèle** : Les prompts sont automatiquement structurés en légendes descriptives (pas en commandes) selon la [documentation AWS](https://docs.aws.amazon.com/nova/latest/userguide/prompting-image-generation.html). Les mots de négation sont retirés du prompt principal et les termes d'exclusion sont envoyés comme un **prompt négatif** distinct. Le prompt est tronqué au `prompt_limit` spécifique de chaque modèle depuis le registre.

> [!NOTE]
> **La sensibilité de modération varie selon le modèle** et est suivie dans le registre (`moderation_strictness`). Les modèles Amazon Bedrock Stability (p. ex. SD 3.5 Large, Stable Image Ultra, Stable Image Core) appliquent la modération de la plateforme AWS et sont réglés en « modérée » ; les modèles auto-hébergés (p. ex. FLUX, HunyuanImage, Qwen-Image) s'exécutent dans votre propre compte sans filtre de contenu imposé par la plateforme. ArtSmoker gère les blocages automatiquement — quand un prompt est rejeté, le système essaie des modèles alternatifs ordonnés par sévérité avant de suggérer une réécriture.

## 📌 7. Stack technique

| Couche | Technologie |
|--------|-------------|
| Backend | FastAPI (Python 3.12–3.14), boto3, Pydantic |
| Frontend | Vanilla JS, Tailwind CSS (CDN) |
| IA (LLM) | LLM rapide et LLM complexe — basculés automatiquement à chaque Sync vers les Claude Sonnet et Opus les plus récents |
| IA (Image) | Modèles d'image Amazon Bedrock trouvés par Sync (p. ex. Stable Diffusion 3.5 Large, Stable Image Ultra, Stable Image Core) ; catalogue auto-hébergé sur SageMaker (p. ex. FLUX.2/FLUX.1, HunyuanImage 3.0, Qwen-Image) |
| IA (Post-traitement) | Modèles d'édition Amazon Bedrock (p. ex. Stability AI Remove Background, Creative Upscale) |
| IA (Chat) | Tous les LLM de chat trouvés par Sync, via Bedrock ConverseStream ou Mantle (p. ex. Claude, Nova, Llama, Mistral) |
| IA (Vidéo) | Modèles vidéo Amazon Bedrock trouvés par Sync (p. ex. Luma AI Ray v2, jusqu'à 9 s) |
| IA (Voix) | Amazon Nova Sonic, version active la plus récente (voix vers texte via streaming bidirectionnel) |
| i18n | Fonction t() personnalisée, 9 langues, traduction DOM par recherche inversée |
| Conversion SVG | vtracer (principal), potrace (fallback), Pillow (dernier recours) |
| Rendu texte | Pillow (ombre, contour, effets de lueur) |
| Stockage | Système de fichiers local (interface compatible S3) |
| Dev | Middleware no-cache pour les fichiers statiques ; journalisation d'erreurs côté client via `POST /api/log` |

Aucune étape de build requise pour le frontend.

## 📌 8. Modèle de sécurité

ArtSmoker est conçu comme un **outil de développement local/réseau de confiance** — il fonctionne sur la machine du développeur ou sur une instance EC2 privée. Le modèle de sécurité reflète cela :

- **Pas d'authentification** — tous les endpoints API sont ouverts. Approprié pour le développement local et les déploiements d'équipe privés.
- **Les autres sites web ne peuvent pas se servir de votre navigateur pour l'atteindre** — ArtSmoker refuse les requêtes qu'un autre site web émet via votre navigateur (requêtes intersites et noms d'hôte inconnus, c.-à-d. DNS rebinding), si bien qu'une page que vous visitez ne peut ni lire vos assets ni lancer de tâches sur votre compte. Vous y accédez par un nom DNS ? Ajoutez ce nom à `ARTSMOKER_ALLOWED_HOSTS` (voir [Limites configurables](#-11-limites-configurables)).
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
| **Génération** | |
| `POST /api/generate/` | Générer des assets (options × variations) avec streaming SSE |
| `POST /api/generate/post-process` | Appliquer un traitement aux assets existants |
| `POST /api/generate/edit` | Édition d'image : retouche (inpaint), extension (outpaint), effacement (erase), rechercher-remplacer (search-replace), etc. Accepte l'image source, le masque, le prompt, le modèle. |
| `POST /api/generate/suggest-edit-prompt` | IA « Générer un prompt » pour l'onglet Modifier : lit l'image + le prompt original et renvoie un prompt d'édition pour un mode donné, formaté pour le modèle d'édition cible (légende vs. instruction) |
| `POST /api/generate/analyze-moderation` | Analyser un prompt bloqué par la modération et suggérer une réécriture sûre |
| **Styles** | |
| `POST /api/styles/` | Créer un profil de style |
| `POST /api/styles/{id}/import` | Importer en masse des références depuis un dossier local ou un URI S3 |
| `POST /api/styles/{id}/analyze` | Déclencher l'analyse de style par l'IA |
| **Prompt** | |
| `POST /api/refine-prompt/` | Aperçu d'un prompt affiné |
| `POST /api/transcribe/` | Voix vers texte (Nova Sonic) |
| **Galerie** | |
| `GET /api/gallery/` | Parcourir les assets générés (supporte la pagination limit/offset) |
| `GET /api/gallery/batch/{batch_id}` | Reconstruire la structure complète options × variations d'un lot |
| `DELETE /api/gallery/` | Supprimer des assets en masse |
| **Studio de Texte** | |
| `POST /api/type-studio/preview` | Rendre l'aperçu de la superposition de texte |
| `POST /api/type-studio/suggest` | Suggestion de mise en page IA pour le texte |
| `GET /api/type-studio/fonts` | Lister les polices disponibles |
| **Navigation** | |
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
| **Vidéo** | |
| `POST /api/video/generate` | Démarrer une tâche de génération vidéo asynchrone |
| `GET /api/video/status/{job_id}` | Interroger le statut d'une tâche de génération vidéo |
| `GET /api/video/jobs` | Lister toutes les tâches de génération vidéo |
| `GET /api/video/{id}/mp4` | Servir le fichier vidéo MP4 |
| `GET /api/video/{id}/thumbnail` | Servir la vignette vidéo |
| `DELETE /api/video/{id}` | Supprimer une vidéo |
| **Administration** | |
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
| **Système** | |
| `POST /api/log` | Journalisation d'erreurs/avertissements côté client (enregistrée en `[CLIENT]` dans la console serveur) |
| `GET /api/health` | Health check + validation des identifiants AWS/Bedrock |

## 📌 10. Structure du projet

```
ArtSmoker/
├── backend/
│   ├── main.py              # Application FastAPI, validation au démarrage, montage statique
│   ├── config.py            # Paramètres (régions AWS, ID de modèles, chemins, limites)
│   ├── model_registry.json  # Source de vérité unique : modèles, régions, tarifs, familles de format, niveaux de qualité
│   ├── requirements.txt
│   ├── prompt_templates.json # Prompts directifs LLM éditables — source de vérité à l'exécution (28 modèles de prompt)
│   ├── routers/
│   │   ├── generate.py      # Génération d'assets à deux niveaux + streaming SSE + guidée par référence
│   │   ├── generate_3d.py   # Image vers 3D : génération, vérification de la source, variantes, tâches asynchrones
│   │   ├── custom_deploy.py # Déploiement/démantèlement des modèles auto-hébergés (Amazon SageMaker)
│   │   ├── styles.py        # CRUD des profils de style + import répertoire/S3 + analyse
│   │   ├── gallery.py       # Navigation des assets + service des fichiers + exports moteur + suppression en masse
│   │   ├── typestudio.py    # Studio de Texte : superposition de texte, service des polices, mise en page IA
│   │   ├── video.py         # Génération vidéo (asynchrone), suivi des tâches, service MP4/vignettes
│   │   ├── chat.py          # Studio de Chat : streaming LLM, sessions, export, compactage du contexte
│   │   ├── browse.py        # Explorateur fichiers/S3 côté serveur pour l'import de références
│   │   ├── refine.py        # Aperçu de l'affinage du prompt + aperçu de la traduction
│   │   ├── transcribe.py    # Transcription vocale
│   │   └── admin.py         # Gestion du registre des modèles + découverte Bedrock + modèles de prompt
│   ├── services/
│   │   ├── bedrock_client.py     # Client Bedrock partagé avec pool de connexions
│   │   ├── model_registry.py     # Registre des modèles : charge/enregistre model_registry.json
│   │   ├── prompt_engineer.py    # Claude : affinage du prompt + génération de concepts
│   │   ├── image_generator.py    # Aiguille vers Bedrock (SD 3.5 / Ultra / Core) ou SageMaker (FLUX / Hunyuan / Qwen)
│   │   ├── style_analyzer.py     # Analyse de style en deux phases (cohésion + complète)
│   │   ├── post_processor.py     # Stability AI : suppression d'arrière-plan, agrandissement ; vtracer : SVG
│   │   ├── transcriber.py        # Nova Sonic : transcription vocale en streaming
│   │   ├── import_dedup.py       # Dédoublonnage intelligent (rotations, animations, dossiers)
│   │   ├── texture_extractor.py  # Extraction de textures glTF/GLB
│   │   ├── prompt_translator.py  # Détection automatique de la langue + traduction en anglais
│   │   ├── prompt_templates.py   # Prompts directifs LLM éditables (chargement/enregistrement/validation)
│   │   ├── video_generator.py   # Vidéo : invocation Bedrock asynchrone, téléchargement S3, vignettes ffmpeg
│   │   ├── cost_tracker.py      # Accumulateur de coûts par requête
│   │   ├── custom_models.py    # Catalogue de modèles auto-hébergés (extensible)
│   │   ├── async_jobs.py       # File de tâches de génération asynchrones (panneau Tâches en attente)
│   │   ├── reference_analyzer.py # Analyse visuelle « Inspiré de la référence »
│   │   ├── mesh_export.py      # Exports 3D prêts pour le moteur via un Blender headless géré
│   │   ├── sagemaker_deployer.py # Gestion des endpoints Amazon SageMaker (récupération directe depuis HF pour les modèles HF)
│   │   └── sagemaker_invoker.py  # Aiguille l'inférence vers les endpoints Amazon SageMaker
│   ├── models/
│   │   ├── style_profile.py       # StyleProfile, AnalyzedStyle, Create/Update
│   │   ├── generation_request.py  # Enums GenerationRequest, AssetType, ImageModel
│   │   └── generation_result.py   # GenerationResult, OptionResult, VariantResult
│   └── storage/
│       └── local_store.py         # Système de fichiers local (interface compatible S3)
├── frontend/
│   ├── index.html           # Point d'entrée de la SPA
│   ├── css/styles.css       # Thème sombre + animations
│   └── js/
│       ├── app.js               # Routeur SPA + cache DOM + navigation + showConfirm()
│       ├── i18n/
│       │   ├── i18n.js          # Cœur : fonction t(), changement de langue, recherche inversée
│       │   ├── en.json          # Anglais (base) — ~1 500 clés
│       │   └── ja/zh/ko/hi/ru/fr/es/de.json   # 8 traductions
│       ├── services/api.js      # Client de l'API backend
│       └── components/
│           ├── ImageStudio.js   # Studio Image (options × variations, multi-modèle)
│           ├── TypeStudio.js    # Studio de Texte (superposition de texte)
│           ├── VideoStudio.js   # Studio Vidéo (génération texte-vers-vidéo)
│           ├── ChatStudio.js    # Studio de Chat (chat LLM multi-modèle)
│           ├── Gallery.js       # Grille de la Galerie + recherche + opérations en masse
│           ├── StyleLibrary.js  # Gestion des styles + explorateur de fichiers
│           ├── AssetViewer.js   # Aperçu en taille réelle, retouche, 3D, exports, métadonnées
│           ├── ModelSettings.js # Interface d'administration du registre des modèles (modale)
│           ├── PromptEditor.js  # Éditeur de prompt à deux zones + composition
│           ├── PromptDesigner.js # Décomposition structurée du prompt (champs verrouiller/varier)
│           ├── ReferenceStudio.js # Onglet Inspiration image (génération guidée par référence)
│           └── VoiceInput.js    # MediaRecorder + transcription
├── data/
│   ├── styles/              # Profils de style + images de référence (liens symboliques)
│   ├── images/              # Assets générés (PNG + SVG + metadata.json)
│   ├── video/               # Assets vidéo (MP4 + vignettes + métadonnées des tâches)
│   └── chat/                # Sessions de chat (un JSON par session)
├── tools/                   # Blender portable géré (téléchargé automatiquement ; ignoré par git)
├── SPEC.md                  # Spécification technique complète (plan de reconstruction)
└── README.md                # Version anglaise de ce fichier
```

## 📌 11. Limites configurables

Les paramètres de `backend/config.py` peuvent être surchargés via des variables d'environnement (préfixe `ARTSMOKER_`) :

| Paramètre | Variable d'env | Défaut | But |
|-----------|----------------|--------|-----|
| `max_reference_images` | `ARTSMOKER_MAX_REFERENCE_IMAGES` | 100 | Nombre max d'images importées par style |
| `max_analysis_images` | `ARTSMOKER_MAX_ANALYSIS_IMAGES` | 20 | Nombre max d'images envoyées à l'IA par appel d'analyse |
| `aws_region_models` | `ARTSMOKER_AWS_REGION_MODELS` | us-west-2 | Région pour les modèles Claude + Stability AI |
| `aws_region_images` | `ARTSMOKER_AWS_REGION_IMAGES` | us-east-1 | Région pour Amazon (voix Nova Sonic) |
| `aws_profile` | `ARTSMOKER_AWS_PROFILE` | None | Nom du profil AWS (utilise la chaîne par défaut si non défini) |
| `allowed_hosts` | `ARTSMOKER_ALLOWED_HOSTS` | *(vide)* | Noms d'hôte supplémentaires auxquels le serveur répond, séparés par des virgules (`.example.com` autorise les sous-domaines ; `*` désactive la vérification). Toujours autorisés : localhost, toute adresse IP et le nom d'hôte de cette machine |
| `cors_origins` | `ARTSMOKER_CORS_ORIGINS` | *(vide)* | Autres origines web autorisées à appeler l'API depuis un navigateur, séparées par des virgules. Aucune n'est nécessaire : ArtSmoker sert sa propre interface |
| `auto_update` | `ARTSMOKER_AUTO_UPDATE` | true | Mise à jour avec contrôle de version au démarrage + vérification périodique 24h (git ou tarball), puis redémarrage sur place |

Réduire `max_analysis_images` réduit les coûts de vision IA par analyse. Réduire `max_reference_images` limite le stockage. Les deux peuvent être ajustés selon le budget.

## 📌 12. Tarification Amazon Bedrock et ventilation des coûts

> [!IMPORTANT]
> **Les modèles sont dépréciés et changent rapidement.** De nouveaux modèles sortent et les anciens sont retirés fréquemment, si bien que tout nom de modèle ou tarif codé en dur dans la documentation devient vite obsolète. ArtSmoker gère cela automatiquement — chaque exécution de **Synchroniser depuis AWS** redécouvre la gamme de modèles actuelle, bascule automatiquement les emplacements LLM partagés vers les Claude Sonnet/Opus les plus récents, et rafraîchit les tarifs en direct par modèle depuis l'API AWS Pricing dans `model_registry.json`. **L'application fait autorité** — à la fois sur les modèles qui existent et sur leur coût (affiché en direct dans la barre latérale du Studio Image selon le modèle sélectionné, le niveau de qualité, la région et la taille du lot). Les noms de modèles et tous les chiffres ci-dessous ne sont que des **exemples illustratifs** (voir [À propos des noms de modèles](#about-model-names)) — confirmez toujours les modèles/tarifs actuels dans l'application ou sur la [page de tarification Amazon Bedrock](https://aws.amazon.com/bedrock/pricing/) officielle.

Les **régions d'origine par défaut** de l'application sont `us-west-2` (p. ex. Claude, Stability AI) et `us-east-1` (p. ex. Amazon Nova Sonic) ; Sync épingle chaque modèle à une Région où AWS le propose, et les prix diffèrent selon la région. Consultez également [SPEC.md](SPEC.md#14-amazon-bedrock-pricing--cost-breakdown) pour le modèle de coût.

### 📝 12.1 Tarification à l'unité

Ce qui génère des coûts, et son unité de facturation (voir l'application pour le tarif unitaire actuel) :

| Service | Facturé | Notes |
|---------|---------|-------|
| **Ingénierie de prompts LLM et chat** (LLM rapide / complexe — p. ex. Claude Sonnet / Opus, basculés vers les plus récents à la synchro) | par token entrée / sortie | Affinage de prompts, concepts, chat, analyse de style, modération |
| **Génération d'images Bedrock** (p. ex. Stable Diffusion 3.5 Large, Stable Image Ultra, Stable Image Core) | par image | Ultra ≫ SD 3.5 ≫ Core en prix ; chiffre en direct affiché dans l'application |
| **Images/3D auto-hébergés** (p. ex. FLUX, HunyuanImage, Qwen-Image, TripoSG, TRELLIS.2) | par seconde-GPU de votre instance SageMaker | Scale-to-zero à l'inactivité (0$) ; non facturé par image |
| **Post-traitement** (Remove Background, Creative Upscale) | par image | Services Stability AI |
| **Conversion SVG** | gratuit | Local (vtracer/potrace) — $0.00 |

> [!NOTE]
> Tarifs issus de la [page de tarification Amazon Bedrock](https://aws.amazon.com/bedrock/pricing/) officielle en date de mars 2026. Les tarifs peuvent changer — vérifiez toujours auprès de la source officielle avant de budgéter.

### 📝 12.2 Coûts LLM additionnels (par utilisation)

Ces appels LLM sont inclus dans le workflow de génération mais ne sont pas détaillés séparément dans les tableaux de coûts par lot ci-dessous :

| Appel | Modèle | Quand | Coût approx. |
|-------|--------|-------|--------------|
| **Pré-vérification du prompt** | LLM rapide (p. ex. Claude Sonnet) | Avant la génération (si le toggle est activé) | ~$0.005 |
| **Réécriture de modération** | LLM rapide (p. ex. Claude Sonnet) | Uniquement quand tous les modèles rejettent un prompt | ~$0.005 |
| **Mise en page (Studio de Texte)** | LLM complexe (p. ex. Claude Opus) | Chaque demande de suggestion de mise en page IA | ~$0.02–$0.05 |

Ceux-ci sont faibles — la pré-vérification et la réécriture de modération coûtent une fraction de centime chacune. La mise en page du Studio de Texte est comparable à un affinage de prompt à option unique.

### 📝 12.3 Coût de l'analyse de style (unique par style)

~**$0.14** par style (20 images envoyées au LLM complexe, p. ex. Claude Opus, + une vérification de cohésion de 8 images sur le LLM rapide, p. ex. Claude Sonnet). La vérification de cohésion ajoute ~$0.01.

### 📝 12.4 Coût de génération selon la taille du lot

Inclut l'affinage de prompts/la génération de concepts + la génération d'images :

| Scénario | Stable Image Core | Stable Diffusion 3.5 Large | Stable Image Ultra |
|----------|-------------------|----------------------------|--------------------|
| 1 option × 1 variation | ~$0.05 | ~$0.09 | ~$0.15 |
| 1 option × 5 variations | ~$0.21 | ~$0.41 | ~$0.71 |
| 5 options × 5 variations | ~$1.05 | ~$2.05 | ~$3.55 |

Les modèles SageMaker auto-hébergés (p. ex. FLUX, HunyuanImage, Qwen-Image) sont facturés au temps GPU sur votre propre instance (scale-to-zero à l'inactivité), pas par image — voir [SPEC.md](SPEC.md#14-amazon-bedrock-pricing--cost-breakdown) pour le modèle de coût de calcul.

### 📝 12.5 Options de post-traitement (par image)

| Option | Par image | 1 image | 5 images | 25 images |
|--------|-----------|---------|----------|-----------|
| Supprimer l'arrière-plan | $0.07 | $0.07 | $0.35 | $1.75 |
| Agrandir (créatif) | $0.60 | $0.60 | $3.00 | $15.00 |
| Convertir en SVG | $0.00 | $0.00 | $0.00 | $0.00 |

> [!TIP]
> **Note Creative Upscale** : Gère automatiquement la limite de charge utile de réponse de 16 Mo de Stability AI en utilisant le format de sortie JPEG en interne, puis en reconvertissant en PNG. Inclut un réessai avec backoff exponentiel pour la limitation d'API.

### 📝 12.6 Exemples chiffrés

| Exemple | Configuration | Coût total |
|---------|---------------|------------|
| **Le moins cher** | 1×1, Stable Image Core, aucun traitement | ~$0.05 |
| **Standard** | 1×5, Stable Diffusion 3.5 Large, Supprimer l'arrière-plan | ~$0.76 |
| **Exploration complète** | 5×5, Stable Diffusion 3.5 Large, Supprimer l'arrière-plan + SVG | ~$3.80 |
| **Premium** | 5×5, Stable Image Ultra, Supprimer l'arrière-plan + Agrandir (créatif) + SVG | ~$20.30 |

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
