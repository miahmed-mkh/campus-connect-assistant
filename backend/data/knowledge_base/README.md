# Base de connaissances Campus Connect

Cette arborescence contient les données pédagogiques utilisées par
l’assistant virtuel Campus Connect.

## Nature des données

Les données ont été fournies dans le cadre du projet étudiant
« Assistant virtuel Campus ».

Elles sont exclusivement destinées à la démonstration et aux tests du
projet. Elles ne constituent pas des informations officielles ou
nécessairement fiables de l’ESIC.

Les noms, coordonnées, horaires, emplois du temps, procédures, tarifs,
dates et autres informations doivent être considérés comme des données
pédagogiques de démonstration.

## Période de référence

Les documents font principalement référence à l’année académique
2024-2025. Cette période est passée au 4 octobre 2026.

L’application ne doit donc pas présenter ces informations comme étant
actuelles sans afficher leur période de référence.

## Arborescence

- `raw/` : copies intactes des sources structurées fournies ;
- `processed/` : données normalisées en UTF-8 et prêtes à être utilisées ;
- `documents/` : documents PDF sources ;
- `../../scripts/knowledge_base/` : scripts de contrôle et de
  normalisation.

## Transformations appliquées

- validation syntaxique des fichiers JSON ;
- correction structurelle de `faq_complete.json` avant import ;
- suppression des deux lignes de métadonnées non tabulaires du CSV ;
- conversion du CSV de CP1252 vers UTF-8 ;
- normalisation des fichiers JSON en UTF-8 ;
- ajout, dans la version traitée de l’emploi du temps, des matières
  référencées par les cours et disponibles dans le CSV ;
- validation des références vers les matières, enseignants et salles.

Les fichiers du dossier `raw/` ne doivent pas être modifiés directement.
Toute transformation doit produire ou mettre à jour un fichier du
dossier `processed/`.
