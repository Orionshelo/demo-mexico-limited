"""
Servicio de notificaciones por email para Mexico Limited.

Envía notificaciones al ejecutivo de validación:
- Comprobantes de pago recibidos por WhatsApp.
- Alertas de Human Handoff.
"""

import base64
import logging
from typing import Optional

from config import (
    SENDGRID_API_KEY,
    NOTIFICATION_FROM_EMAIL,
    EXECUTIVE_EMAIL,
)

logger = logging.getLogger(__name__)

# Try to import sendgrid, fall back to logging if not available
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import (
        Mail,
        Attachment,
        FileContent,
        FileName,
        FileType,
        Disposition,
    )

    HAS_SENDGRID = True
except ImportError:
    HAS_SENDGRID = False
    logger.warning(
        "sendgrid package not installed. Email notifications will be logged only."
    )


class EmailService:
    """
    Servicio de envío de emails para notificaciones internas.
    Usa SendGrid cuando está disponible, sino solo logea.
    """

    def __init__(self):
        self._client = None
        if HAS_SENDGRID and SENDGRID_API_KEY:
            self._client = SendGridAPIClient(SENDGRID_API_KEY)

    def send_payment_receipt(
        self,
        lead_name: str,
        lead_phone: str,
        lead_email: str,
        lead_company: str,
        image_data: bytes,
        mime_type: str = "image/jpeg",
    ) -> bool:
        """
        Envía el comprobante de pago al ejecutivo para validación.

        Args:
            lead_name: Nombre del emprendedor.
            lead_phone: Teléfono del emprendedor.
            lead_email: Email del emprendedor.
            lead_company: Nombre de la empresa.
            image_data: Bytes de la imagen del comprobante.
            mime_type: MIME type de la imagen.

        Returns:
            True si se envió exitosamente.
        """
        subject = f"🏦 Comprobante de Pago — {lead_name} ({lead_company})"

        body_html = f"""
        <h2>Nuevo Comprobante de Pago Recibido</h2>
        <table style="border-collapse: collapse; width: 100%; max-width: 600px;">
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Nombre</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{lead_name}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Empresa</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{lead_company}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Teléfono</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{lead_phone}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Correo</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{lead_email}</td>
            </tr>
        </table>

        <p style="margin-top: 20px;">
            <strong>Acción requerida:</strong> Validar el comprobante adjunto y actualizar
            la celda <code>Estatus_Pago</code> a "Aprobado" en Google Sheets.
        </p>

        <p>El comprobante se adjunta a este correo.</p>
        """

        # Determine file extension
        ext_map = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
            "application/pdf": "pdf",
        }
        extension = ext_map.get(mime_type, "jpg")
        filename = f"comprobante_{lead_name.replace(' ', '_')}.{extension}"

        return self._send_email(
            subject=subject,
            body_html=body_html,
            attachment_data=image_data,
            attachment_filename=filename,
            attachment_mime=mime_type,
        )

    def send_handoff_alert(
        self,
        lead_name: str,
        lead_phone: str,
        lead_company: str,
        conversation_summary: str,
    ) -> bool:
        """
        Envía una alerta al ejecutivo cuando se activa un Human Handoff.

        Args:
            lead_name: Nombre del emprendedor.
            lead_phone: Teléfono del emprendedor.
            lead_company: Nombre de la empresa.
            conversation_summary: Último mensaje o resumen de la conversación.

        Returns:
            True si se envió exitosamente.
        """
        subject = f"🚨 Human Handoff — {lead_name} ({lead_company})"

        body_html = f"""
        <h2>⚠️ Atención: Solicitud de Atención Humana</h2>
        <p>Un emprendedor ha solicitado hablar con un ejecutivo o el agente
        detectó señales de frustración.</p>

        <table style="border-collapse: collapse; width: 100%; max-width: 600px;">
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Nombre</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{lead_name}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Empresa</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{lead_company}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Teléfono</td>
                <td style="padding: 8px; border: 1px solid #ddd;">
                    <a href="https://wa.me/{lead_phone.lstrip('+')}">{lead_phone}</a>
                </td>
            </tr>
        </table>

        <h3>Contexto / Último mensaje:</h3>
        <blockquote style="background: #f9f9f9; border-left: 4px solid #e71873;
                    padding: 12px; margin: 16px 0;">
            {conversation_summary}
        </blockquote>

        <p><strong>Por favor, contacta al emprendedor lo antes posible.</strong></p>
        """

        return self._send_email(subject=subject, body_html=body_html)

    def _send_email(
        self,
        subject: str,
        body_html: str,
        attachment_data: Optional[bytes] = None,
        attachment_filename: Optional[str] = None,
        attachment_mime: Optional[str] = None,
    ) -> bool:
        """Internal method to send an email via SendGrid or log it."""
        if not EXECUTIVE_EMAIL:
            logger.warning("EXECUTIVE_EMAIL not configured, skipping email.")
            return False

        if not self._client:
            logger.info(
                f"[EMAIL LOG] To: {EXECUTIVE_EMAIL} | Subject: {subject}\n"
                f"Body: {body_html[:200]}..."
            )
            return True

        try:
            message = Mail(
                from_email=NOTIFICATION_FROM_EMAIL,
                to_emails=EXECUTIVE_EMAIL,
                subject=subject,
                html_content=body_html,
            )

            if attachment_data and attachment_filename:
                encoded = base64.b64encode(attachment_data).decode("utf-8")
                attachment = Attachment()
                attachment.file_content = FileContent(encoded)
                attachment.file_name = FileName(attachment_filename)
                attachment.file_type = FileType(attachment_mime or "image/jpeg")
                attachment.disposition = Disposition("attachment")
                message.attachment = attachment

            response = self._client.send(message)
            logger.info(
                f"Email sent: {subject} | Status: {response.status_code}"
            )
            return response.status_code in (200, 201, 202)

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
