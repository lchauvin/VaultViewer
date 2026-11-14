"""Le type d'un coffre, et ce que l'interface en montre.

Un coffre declare son type dans un petit manifeste, range dans le coffre
lui-meme, dans un dossier cache qu'Obsidian et l'index ignorent :

    <coffre>/.assistant/coffre.toml     le type, et d'eventuels reglages
    <coffre>/.assistant/style.css       un style propre au coffre (optionnel)

    type = "documentation"              # ou "jeu"
    statut_brouillon = "draft"          # le statut d'une page ecrite par l'assistant

    [fonctions]                         # pour activer ou couper une fonction
    cartes = true

    [libelles]                          # pour renommer ce que l'interface affiche
    titre = "Documentation PixInsight"

Sans manifeste, le coffre est un coffre de jeu : c'est le comportement
d'origine de l'outil, et un coffre existant n'a rien a changer.

Le manifeste est relu a chaque requete, comme les pages : le modifier ne
demande pas de redemarrer.
"""

from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DOSSIER = ".assistant"
MANIFESTE = "coffre.toml"
STYLE = "style.css"

TYPE_PAR_DEFAUT = "jeu"

# Les fonctions qu'un type active. Toutes sont propres au jeu de role :
#   mode_joueurs  l'ecran tourne vers la table, pages et encadres MJ masques
#   cartes        les pages `type: carte` affichees en carte interactive
#   visibilite    la metadonnee `visibilite` montree (filtre, marqueurs, pastilles)
TYPES: dict[str, dict] = {
    "jeu": {
        "fonctions": {"mode_joueurs": True, "cartes": True, "visibilite": True},
        "libelles": {
            "titre": "Assistant de MJ",
            "utilisateur": "MJ",
            "question": "Une question de regle, un PNJ a improviser, une scene a preparer…",
        },
        "statut_brouillon": "brouillon",
    },
    "documentation": {
        "fonctions": {"mode_joueurs": False, "cartes": False, "visibilite": False},
        "libelles": {
            "titre": "Lecteur de documentation",
            "utilisateur": "Vous",
            "question": "Une question sur la documentation, une notion a expliquer, une page a retrouver…",
        },
        "statut_brouillon": "brouillon",
    },
}

# Les autres noms acceptes dans le manifeste.
SYNONYMES = {
    "game": "jeu",
    "jdr": "jeu",
    "jeu-de-role": "jeu",
    "doc": "documentation",
    "docs": "documentation",
}


@dataclass
class Profil:
    type: str
    fonctions: dict[str, bool]
    libelles: dict[str, str]
    statut_brouillon: str
    # Les problemes du manifeste, affiches plutot que tus.
    avertissements: list[str] = field(default_factory=list)

    @property
    def jeu(self) -> bool:
        return self.type == "jeu"

    def a(self, fonction: str) -> bool:
        return bool(self.fonctions.get(fonction))

    def vers_json(self) -> dict:
        return {
            "type": self.type,
            "fonctions": dict(self.fonctions),
            "libelles": dict(self.libelles),
            "statut_brouillon": self.statut_brouillon,
            "avertissements": list(self.avertissements),
        }


def _depuis_type(nom: str) -> Profil:
    base = TYPES[nom]
    return Profil(
        type=nom,
        fonctions=dict(base["fonctions"]),
        libelles=dict(base["libelles"]),
        statut_brouillon=base["statut_brouillon"],
    )


def charger(racine: Path | None) -> Profil:
    """Le profil d'un coffre : son manifeste, ou le type par defaut."""
    if racine is None:
        return _depuis_type(TYPE_PAR_DEFAUT)
    fichier = Path(racine) / DOSSIER / MANIFESTE
    if not fichier.is_file():
        return _depuis_type(TYPE_PAR_DEFAUT)

    try:
        brut = tomllib.loads(fichier.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError, UnicodeDecodeError) as err:
        profil = _depuis_type(TYPE_PAR_DEFAUT)
        profil.avertissements.append("%s illisible : %s" % (fichier, err))
        print("[profil] " + profil.avertissements[-1], file=sys.stderr)
        return profil

    demande = str(brut.get("type") or TYPE_PAR_DEFAUT).strip().lower()
    nom = SYNONYMES.get(demande, demande)
    avertissements = []
    if nom not in TYPES:
        avertissements.append(
            "type de coffre inconnu : « %s » (connus : %s)" % (demande, ", ".join(TYPES))
        )
        nom = TYPE_PAR_DEFAUT
    profil = _depuis_type(nom)
    profil.avertissements = avertissements

    fonctions = brut.get("fonctions") or {}
    if isinstance(fonctions, dict):
        for cle, valeur in fonctions.items():
            if cle in profil.fonctions and isinstance(valeur, bool):
                profil.fonctions[cle] = valeur
            else:
                profil.avertissements.append("fonction ignoree : %s" % cle)

    libelles = brut.get("libelles") or {}
    if isinstance(libelles, dict):
        for cle, valeur in libelles.items():
            if cle in profil.libelles and str(valeur).strip():
                profil.libelles[cle] = str(valeur).strip()
            else:
                profil.avertissements.append("libelle ignore : %s" % cle)

    statut = str(brut.get("statut_brouillon") or "").strip()
    if statut:
        profil.statut_brouillon = statut
    return profil


def fichier_style(racine: Path | None) -> Path | None:
    """La feuille de style propre au coffre, si elle existe."""
    if racine is None:
        return None
    fichier = Path(racine) / DOSSIER / STYLE
    return fichier if fichier.is_file() else None


def version_style(racine: Path | None) -> str:
    """Change quand la feuille change : le navigateur la recharge alors."""
    fichier = fichier_style(racine)
    if fichier is None:
        return ""
    try:
        etat = fichier.stat()
    except OSError:
        return ""
    return "%d-%d" % (etat.st_mtime_ns, etat.st_size)
