"""
Módulo de Scoring de Madurez Digital para Mexico Limited.

Calcula un puntaje de 0-100 en base a 4 dimensiones extraídas
de la conversación por el LLM:
  - Presencia Digital (0-30 pts)
  - Tracción y Ventas (0-30 pts)
  - Formalización (0-20 pts)
  - Uso de Herramientas (0-20 pts)

Categorización:
  0-30  → Inicial
  31-70 → Intermedio
  71-100 → Avanzado
"""

from typing import TypedDict, Literal, Optional


# ── Type Definitions ──────────────────────────────────────────────

PresenciaDigital = Literal[
    "web_transaccional",
    "redes_sociales",
    "nada"
]

TraccionVentas = Literal[
    "online_recurrente",
    "dm_wa",
    "fisicas",
    "idea"
]

Formalizacion = Literal[
    "formal_rfc",
    "informal"
]

UsoHerramientas = Literal[
    "usa_software",
    "todo_manual"
]


class EntidadesExtraidas(TypedDict, total=False):
    """Entidades que el LLM extrae de la conversación."""
    presencia_digital: Optional[PresenciaDigital]
    traccion_ventas: Optional[TraccionVentas]
    formalizacion: Optional[Formalizacion]
    uso_herramientas: Optional[UsoHerramientas]


class DesgloseScore(TypedDict):
    presencia_digital: int
    traccion_ventas: int
    formalizacion: int
    uso_herramientas: int


class ResultadoScore(TypedDict):
    score: int
    nivel: str
    desglose: DesgloseScore


# ── Score Mappings ────────────────────────────────────────────────

PRESENCIA_DIGITAL_SCORES: dict[str, int] = {
    "web_transaccional": 30,
    "redes_sociales": 15,
    "nada": 0,
}

TRACCION_VENTAS_SCORES: dict[str, int] = {
    "online_recurrente": 30,
    "dm_wa": 15,
    "fisicas": 10,
    "idea": 0,
}

FORMALIZACION_SCORES: dict[str, int] = {
    "formal_rfc": 20,
    "informal": 0,
}

USO_HERRAMIENTAS_SCORES: dict[str, int] = {
    "usa_software": 20,
    "todo_manual": 0,
}


# ── Main Scoring Function ────────────────────────────────────────

def calculate_maturity_score(entities: EntidadesExtraidas) -> ResultadoScore:
    """
    Calcula el Score de Madurez Digital (0-100) basado en las entidades
    extraídas por el LLM de la conversación con el emprendedor.

    Args:
        entities: Diccionario con las 4 dimensiones extraídas.
                  Claves faltantes se tratan como el valor mínimo.

    Returns:
        Diccionario con score total (0-100), nivel ("Inicial"|"Intermedio"|"Avanzado"),
        y desglose por dimensión.

    Example:
        >>> result = calculate_maturity_score({
        ...     "presencia_digital": "redes_sociales",
        ...     "traccion_ventas": "dm_wa",
        ...     "formalizacion": "formal_rfc",
        ...     "uso_herramientas": "todo_manual"
        ... })
        >>> result["score"]
        50
        >>> result["nivel"]
        'Intermedio'
    """
    presencia = PRESENCIA_DIGITAL_SCORES.get(
        entities.get("presencia_digital", "nada"), 0
    )
    traccion = TRACCION_VENTAS_SCORES.get(
        entities.get("traccion_ventas", "idea"), 0
    )
    formalizacion = FORMALIZACION_SCORES.get(
        entities.get("formalizacion", "informal"), 0
    )
    herramientas = USO_HERRAMIENTAS_SCORES.get(
        entities.get("uso_herramientas", "todo_manual"), 0
    )

    total = presencia + traccion + formalizacion + herramientas
    nivel = _categorize(total)

    return {
        "score": total,
        "nivel": nivel,
        "desglose": {
            "presencia_digital": presencia,
            "traccion_ventas": traccion,
            "formalizacion": formalizacion,
            "uso_herramientas": herramientas,
        },
    }


def _categorize(score: int) -> str:
    """Categoriza el score en nivel de madurez."""
    if score <= 30:
        return "Inicial"
    elif score <= 70:
        return "Intermedio"
    else:
        return "Avanzado"


# ── Validation Helper ─────────────────────────────────────────────

VALID_VALUES = {
    "presencia_digital": set(PRESENCIA_DIGITAL_SCORES.keys()),
    "traccion_ventas": set(TRACCION_VENTAS_SCORES.keys()),
    "formalizacion": set(FORMALIZACION_SCORES.keys()),
    "uso_herramientas": set(USO_HERRAMIENTAS_SCORES.keys()),
}


def validate_entities(entities: dict) -> tuple[bool, list[str]]:
    """
    Valida que las entidades extraídas tengan valores reconocidos.

    Returns:
        Tuple de (is_valid, lista de errores).
    """
    errors: list[str] = []

    for key, valid_set in VALID_VALUES.items():
        value = entities.get(key)
        if value is not None and value not in valid_set:
            errors.append(
                f"'{key}' tiene valor '{value}', esperado uno de: {valid_set}"
            )

    return (len(errors) == 0, errors)
