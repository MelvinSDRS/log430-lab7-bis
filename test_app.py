"""
Tests unitaires pour l'application Hello World.
"""
import io
import sys
from app import main

def test_main_output():
    """Test que la fonction main affiche bien 'Hello World!'"""
    captured_output = io.StringIO()
    sys.stdout = captured_output

    main()

    sys.stdout = sys.__stdout__
    assert captured_output.getvalue().strip() == "Hello World!"

def test_main_not_empty():
    """Test que la sortie de main n'est pas vide"""
    captured_output = io.StringIO()
    sys.stdout = captured_output

    main()

    sys.stdout = sys.__stdout__
    assert captured_output.getvalue().strip() != ""
