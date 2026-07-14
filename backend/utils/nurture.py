"""
Lógica de Nurturing (seguimiento) de leads para Mexico Limited.

Este módulo es PURO (sin I/O): dada la fila de un lead y la hora actual,
decide si toca enviar un mensaje de seguimiento, en qué etapa de la
secuencia, por qué canal (WhatsApp / email) y con qué contenido.

El cron `jobs/nurture_watcher.py` es quien consulta Google Sheets,
ejecuta el envío y persiste el avance de etapa.

Tracks (secuencias) soportados:
  - "sin_respuesta":  lead que llenó el formulario, recibió la bienvenida
                      y nunca respondió (Estatus = "Nuevo").
  - "pago_pendiente": lead calificado al que se le enviaron los datos de
                      pago y aún no paga (Estatus = "Pendiente Pago").

La cadencia de cada etapa se mide en horas desde el último contacto
(`Ultimo_Nurture`) o, si aún no hay nurturing, desde `Fecha_Registro`.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ── Estatus que disparan nurturing ────────────────────────────────
# Deben coincidir con services.sheets.schema.LeadStatus. Se replican como
# literales para mantener este módulo libre de dependencias de I/O.
STATUS_SIN_RESPUESTA = "Nuevo"
STATUS_PAGO_PENDIENTE = "Pendiente Pago"


# ── Definición de las secuencias ──────────────────────────────────
# cadence_hours[i] = horas que deben transcurrir desde el contacto previo
# antes de disparar la etapa (i+1).
NURTURE_TRACKS: dict[str, dict] = {
    "sin_respuesta": {
        "status": STATUS_SIN_RESPUESTA,
        "max_stages": 3,
        "cadence_hours": [24, 48, 96],
        "channels": {
            1: ["whatsapp"],
            2: ["whatsapp", "email"],
            3: ["whatsapp"],
        },
    },
    "pago_pendiente": {
        "status": STATUS_PAGO_PENDIENTE,
        "max_stages": 3,
        "cadence_hours": [24, 72, 120],
        "channels": {
            1: ["whatsapp"],
            2: ["whatsapp", "email"],
            3: ["whatsapp", "email"],
        },
    },
}

# Estatus → nombre del track
_STATUS_TO_TRACK = {
    cfg["status"]: name for name, cfg in NURTURE_TRACKS.items()
}


# ── Contenido de los mensajes ─────────────────────────────────────

_WHATSAPP_MESSAGES: dict[str, dict[int, str]] = {
    "sin_respuesta": {
        1: (
            "¡Hola {nombre}! 👋 Vimos que iniciaste tu registro en "
            "Mexico Limited pero no hemos podido continuar. ¿Te gustaría "
            "que te contemos cómo ayudamos a los emprendedores a escalar "
            "su negocio? 🇲🇽"
        ),
        2: (
            "Hola {nombre}, seguimos aquí para apoyarte 💪. Con Mexico "
            "Limited puedes tener tu tienda en línea, fotos de producto con "
            "IA y mentoría personalizada. ¿Retomamos tu proceso?"
        ),
        3: (
            "{nombre}, este será nuestro último recordatorio por ahora. "
            "Cuando quieras impulsar tu emprendimiento, escríbenos y con "
            "gusto te acompañamos. ¡Mucho éxito! 🚀"
        ),
    },
    "pago_pendiente": {
        1: (
            "¡Hola {nombre}! Ya casi completas tu inscripción a Mexico "
            "Limited 🎉. ¿Tuviste algún problema con el pago? Con gusto te "
            "ayudo a resolverlo."
        ),
        2: (
            "Hola {nombre}, tu lugar en Mexico Limited sigue apartado. Si "
            "tienes dudas sobre el pago o prefieres otra forma de pagar, "
            "dime y lo resolvemos juntos. 🙌"
        ),
        3: (
            "{nombre}, mantendremos tu cupo un poco más. Cuando estés "
            "list@ para completar tu pago e iniciar tu onboarding, aquí "
            "estamos para ayudarte. 🚀"
        ),
    },
}

_EMAIL_SUBJECTS: dict[str, dict[int, str]] = {
    "sin_respuesta": {
        2: "{nombre}, tu lugar en Mexico Limited te espera 🇲🇽",
    },
    "pago_pendiente": {
        2: "{nombre}, completa tu inscripción a Mexico Limited",
        3: "Últimos días para apartar tu lugar en Mexico Limited",
    },
}


@dataclass
class NurtureAction:
    """Decisión de nurturing para un lead en un momento dado."""

    track: str
    stage: int
    channels: list[str]
    whatsapp_text: str
    email_subject: str = ""
    email_html: str = ""


# ── Función principal de decisión ─────────────────────────────────

def decide_nurture_action(
    lead: dict, now: datetime
) -> Optional[NurtureAction]:
    """
    Decide si un lead debe recibir un mensaje de nurturing ahora.

    Args:
        lead: Fila del lead (dict con claves de LEAD_COLUMNS).
        now: Momento actual (timezone-aware).

    Returns:
        NurtureAction si toca enviar, o None si no aplica.
    """
    track_name = _STATUS_TO_TRACK.get(lead.get("Estatus", ""))
    if track_name is None:
        return None

    track = NURTURE_TRACKS[track_name]

    stage_done = _parse_int(lead.get("Nurture_Etapa"))
    if stage_done >= track["max_stages"]:
        return None

    anchor = _parse_dt(lead.get("Ultimo_Nurture")) or _parse_dt(
        lead.get("Fecha_Registro")
    )
    if anchor is None:
        return None

    elapsed_hours = (now - anchor).total_seconds() / 3600
    required_hours = track["cadence_hours"][stage_done]
    if elapsed_hours < required_hours:
        return None

    next_stage = stage_done + 1
    return _build_action(track_name, next_stage, lead)


# ── Constructores de acción / contenido ───────────────────────────

def _build_action(track_name: str, stage: int, lead: dict) -> NurtureAction:
    nombre = lead.get("Nombre") or "emprendedor"
    channels = list(NURTURE_TRACKS[track_name]["channels"].get(stage, ["whatsapp"]))

    whatsapp_text = _WHATSAPP_MESSAGES[track_name][stage].format(nombre=nombre)

    email_subject = ""
    email_html = ""
    if "email" in channels:
        subject_tpl = _EMAIL_SUBJECTS.get(track_name, {}).get(stage)
        email_subject = (subject_tpl or "Mexico Limited").format(nombre=nombre)
        email_html = _build_email_html(nombre, whatsapp_text)

    return NurtureAction(
        track=track_name,
        stage=stage,
        channels=channels,
        whatsapp_text=whatsapp_text,
        email_subject=email_subject,
        email_html=email_html,
    )


def _build_email_html(nombre: str, message: str) -> str:
    """Envuelve el mensaje de seguimiento en un HTML simple para email."""
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 560px; margin: 0 auto;">
        <h2 style="color: #e71873;">Mexico Limited 🇲🇽</h2>
        <p>Hola {nombre},</p>
        <p>{message}</p>
        <p style="margin-top: 24px;">
            Responde este correo o escríbenos por WhatsApp y con gusto
            continuamos tu proceso.
        </p>
        <p style="color: #888; font-size: 12px; margin-top: 32px;">
            Equipo Mexico Limited — impulsando el talento mexicano.
        </p>
    </div>
    """


# ── Helpers de parsing ────────────────────────────────────────────

def _parse_int(value) -> int:
    try:
        return int(str(value).strip() or "0")
    except (ValueError, TypeError):
        return 0


def _parse_dt(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).strip())
    except (ValueError, TypeError):
        return None
