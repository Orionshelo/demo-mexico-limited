"""
Esquema de columnas para la hoja de Google Sheets.
Define las columnas, estatus válidos y helpers de mapeo.
"""

from enum import Enum


# ── Estatus del Lead ──────────────────────────────────────────────

class LeadStatus(str, Enum):
    """Estados del flujo del lead en el sistema."""
    NUEVO = "Nuevo"
    EN_TRIAJE = "En Triaje"
    CALIFICADO = "Calificado"
    DESCARTADO = "Descartado"
    PENDIENTE_PAGO = "Pendiente Pago"
    APROBADO = "Aprobado"
    ONBOARDING_ENVIADO = "Onboarding Enviado"
    HUMAN_HANDOFF = "Human Handoff"


class PaymentStatus(str, Enum):
    """Estados del pago."""
    PENDIENTE = "Pendiente"
    COMPROBANTE_ENVIADO = "Comprobante Enviado"
    APROBADO = "Aprobado"
    RECHAZADO = "Rechazado"


class DiscardReason(str, Enum):
    """Razones de descarte automático."""
    NO_MEXICANO = "Producto no es 100% mexicano"
    MULTINIVEL = "Negocio multinivel"
    PERECEDERO = "Producto perecedero"
    MANUAL = "Descartado manualmente"


# ── Definición de Columnas ────────────────────────────────────────

# Orden de columnas en la pestaña Nuevos_Leads
LEAD_COLUMNS: list[str] = [
    "Fecha_Registro",       # A - Timestamp ISO 8601
    "Nombre",               # B - Nombre completo
    "Correo",               # C - Email
    "Telefono",             # D - Teléfono con código de país (+52...)
    "Empresa",              # E - Nombre de la empresa/marca
    "URL",                  # F - URL del sitio/redes
    "Descripcion_Producto", # G - Descripción libre del producto
    "Es_Mexicano",          # H - Sí/No
    "Estatus",              # I - LeadStatus
    "Score_Madurez",        # J - 0-100
    "Nivel_Madurez",        # K - Inicial/Intermedio/Avanzado
    "Presencia_Digital",    # L - Desglose scoring
    "Traccion_Ventas",      # M - Desglose scoring
    "Formalizacion",        # N - Desglose scoring
    "Uso_Herramientas",     # O - Desglose scoring
    "Estatus_Pago",         # P - PaymentStatus
    "Onboarding_Enviado",   # Q - TRUE/FALSE
    "Razon_Descarte",       # R - DiscardReason o vacío
    "Notas_Agente",         # S - Notas del agente/resumen
    "Historial_Conversacion", # T - JSON serializado de mensajes
]

# Mapeo de nombre de columna → letra de columna (1-indexed)
COLUMN_LETTERS: dict[str, str] = {}
for i, col_name in enumerate(LEAD_COLUMNS):
    COLUMN_LETTERS[col_name] = chr(ord("A") + i)


def get_column_letter(column_name: str) -> str:
    """Retorna la letra de columna para un nombre dado."""
    letter = COLUMN_LETTERS.get(column_name)
    if letter is None:
        raise ValueError(f"Columna '{column_name}' no encontrada en el esquema.")
    return letter


def get_column_index(column_name: str) -> int:
    """Retorna el índice 1-based de la columna."""
    try:
        return LEAD_COLUMNS.index(column_name) + 1
    except ValueError:
        raise ValueError(f"Columna '{column_name}' no encontrada en el esquema.")


def build_header_row() -> list[str]:
    """Retorna la fila de encabezados para inicializar la hoja."""
    return LEAD_COLUMNS.copy()
