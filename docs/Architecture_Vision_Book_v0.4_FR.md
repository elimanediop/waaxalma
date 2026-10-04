LIVRE D’ARCHITECTURE ET DE VISION  ·  v0.4  ·  ÉDITION FRANÇAISE

# Waaxalma Architecture and Vision Book v0.4 FR

Framework Next

22 septembre 2026  ·  Framework Next

**VISION** Waaxalma (« parle pour moi ») transforme la parole, notamment en wolof, en traduction compréhensible et en audio naturel. Le produit vise à préserver l’intention ; le framework sépare agents, pipelines et capacités fournisseurs remplaçables.

## 1. Vision et périmètre

Cette édition décrit le jalon v0.4. Elle reprend le gabarit v0.4 et les capacités livrées à cette étape ; les jalons ultérieurs restent des évolutions futures dans cette édition historique.

- AgentRegistry, ProviderRegistry et PipelineRegistry rendent découverte et composition explicites.
- InterpreterAgent reçoit des pipelines texte/audio nommés. Contexte et Qualité sont agents, Skills, fournisseurs et étapes de pipeline.

### 2. Fondations construites

| Couche | Implémentation | Rôle |
| --- | --- | --- |
| API | FastAPI | Exécution générique d’agents enregistrés ; routes texte/voix. |
| Orchestration | AgentOrchestrator | Résultats, erreurs, durée et annulation. |
| Découverte | AgentRegistry / ProviderRegistry | Résolution explicite par nom et capacité. |
| Composition | PipelineRegistry / SequentialPipeline | Étapes réutilisables ordonnées. |

### 3. Principes directeurs

- Étendre par contrats, enregistrement et composition ; détecter tôt fournisseurs/pipelines inconnus.
- Les Skills dépendent de contrats de capacité. Fiabilité et observabilité restent transverses. Contexte/Qualité par défaut n’ajoutent aucun appel LLM.
- Séparer traitements Standard, transports temps réel et périphériques navigateur ; expliciter les limites de validation.


## 4. Architecture actuelle

La racine de composition assemble fournisseurs concrets, Skills, étapes, pipelines et agents. Les registres résolvent les dépendances sans ajouter d’étapes de traitement à chaque requête.

![architecture](book/assets/v0.4_architecture_FR.png)

AgentOrchestrator exécute les agents enregistrés ; InterpreterAgent reçoit ses pipelines texte/audio configurés. Les services temps réel, lorsqu’ils sont livrés, restent séparés de cette chaîne Standard.

### 5. Flux d’exécution de l’interpréteur

![standard](book/assets/v0.4_standard_FR.png)

**CONTRAT DU PIPELINE** Chaque étape reçoit PipelineState et SessionContext et retourne l’état mis à jour. SequentialPipeline attend les étapes dans l’ordre ; les workflows configurés évoluent sans réécrire InterpreterAgent.


## 6. Modèle d’extensibilité du framework

L’extension repose sur enregistrement et composition explicites, avec API générique et cœur d’orchestration préservés. Les adaptateurs fournisseurs changent derrière les contrats de capacité.

| Extension | Changement requis | Frontière préservée |
| --- | --- | --- |
| Nouvel agent | BaseAgent + AgentRegistry | API / AgentOrchestrator |
| Nouveau fournisseur | Implémenter le contrat de capacité ; enregistrer capacité + nom. | Skill / Agent / API |
| Nouveau pipeline | Composer les étapes et enregistrer le nom. | SequentialPipeline |
| Nouvelle étape | PipelineStage | InterpreterAgent / API |
| Stratégie contexte/qualité | ContextProvider / QualityProvider | Structure des étapes configurées. |

### 7. Contexte et Qualité comme capacités à part entière

- PassthroughContextProvider préserve texte source/métadonnées. TranslationStage privilégie enriched_text lorsqu’il est fourni et conserve source_text.
- DeterministicQualityProvider évalue la structure, pas la justesse sémantique. accepted, score, issues et métadonnées qualité sont retournés ; le rejet ne crée pas de blocage implicite.


## 8. Héritage de fiabilité et d’observabilité

- Les politiques retry/timeout restent centralisées lorsqu’elles sont compatibles. AgentOrchestrator normalise les erreurs et préserve l’annulation.
- ExecutionTrace décrit durées d’étape/fournisseur, résultat et erreurs. Prometheus couvre exécutions, durées et retries.


## 9. Roadmap technique

Chaque jalon s’appuie sur l’architecture précédente. Le tableau décrit les capacités livrées, sans attester un tag public non vérifié. Le périmètre futur est conservé selon le jalon historique.

| Jalon | Position dans cette édition |
| --- | --- |
| Prototype et orchestration | Fondation |
| Fiabilité | Fondation |
| Framework Next | Jalon documenté |
| Realtime Direct | Futur à cette version |
| Realtime Enhanced | Futur à cette version |
| Sortie audio universelle | Futur à cette version |
| Contrôle des périphériques | Futur à cette version |
| Product Readiness | Futur à cette version |
| Framework stable | Futur à cette version |

### 10. Carte des releases Git

| Version | Jalon |
| --- | --- |
| v0.1.0 | Prototype |
| v0.2.0 | Orchestration agents |
| v0.3.0 | Fiabilité |
| v0.4.0 | Framework Next |
| v0.4.1 | Traduction temps réel et configuration de voix |
| v0.4.2 | Streaming Realtime Enhanced |
| v0.4.3 | Sortie audio universelle et pont de conférence |
| v0.4.4 | Audio de conférence et contrôle des périphériques |
| v0.5.0 | Préparation à la production |
| v1.0.0 | Framework stable |


## 11. Critères d’achèvement v0.4

- AgentRegistry, ProviderRegistry et PipelineRegistry rendent découverte et composition explicites.
- InterpreterAgent reçoit des pipelines texte/audio nommés. Contexte et Qualité sont agents, Skills, fournisseurs et étapes de pipeline.
- Cette version ne livre pas encore Direct/Enhanced, l’isolation persistante des propriétaires ni les conteneurs de production.

- Agents Standard, sélection des fournisseurs et pipelines configurés préservent les frontières v0.4 et métadonnées Contexte/Qualité.

**PREUVES DE VALIDATION** Tests composition, unitaires, interchangeabilité, pipelines et API générique établissent les frontières.

### 12. Prochaine étape recommandée

Product Readiness : état persistant, configuration répétable, contrôles de livraison, confidentialité et observabilité de production.

### Direction de préparation à la production

État conversationnel persistant, frontières confidentialité/sécurité, settings/secrets répétables, CI/packaging et signaux de production restent la roadmap opérationnelle. L’implémentation ultérieure choisira l’isolation client, pas une authentification implicite ; ces orientations ne sont pas des garanties livrées dans cette version historique.

**PRINCIPE DU FRAMEWORK** Ajouter une capacité par enregistrement et composition sans déplacer les détails fournisseur ou conférence dans l’API/orchestration générique.
