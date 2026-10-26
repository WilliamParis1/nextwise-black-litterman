# Portefeuille et convictions initiales

Les 23 lignes demandées remplacent entièrement le portefeuille initial. `symbol` conserve le code fourni ; `ticker` est la correspondance Yahoo proposée avec place de cotation. **Les correspondances et les cours restent à vérifier en direct** : l’accès Yahoo est bloqué dans l’environnement de préparation. Les codes courts peuvent désigner des cotations ou classes différentes ; l’ISIN prévaut, notamment pour les ETF. FOHW reste à identifier par son ISIN.

## Méthode de conviction

Les vues sont des hypothèses qualitatives de départ, sans analyse des cours actuels, des dernières publications ou des multiples de valorisation. Une exposition structurelle à l’électrification ou une diversification sectorielle défensive reçoit un léger biais positif ; les thèmes cycliques, concentrés ou à levier reçoivent un biais prudent. Aucun actif ne reçoit de conviction forte par défaut.

`confidence` est la force de la vue Black-Litterman (0 à 1), **pas la probabilité de gain**, ni un score de qualité des données. Une confiance de 0,60 sur « Alléger » renforce une vue négative. « Maintien » est neutre et ne crée pas de vue, quelle que soit sa confiance renseignée. Les valeurs par actif priment sur `CONVICTION_CONFIDENCE` ; les anciens paramètres par action restent le repli pour les entrées sans `confidence`.

Les excès de rendement annuels restent ceux du modèle : Renforcer +3 %, Attente −1 %, Alléger −4 %, Maintien 0 %, ajoutés au rendement d’équilibre. Ce sont des hypothèses, pas des prévisions estimées.

## Composition

| Actif | Code fourni | Yahoo proposé | Vue | Confiance | Motif |
| --- | --- | --- | --- | --- | --- |
| Adyen | ADYEN | `ADYEN.AS` | Maintien | 40% | Croissance et concurrence ; pas de conviction directionnelle sans valorisation récente. |
| ASM International | ASM | `ASM.AS` | Maintien | 40% | Exposition cyclique aux investissements des fabricants de puces. |
| ASML Holding | ASML | `ASML.AS` | Renforcer | 55% | Position technologique différenciée, avec risques de cycle et de restrictions export. |
| Carel Industries | CRL | `CRL.MI` | Maintien | 40% | Automatisation et efficacité énergétique ; sensibilité au cycle industriel. |
| Dassault Aviation | AM | `AM.PA` | Renforcer | 50% | Exposition défense et aviation, avec concentration des contrats. |
| Eramet | ERA | `ERA.PA` | Attente | 30% | Résultats sensibles aux prix des métaux et risques opérationnels. |
| FRAETFFOHWIVXPAR | FOHW | `FOHW.PA` | Maintien | 20% | Identité à confirmer par ISIN ; aucune vue directionnelle. |
| Glanbia PLC | GL9 | `GL9.IR` | Maintien | 40% | Nutrition et ingrédients ; sensibilité aux marges et à la consommation. |
| iShares Agribusiness UCITS ETF USD (Acc) | ISAE | `ISAE.AS` | Maintien | 40% | Diversification de titres, mais exposition sectorielle cyclique. |
| iShares MSCI Taiwan UCITS ETF | ITWN | `ITWN.AS` | Attente | 35% | Concentration géographique et recoupement avec les semi-conducteurs. |
| L&G Battery Value-Chain UCITS ETF | BATT | `BATT.L` | Attente | 30% | Thématique cyclique, concurrence et sensibilité aux matières premières. |
| Legrand | LR | `LR.PA` | Renforcer | 55% | Exposition structurelle aux infrastructures électriques ; cycle du bâtiment. |
| Leonardo | LDO | `LDO.MI` | Renforcer | 50% | Exposition défense diversifiée ; risques de programmes et de contrats. |
| Leverage Shares 3x Apple ETP | 3AAP | `3AAP.L` | Alléger | 60% | Levier quotidien 3x, dépendance au chemin et concentration sur Apple. |
| MSCI World Health Care USD Acc | WHCA | `WHCA.PA` | Renforcer | 50% | Diversification sectorielle défensive ; risques réglementaires et de change. |
| Nexans | NEX | `NEX.PA` | Renforcer | 50% | Demande des réseaux électriques, avec risques de projets et d’exécution. |
| Prysmian | PRY | `PRY.MI` | Renforcer | 55% | Exposition aux câbles et réseaux ; dépendance aux investissements. |
| Schneider Electric | SU | `SU.PA` | Renforcer | 55% | Gestion de l’énergie et automatisation ; valorisation à vérifier. |
| SPDR MSCI World Consumer Staples UCITS ETF | WCOS | `WCOS.AS` | Renforcer | 50% | Diversification défensive sectorielle ; risques de marges et de change. |
| SPIE | SPIE | `SPIE.PA` | Renforcer | 50% | Services techniques et maintenance ; risques d’exécution et de coûts. |
| Technip Energies | TE | `TE.PA` | Maintien | 40% | Projets d’ingénierie énergétique ; risques de cycle et d’exécution. |
| Thales | HO | `HO.PA` | Renforcer | 55% | Défense, électronique et cybersécurité ; risques contractuels. |
| VanEck Uranium and Nuclear Technologies UCITS ETF | NUCL | `NUCL.PA` | Attente | 30% | Thématique concentrée et volatile ; risques politiques et de matières premières. |

## Données et limites

- Aucun ancien actif ou fonds de remplacement n’est conservé. Une donnée manquante ne doit pas être remplacée par une exposition différente.
- Vérifier en priorité les places et classes de FOHW, ISAE, ITWN, BATT, WHCA, WCOS et NUCL auprès des ISIN du relevé de portefeuille.
- Le portefeuille reste majoritairement actions, avec recoupements sectoriels. Les plafonds de cluster s’appliquent aux groupes définis dans `config.py` ; ils ne suppriment pas toutes les corrélations entre groupes.
- Les cotations peuvent être en EUR, GBP ou USD : le backtest existant utilise les rendements locaux sans conversion commune de devise.
- 3AAP est un ETP à levier quotidien, avec dépendance au chemin, frais et risques d’émetteur. Le backtest de ses cours ne simule pas les exigences réglementaires ni une exposition notionnelle UCITS.
- Les poids ajustés à partir de tout l’historique sont ensuite backtestés sur ce même historique : la comparaison est rétrospective, pas un test hors échantillon.

Pour ajuster une vue, modifier `action` et `confidence` dans `config.py`. Les motifs sont documentés ici pour permettre une révision explicite.
