"""Genere le hachage d'un mot de passe pour la console IoT.

Usage (depuis la racine du projet) :
    python -m backend.scripts.hash_password

Le mot de passe est saisi sans affichage et n'est jamais ecrit sur disque.
Copiez la ligne affichee dans votre fichier .env (ignore par Git).
"""

import getpass
import sys

from backend.app.core.console_auth import hash_password


def main() -> int:
    first = getpass.getpass("Mot de passe : ")
    if len(first) < 8:
        print("Mot de passe trop court (8 caracteres minimum).", file=sys.stderr)
        return 1

    second = getpass.getpass("Confirmation : ")
    if first != second:
        print("Les deux saisies sont differentes.", file=sys.stderr)
        return 1

    print(hash_password(first))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
