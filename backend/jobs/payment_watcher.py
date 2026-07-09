"""
Payment Watcher — Cron Job para detectar pagos aprobados.

Periódicamente consulta Google Sheets buscando leads cuyo
Estatus_Pago cambió a "Aprobado" y que aún no han recibido
el onboarding. Envía la Template 3 (Onboarding) por WhatsApp.
"""

import logging

from config import (
    CALENDLY_LINK,
    ONBOARDING_GUIDE_LINK,
)
from services.sheets.sheets_client import SheetsClient
from services.sheets.schema import LeadStatus
from services.whatsapp.whatsapp_client import WhatsAppClient

logger = logging.getLogger(__name__)


def check_approved_payments() -> int:
    """
    Verifica la hoja de Google Sheets buscando pagos aprobados
    pendientes de onboarding y despacha las plantillas correspondientes.

    Returns:
        Número de leads procesados.
    """
    logger.info("Payment watcher: checking for approved payments...")

    sheets = SheetsClient()
    whatsapp = WhatsAppClient()

    try:
        leads = sheets.get_approved_payments_pending_onboarding()
    except Exception as e:
        logger.error(f"Error querying Google Sheets: {e}")
        return 0

    if not leads:
        logger.info("Payment watcher: no pending onboardings found.")
        return 0

    processed = 0

    for lead in leads:
        phone = lead.get("Telefono", "")
        name = lead.get("Nombre", "Emprendedor")
        row = lead.get("_row")

        if not phone or not row:
            continue

        try:
            # Send Onboarding Template (Template 3)
            whatsapp.send_onboarding_template(
                to=phone,
                name=name,
                guide_link=ONBOARDING_GUIDE_LINK or "Próximamente",
                calendly_link=CALENDLY_LINK,
            )

            # Update the sheet
            sheets.update_lead(
                row,
                {
                    "Onboarding_Enviado": "TRUE",
                    "Estatus": LeadStatus.ONBOARDING_ENVIADO.value,
                },
            )

            logger.info(
                f"Onboarding sent to {name} ({phone}) — row {row}"
            )
            processed += 1

        except Exception as e:
            logger.error(
                f"Error sending onboarding to {phone}: {e}",
                exc_info=True,
            )

    logger.info(f"Payment watcher: processed {processed} leads.")
    return processed
