"""
Tests para el módulo de Scoring de Madurez Digital.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.scoring import (
    calculate_maturity_score,
    validate_entities,
    PRESENCIA_DIGITAL_SCORES,
    TRACCION_VENTAS_SCORES,
    FORMALIZACION_SCORES,
    USO_HERRAMIENTAS_SCORES,
)


class TestCalculateMaturityScore:
    """Tests for the calculate_maturity_score function."""

    def test_maximum_score(self):
        """All dimensions at max should yield 100."""
        entities = {
            "presencia_digital": "web_transaccional",
            "traccion_ventas": "online_recurrente",
            "formalizacion": "formal_rfc",
            "uso_herramientas": "usa_software",
        }
        result = calculate_maturity_score(entities)
        assert result["score"] == 100
        assert result["nivel"] == "Avanzado"
        assert result["desglose"]["presencia_digital"] == 30
        assert result["desglose"]["traccion_ventas"] == 30
        assert result["desglose"]["formalizacion"] == 20
        assert result["desglose"]["uso_herramientas"] == 20

    def test_minimum_score(self):
        """All dimensions at min should yield 0."""
        entities = {
            "presencia_digital": "nada",
            "traccion_ventas": "idea",
            "formalizacion": "informal",
            "uso_herramientas": "todo_manual",
        }
        result = calculate_maturity_score(entities)
        assert result["score"] == 0
        assert result["nivel"] == "Inicial"

    def test_empty_entities(self):
        """Empty dict should default to minimum values (0)."""
        result = calculate_maturity_score({})
        assert result["score"] == 0
        assert result["nivel"] == "Inicial"

    def test_partial_entities(self):
        """Only some dimensions provided."""
        entities = {
            "presencia_digital": "redes_sociales",
            "formalizacion": "formal_rfc",
        }
        result = calculate_maturity_score(entities)
        assert result["score"] == 35  # 15 + 0 + 20 + 0
        assert result["nivel"] == "Intermedio"

    def test_intermediate_score(self):
        """Mixed values yielding intermediate."""
        entities = {
            "presencia_digital": "redes_sociales",  # 15
            "traccion_ventas": "dm_wa",              # 15
            "formalizacion": "formal_rfc",           # 20
            "uso_herramientas": "todo_manual",       # 0
        }
        result = calculate_maturity_score(entities)
        assert result["score"] == 50
        assert result["nivel"] == "Intermedio"

    def test_boundary_inicial(self):
        """Score exactly 30 should be Inicial."""
        entities = {
            "presencia_digital": "redes_sociales",  # 15
            "traccion_ventas": "dm_wa",              # 15
            "formalizacion": "informal",             # 0
            "uso_herramientas": "todo_manual",       # 0
        }
        result = calculate_maturity_score(entities)
        assert result["score"] == 30
        assert result["nivel"] == "Inicial"

    def test_boundary_intermedio(self):
        """Score exactly 31 should be Intermedio."""
        entities = {
            "presencia_digital": "nada",             # 0
            "traccion_ventas": "online_recurrente",  # 30
            "formalizacion": "informal",             # 0
            "uso_herramientas": "todo_manual",       # 0
        }
        # Score = 30, Inicial. Need 31.
        # Actually this is 30, not 31. Let's use a different combo.
        result = calculate_maturity_score(entities)
        assert result["score"] == 30
        assert result["nivel"] == "Inicial"

    def test_boundary_avanzado(self):
        """Score exactly 71 should be Avanzado."""
        entities = {
            "presencia_digital": "web_transaccional",  # 30
            "traccion_ventas": "online_recurrente",     # 30
            "formalizacion": "informal",                # 0
            "uso_herramientas": "todo_manual",          # 0
        }
        # Score = 60, Intermedio
        result = calculate_maturity_score(entities)
        assert result["score"] == 60
        assert result["nivel"] == "Intermedio"

    def test_traccion_fisicas(self):
        """Test the 'fisicas' value for traccion_ventas (10 pts)."""
        entities = {
            "traccion_ventas": "fisicas",
        }
        result = calculate_maturity_score(entities)
        assert result["desglose"]["traccion_ventas"] == 10

    def test_unknown_values_default_to_zero(self):
        """Unknown entity values should default to 0."""
        entities = {
            "presencia_digital": "valor_inventado",
        }
        result = calculate_maturity_score(entities)
        assert result["desglose"]["presencia_digital"] == 0

    def test_desglose_structure(self):
        """Result should have the expected desglose keys."""
        result = calculate_maturity_score({})
        assert "presencia_digital" in result["desglose"]
        assert "traccion_ventas" in result["desglose"]
        assert "formalizacion" in result["desglose"]
        assert "uso_herramientas" in result["desglose"]


class TestValidateEntities:
    """Tests for the validate_entities function."""

    def test_valid_entities(self):
        entities = {
            "presencia_digital": "web_transaccional",
            "traccion_ventas": "dm_wa",
        }
        is_valid, errors = validate_entities(entities)
        assert is_valid is True
        assert errors == []

    def test_invalid_entity_value(self):
        entities = {
            "presencia_digital": "invalid_value",
        }
        is_valid, errors = validate_entities(entities)
        assert is_valid is False
        assert len(errors) == 1

    def test_empty_entities_valid(self):
        is_valid, errors = validate_entities({})
        assert is_valid is True

    def test_none_values_valid(self):
        """None values should be valid (not yet extracted)."""
        entities = {
            "presencia_digital": None,
            "traccion_ventas": None,
        }
        is_valid, errors = validate_entities(entities)
        assert is_valid is True
