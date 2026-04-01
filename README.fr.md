> Ce document est une traduction du README anglais. Pour les informations les plus récentes, consultez le [English README](README.md).

# ArtSmoker
> *Le smoke-test de vos créations artistiques !*

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green?logo=fastapi&logoColor=white)
![Amazon Bedrock](https://img.shields.io/badge/Amazon-Bedrock-orange?logo=amazonaws&logoColor=white)
![License](https://img.shields.io/badge/License-MIT--0-yellow)

## Language / 言語 / 语言 / 언어 / Langue / Idioma

ArtSmoker prend en charge 6 langues. Changez la langue de l'interface via les boutons de langue dans la barre de navigation supérieure (EN | JA | ZH | KO | FR | ES). Votre sélection est automatiquement sauvegardée.

| Langue | README |
|--------|--------|
| English | [README.md](README.md) |
| 日本語 (Japanese) | [README.ja.md](README.ja.md) |
| 中文 (Chinese) | [README.zh.md](README.zh.md) |
| 한국어 (Korean) | [README.ko.md](README.ko.md) |
| Français | Ce document |
| Español (Spanish) | [README.es.md](README.es.md) |

**Prise en charge multilingue des prompts :**
- Les prompts non anglais (japonais, chinois, coréen, français, espagnol) sont automatiquement détectés et traduits en anglais avant la génération
- Un aperçu bilingue apparaît dans la zone de prompt : basculez entre votre texte original et la traduction anglaise pour voir exactement ce que le modèle recevra
- Le prompt original, la langue détectée et la traduction anglaise sont tous conservés dans les métadonnées de l'asset
- Les noms de fichiers sont générés à partir du prompt traduit en anglais (par exemple « un bâtiment d'hôpital » → `hospital-building_opt1_var1.png`)
- Chat Studio transmet les prompts directement au LLM (sans traduction) — les modèles comme Claude sont nativement multilingues
- Le texte de Type Studio reste dans votre langue (il est rendu tel quel sur l'image)
- Toutes les vérifications de modération et le filtrage de contenu s'appliquent sur le prompt traduit en anglais, par souci de cohérence

## 📌 0. Présentation

Une interface simple et conviviale pour les artistes, dédiée aux modèles de génération d'images et de vidéos d'Amazon Bedrock. ArtSmoker permet aux équipes créatives d'utiliser Bedrock efficacement — sans avoir à apprendre l'API, le CLI ou l'ingénierie de prompts.

### 📝 Le problème

Les équipes créatives et les studios de jeux veulent utiliser l'IA pour la génération d'assets, mais font face à de véritables obstacles :

- **Pas d'interface simple** — les artistes ne devraient pas avoir à se connecter à la console Bedrock ou à écrire des appels API pour générer des images
- **L'ingénierie de prompts est difficile** — composer des prompts efficaces avec les bons prompts négatifs, les directives de style et le formatage spécifique à chaque modèle demande une expertise que la plupart des artistes n'ont pas
- **Les équipes ne construisent/entraînent pas leurs propres modèles** — elles ont besoin d'accéder aux nombreux modèles déjà disponibles sur Bedrock, via un outil qu'elles peuvent réellement utiliser
- **L'édition d'images est inaccessible** — l'inpainting, l'outpainting, la recherche et remplacement, et le transfert de style nécessitent tous des connaissances API

### 📝 La solution

ArtSmoker est une application web auto-hébergée qui enveloppe Amazon Bedrock dans une interface créative épurée. Conçu spécifiquement pour la production d'assets de jeux vidéo, il est également applicable à d'autres industries créatives telles que la publicité, le e-commerce, l'édition et les médias numériques où le contenu visuel généré par l'IA a de la valeur.

- **Les artistes décrivent simplement ce dont ils ont besoin** en langage naturel — ArtSmoker gère la composition des prompts, l'extraction des prompts négatifs, le formatage spécifique aux modèles et l'application des styles en coulisses
- **Génération guidée par le style** — téléchargez l'art existant de votre jeu, et les modèles de vision d'ArtSmoker apprennent votre identité visuelle. Chaque asset généré correspond à l'apparence et à l'atmosphère de votre jeu
- **Tous les modèles Bedrock, toutes les régions** — entièrement configurable. Choisissez vos modèles text-to-image, modèles vidéo et régions. Le système découvre dynamiquement les modèles disponibles via l'API Bedrock
- **Auto-déployé, auto-facturé** — fonctionne sur votre propre infrastructure, utilise votre propre compte AWS. Pas d'endpoints partagés, pas d'accès tiers aux données, pas de factures surprises de services externes

Construit sur Amazon Bedrock : Claude Sonnet/Opus (ingénierie de prompts et chat), Nova Canvas, Titan Image, Stable Diffusion 3.5 Large, Stable Image Ultra, Stability AI (édition d'images), Nova Reel, Luma AI Ray (génération vidéo), plus 80+ LLM de 16 fournisseurs pour Chat Studio.

**[Commencer maintenant — aller aux prérequis et installation ▸](#get-started)**

## 📌 1. Fonctionnalités

ArtSmoker fonctionne en deux modes — **autonome** (aucune configuration de style ou de thème nécessaire, décrivez et générez simplement) et **guidé par le style** (téléchargez votre art existant, et chaque génération correspond à votre identité visuelle). Les deux modes utilisent les mêmes studios et le même pipeline de génération.

### 📝 Mode autonome (démarrage rapide)

Aucune configuration de style ou de thème nécessaire — ouvrez le 2D Image Studio, le Video Studio ou le Type Studio et commencez à créer immédiatement.

1. **Décrivez ce dont vous avez besoin** — saisissez un prompt comme « hospital building » ou « fire mage character », ou utilisez l'entrée vocale. L'IA améliore automatiquement votre prompt avec les directives de composition appropriées, les prompts négatifs et le formatage spécifique au modèle.
2. **Choisissez votre modèle et vos paramètres** — sélectionnez parmi tous les modèles text-to-image disponibles sur Amazon Bedrock, choisissez les dimensions, le niveau de qualité et la région. Ou utilisez « All Available Models » pour générer simultanément sur tous les modèles activés et comparer côte à côte.
3. **Obtenez plusieurs options** — le système génère jusqu'à 5 concepts créatifs distincts, chacun avec jusqu'à 5 variations de seed (25 images au total). Choisissez celle qui vous plaît.
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
- 🖼️ **2D Image Studio** — Générez des images avec options × variations, éditeur de prompt à deux zones
- 🎬 **Video Studio** — Text-to-video avec Nova Reel & Luma Ray, multi-shot, image-to-video
- ✍️ **Type Studio** — Superpositions de texte conçues par l'IA avec sélecteur de polices
- 💬 **Chat Studio** — Chat LLM multi-modèle avec streaming, Markdown, coloration syntaxique, vision, sessions, compactage de contexte
- 📁 **Galerie unifiée** — Parcourez images + vidéos, filtre par média, recherche, téléchargement, suppression
- ✏️ **Édition d'images** — Inpainting, outpainting, effacement, recherche et remplacement, recoloration (dans l'AssetViewer)
- 🔄 **Progression en temps réel** — Streaming SSE avec visibilité des tentatives/limitations
- 🛡️ **Modération intelligente** — Test canari, changement automatique de modèle, réécriture assistée par l'IA
- ⚙️ **Model Registry** — Interface d'administration organisée par studio (Image, Video, Chat, Type, Shared), découverte Bedrock, support des modèles personnalisés
- 📝 **Prompt Templates** — 14 prompts directifs LLM éditables, amélioration assistée par l'IA, validation de variables avec correction automatique
- 📦 **Versionnement des assets** — Édition sur place avec historique des versions (v1, v2, ...) et navigation entre versions
- 💰 **Suivi des coûts** — Dépenses AWS estimées par requête, par session, par asset — envoyées à la télémétrie PulseBoard
- 🌐 **i18n en 6 langues** — Traduction complète de l'UI (EN, JA, ZH, KO, FR, ES), détection automatique des prompts non anglais, aperçu bilingue
- 🔍 **Support des modèles personnalisés** — Découverte automatique des modèles Bedrock fine-tunés, importés et déployés

### 📝 1.2 Captures d'écran

**2D Image Studio** — Paramètres à gauche, prompt avec amélioration IA à droite, résultats de comparaison de modèles en dessous. Le mode All Available Models génère simultanément sur tous les modèles d'image activés.

![2D Image Studio — Paramètres, prompt et résultats générés](docs/images/image-studio-top.png)

![2D Image Studio — Comparaison de modèles, options de post-traitement et aperçu complet](docs/images/image-studio-bottom.png)

**Style Library** — Téléchargez l'art existant de votre jeu, l'IA analyse le style visuel et produit un guide de prompts riche en métadonnées. Les images de référence sont affichées avec l'analyse IA complète et le profil de style JSON.

![Style Library — Analyse de style IA avec images de référence](docs/images/style-library-top.png)

![Style Library — Images de référence, options d'importation et données d'analyse](docs/images/style-library-bottom.png)

**Galerie** — Vue unifiée de toutes les images et vidéos générées avec filtre par type de média, filtre par style, recherche et tri. Cliquez sur n'importe quel asset pour ouvrir la vue complète.

![Galerie — Grille d'assets générés avec filtres](docs/images/gallery.png)

**Asset Viewer et édition d'images** — Aperçu en taille réelle avec zoom/panoramique, onglet Édition pour l'inpainting (peinture de masque + prompt), historique des versions et téléchargement PNG/SVG.

![Asset Viewer — Édition d'image avec inpainting](docs/images/asset-viewer-edit.png)

**Video Studio** — Paramètres à gauche (modèle, mode de génération, durée, région, estimation des coûts), prompt à droite. Prend en charge Nova Reel (plan unique, multi-shot auto/manuel jusqu'à 2 minutes) et Luma AI Ray (rapports d'aspect, boucle).

![Video Studio — Paramètres et prompt](docs/images/video-studio.png)

![Video Studio — Génération en cours avec prompt amélioré par l'IA](docs/images/video-studio-generating.png)

![Video Studio — Vidéo terminée avec vignette et vidéos récentes](docs/images/video-studio-completed.png)

**Lecteur vidéo** — Cliquez sur une vidéo pour la lire en ligne avec toutes les métadonnées (prompt original, prompt amélioré par l'IA, modèle, durée, région).

![Lecteur vidéo — Lecture d'une vidéo générée avec métadonnées](docs/images/video-player.png)

### 📝 1.3 Génération à deux niveaux

Pour chaque prompt, l'IA crée des **Options** — des interprétations de design fondamentalement différentes (par exemple pour « a warrior » : berserker viking, samouraï japonais, guerrier tribal, cyber-soldat, hoplite grec). Pour chaque option, le modèle d'image produit des **Variations** — différents seeds aléatoires donnant des différences visuelles subtiles. Cela offre aux artistes une large palette créative pour faire leur choix.

### 📝 1.4 All Available Models

Sélectionnez **« All Available Models »** dans le menu déroulant des modèles pour générer votre prompt simultanément sur tous les modèles d'image activés — une image par modèle. Cela permet une comparaison directe côte à côte de la façon dont Nova Canvas, Titan Image, SD 3.5 Large et Stable Image Ultra interprètent chacun le même prompt. Chaque modèle s'exécute indépendamment : si un modèle plus strict bloque le prompt, vous obtenez quand même les résultats des modèles qui l'ont accepté, avec des labels de statut clairs (succès, bloqué par la modération, ou échec) sur chaque carte d'option.

Le toggle optionnel **« Model-optimized prompts »** adapte le prompt aux forces de chaque modèle au lieu d'envoyer le même prompt à tous — utile quand vous voulez le meilleur résultat de chaque modèle plutôt qu'une comparaison directe.

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

Pour les permissions IAM détaillées, les instructions d'installation, les options de configuration et les informations tarifaires, consultez les sections 2.1.1 à 2.4, les sections 3 à 4 et les sections 11 à 12 du [README anglais](README.md).

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
│  Claude Sonnet 4.6   │  │  Nova Canvas             │
│  Claude Opus 4.6     │  │  Titan Image v2          │
│  SD 3.5 Large        │  │  Nova Sonic              │
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
| IA (LLM) | Claude Sonnet 4.6 (tâches rapides), Claude Opus 4.6 (tâches complexes) |
| IA (Image) | Nova Canvas, Titan Image v2, Stable Diffusion 3.5 Large, Stable Image Ultra |
| IA (Post-traitement) | Stability AI (Remove Background, Creative Upscale) |
| IA (Chat) | 80+ LLM de 16 fournisseurs via Bedrock ConverseStream |
| IA (Vidéo) | Nova Reel v1.0/v1.1 (jusqu'à 2 min), Luma AI Ray v2 (jusqu'à 9 s) |
| IA (Voix) | Nova Sonic (voix vers texte via streaming bidirectionnel) |
| i18n | Fonction t() personnalisée, 817 clés × 6 langues, traduction DOM par recherche inversée |
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
> N'exposez pas ArtSmoker à des réseaux non fiables sans ajouter l'authentification et les restrictions de chemins. Consultez le [plan de déploiement dans SPEC.md](SPEC.md#14-deployment--scaling-roadmap) pour les recommandations de durcissement en production.

## 📌 12. Tarification Amazon Bedrock et ventilation des coûts

> [!NOTE]
> Les tableaux ci-dessous sont des **tarifs de référence à des fins de planification**. L'application elle-même affiche les **tarifs en direct par modèle** dans la barre latérale de l'Image Studio — récupérés depuis l'API AWS Pricing lors du rafraîchissement du registre et stockés dans `model_registry.json`.

Tous les tarifs proviennent de la [page de tarification Amazon Bedrock](https://aws.amazon.com/bedrock/pricing/) (régions US). Pour plus de détails, consultez [SPEC.md](SPEC.md#13-aws-bedrock-pricing--cost-breakdown).

| Service | Modèle | Coût | Unité |
|---------|--------|------|-------|
| **Claude Sonnet 4.6** | `us.anthropic.claude-sonnet-4-6` | $3.00 entrée / $15.00 sortie | par million de tokens |
| **Claude Opus 4.6** | `us.anthropic.claude-opus-4-6-v1` | $5.00 entrée / $25.00 sortie | par million de tokens |
| **Nova Canvas** | `amazon.nova-canvas-v1:0` | $0.06 | par image |
| **Titan Image v2** | `amazon.titan-image-generator-v2:0` | $0.01 | par image |
| **Stable Diffusion 3.5 Large** | `stability.sd3-5-large-v1:0` | $0.08 | par image |
| **Stable Image Ultra** | `stability.stable-image-ultra-v1:1` | $0.14 | par image |
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
> **Aucune garantie** : Ce logiciel est fourni « tel quel » sans garantie d'aucune sorte. Consultez la [LICENSE](LICENSE) pour les conditions complètes.

## 📌 14. Spécification complète

Consultez **[SPEC.md](SPEC.md)** pour la spécification technique complète — architecture, conception des composants, configuration des modèles, référence API, modèle de sécurité, tarification, feuille de route de déploiement, et suffisamment de détails pour reconstruire le projet de zéro.
