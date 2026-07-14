"""
Nurture Watcher — Cron Job de seguimiento (nurturing) de leads.

Periódicamente revisa los leads que se enfriaron y les envía mensajes
de re-enganche por WhatsApp y/o email, según la secuencia definida en
`utils/nurture.py`:

  - "sin_respuesta":  leads que se registraron, recibieron la bienvenida
                      y nunca contestaron (Estatus = "Nuevo").
  - "pago_pendiente": leads calificados con datos de pago enviados que
                      aún no pagan (Estatus = "Pendiente Pago").

Tras cada envío, avanza `Nurture_Etapa` y sella `Ultimo_Nurture` para
respetar la cadencia y el tope de etapas.

NOTA (producción): los mensajes de WhatsApp fuera de la ventana de 24h
requieren plantillas pre-aprobadas por Meta. Para producción, registra
estas secuencias como plantillas y despáchalas con `send_template`.
Aquí se envían como texto libre para simplicidad de la demo.
"""

import logging
from datetime import datetime, timezone

from services.sheets.sheets_client import SheetsClient
from services.sheets.schema import LeadStatus
from services.whatsapp.whatsapp_client import WhatsAppClient
from services.notifications.email_service import EmailService
from utils.nurture import decide_nurture_action

logger = logging.getLogger(__name__)


def run_nurture_cycle() -> int:
    """
    Ejecuta un ciclo de nurturing sobre todos los leads elegibles.

    Returns:
        Número de leads a los que se les envió un seguimiento.
    """
    logger.info("Nurture watcher: checking for leads to follow up...")

    sheets = SheetsClient()
    whatsapp = WhatsAppClient()
    email_service = EmailService()

    try:
        candidates = _get_candidates(sheets)
    except Exception as e:
        logger.error(f"Nurture watcher: error querying Google Sheets: {e}")
        return 0

    if not candidates:
        logger.info("Nurture watcher: no leads to follow up.")
        return 0

    now = datetime.now(timezone.utc)
    processed = 0

    for lead in candidates:
        action = decide_nurture_action(lead, now)
        if action is None:
            continue

        phone = lead.get("Telefono", "")
        row = lead.get("_row")
        name = lead.get("Nombre", "emprendedor")

        if not phone or not row:
            continue

        try:
            if "whatsapp" in action.channels:
                whatsapp.send_text_message(phone, action.whatsapp_text)

            if "email" in action.channels:
                email_service.send_lead_nurture(
                    to_email=lead.get("Correo", ""),
                    subject=action.email_subject,
                    body_html=action.email_html,
                )

            sheets.update_lead(
                row,
                {
                    "Nurture_Etapa": str(action.stage),
                    "Ultimo_Nurture": now.isoformat(),
                },
            )

            logger.info(
                f"Nurture sent to {name} ({phone}) — "
                f"track={action.track} stage={action.stage} "
                f"channels={action.channels}"
            )
            processed += 1

        except Exception as e:
            logger.error(
                f"Nurture watcher: error following up {phone}: {e}",
                exc_info=True,
            )

    logger.info(f"Nurture watcher: processed {processed} leads.")
    return processed


def _get_candidates(sheets: SheetsClient) -> list[dict]:
    """Reúne los leads en estatus elegibles para nurturing."""
    candidates: list[dict] = []
    for status in (LeadStatus.NUEVO.value, LeadStatus.PENDIENTE_PAGO.value):
        candidates.extend(sheets.get_leads_by_status(status))
    return candidates
