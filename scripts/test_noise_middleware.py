"""
Script de test rapide pour le middleware d'injection de bruit.
Lance les tests unitaires et affiche un résumé.
"""
import subprocess
import sys
from pathlib import Path


def main():
    """Point d'entrée principal."""
    print("="*70)
    print(" 🧪 Tests du Middleware d'Injection de Bruit")
    print("="*70)
    print()
    
    # Path vers le fichier de test
    test_file = Path(__file__).parent.parent / "tests" / "test_noise_injection.py"
    
    if not test_file.exists():
        print(f"❌ Fichier de test non trouvé: {test_file}")
        return 1
    
    print(f"📁 Fichier de test: {test_file}")
    print()
    print("🚀 Lancement des tests...")
    print("-"*70)
    
    # Lancer pytest
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
        cwd=Path(__file__).parent.parent,
        capture_output=False
    )
    
    print()
    print("-"*70)
    
    if result.returncode == 0:
        print("✅ Tous les tests ont réussi!")
        print()
        print("💡 Prochaines étapes:")
        print("   1. Exécutez 'python examples/noise_injection_demo.py' pour voir les visualisations")
        print("   2. Utilisez le middleware dans votre code pour stress-tester vos décodeurs")
        print()
    else:
        print("❌ Certains tests ont échoué. Vérifiez les erreurs ci-dessus.")
        print()
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
