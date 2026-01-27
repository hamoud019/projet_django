#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path


def validate_project():
    """Valide la configuration du projet avant execution"""
    issues = []
    
    # Vérifier les fichiers de configuration critiques
    base_dir = Path(__file__).resolve().parent
    critical_files = [
        base_dir / "project" / "settings.py",
        base_dir / "project" / "urls.py",
        base_dir / "manage.py",
    ]
    
    for file_path in critical_files:
        if not file_path.exists():
            issues.append(f"❌ Fichier manquant: {file_path.relative_to(base_dir)}")
    
    # Vérifier les dossiers essentiels
    essential_dirs = [
        base_dir / "core",
        base_dir / "project",
    ]
    
    for dir_path in essential_dirs:
        if not dir_path.exists():
            issues.append(f"❌ Dossier manquant: {dir_path.relative_to(base_dir)}")
    
    # Afficher les erreurs s'il y en a
    if issues:
        print("\n⚠️  ERREURS DE CONFIGURATION:")
        for issue in issues:
            print(f"  {issue}")
        print("\nLe projet ne peut pas être exécuté.\n")
        sys.exit(1)
    
    return True


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
    
    # Valider la structure du projet
    validate_project()
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    # Vérification Django via django check après migration/runserver
    if len(sys.argv) > 1 and sys.argv[1] in ['check', 'migrate', 'makemigrations']:
        print("🔍 Vérification du projet Django...\n")
    
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()


