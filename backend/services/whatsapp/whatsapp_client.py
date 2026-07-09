"""
Cliente de WhatsApp Business API (Meta Cloud API).

Provee funciones para enviar mensajes de texto, plantillas,
y descargar medios (imágenes/documentos) del comprobante de pago.
"""

import logging
from typing import Any, Optional

import requests

from config import (
    META_WHATSAPP_TOKEN,
    META_PHONE_NUMBER_ID,
    META_API_BASE_URL,
)

logger = logging.getLogger(__name__)


class WhatsAppClient:
    """
    Wrapper sobre la API de Meta WhatsApp Cloud.

    Usage:
        client = WhatsAppClient()
        client.send_text_message("+525512345678", "¡Hola!")
        client.send_template("+525512345678", "recepcion_lead", ["Juan"])
    """

    def __init__(
        self,
        token: str = META_WHATSAPP_TOKEN,
        phone_number_id: str = META_PHONE_NUMBER_ID,
        api_base_url: str = META_API_BASE_URL,
    ):
        self._token = token
        self._phone_number_id = phone_number_id
        self._base_url = api_base_url
        self._messages_url = (
            f"{self._base_url}/{self._phone_number_id}/messages"
        )
        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    # ── Text Messages ─────────────────────────────────────────────

    def send_text_message(self, to: str, text: str) -> dict:
        """
        Envía un mensaje de texto libre al usuario.

        Args:
            to: Número de teléfono destino (e.g., "+525512345678").
            text: Texto del mensaje.

        Returns:
            Response JSON de la API de Meta.
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": self._strip_plus(to),
            "type": "text",
            "text": {"body": text},
        }

        return self._send(payload)

    # ── Template Messages ─────────────────────────────────────────

    def send_template(
        self,
        to: str,
        template_name: str,
        parameters: list[str],
        language_code: str = "es_MX",
    ) -> dict:
        """
        Envía una plantilla pre-aprobada de WhatsApp Business.

        Args:
            to: Número de teléfono destino.
            template_name: Nombre de la plantilla registrada en Meta.
            parameters: Lista de parámetros {{1}}, {{2}}, etc.
            language_code: Código de idioma (default: "es_MX").

        Returns:
            Response JSON de la API de Meta.
        """
        components = []
        if parameters:
            body_params = [
                {"type": "text", "text": param} for param in parameters
            ]
            components.append(
                {"type": "body", "parameters": body_params}
            )

        payload = {
            "messaging_product": "whatsapp",
            "to": self._strip_plus(to),
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": components,
            },
        }

        return self._send(payload)

    # ── Convenience Methods for Spec Templates ────────────────────

    def send_welcome_template(self, to: str, name: str) -> dict:
        """
        Template 1: Recepción de Lead.
        "¡Hola {{1}}! Bienvenid@ a Mexico Limited..."
        """
        return self.send_template(
            to=to,
            template_name="recepcion_lead",
            parameters=[name],
        )

    def send_payment_template(
        self, to: str, name: str, payment_info: str
    ) -> dict:
        """
        Template 2: Envío de Datos de Pago.
        "¡Excelente perfil, {{1}}!... {{2}}"
        """
        return self.send_template(
            to=to,
            template_name="envio_datos_pago",
            parameters=[name, payment_info],
        )

    def send_onboarding_template(
        self, to: str, name: str, guide_link: str, calendly_link: str
    ) -> dict:
        """
        Template 3: Onboarding Aprobado.
        "¡Pago confirmado, {{1}}!... {{2}}... {{3}}"
        """
        return self.send_template(
            to=to,
            template_name="onboarding_aprobado",
            parameters=[name, guide_link, calendly_link],
        )

    # ── Media Download ────────────────────────────────────────────

    def download_media(self, media_id: str) -> Optional[bytes]:
        """
        Descarga un archivo multimedia de WhatsApp en dos pasos:
        1. Obtiene la URL del media via API.
        2. Descarga el contenido binario.

        Args:
            media_id: ID del medio proporcionado en el webhook.

        Returns:
            Bytes del archivo, o None si falla.
        """
        try:
            # Step 1: Get media URL
            url = f"{self._base_url}/{media_id}"
            response = requests.get(url, headers=self._headers, timeout=30)
            response.raise_for_status()
            media_url = response.json().get("url")

            if not media_url:
                logger.error(f"No URL found for media_id: {media_id}")
                return None

            # Step 2: Download the actual file
            file_response = requests.get(
                media_url, headers=self._headers, timeout=60
            )
            file_response.raise_for_status()
            return file_response.content

        except requests.RequestException as e:
            logger.error(f"Error downloading media {media_id}: {e}")
            return None

    def get_media_url(self, media_id: str) -> Optional[str]:
        """Obtiene la URL temporal de un medio sin descargarlo."""
        try:
            url = f"{self._base_url}/{media_id}"
            response = requests.get(url, headers=self._headers, timeout=30)
            response.raise_for_status()
            return response.json().get("url")
        except requests.RequestException as e:
            logger.error(f"Error getting media URL for {media_id}: {e}")
            return None

    # ── Mark as Read ──────────────────────────────────────────────

    def mark_as_read(self, message_id: str) -> dict:
        """Marca un mensaje como leído (blue ticks)."""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        return self._send(payload)

    # ── Internal Helpers ──────────────────────────────────────────

    def _send(self, payload: dict) -> dict:
        """Sends a request to the WhatsApp API."""
        try:
            response = requests.post(
                self._messages_url,
                headers=self._headers,
                json=payload,
                timeout=30,
            )

            if response.status_code not in (200, 201):
                logger.error(
                    f"WhatsApp API error {response.status_code}: {response.text}"
                )

            response.raise_for_status()
            result = response.json()
            logger.info(f"Message sent successfully: {result}")
            return result

        except requests.RequestException as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            return {"error": str(e)}

    @staticmethod
    def _strip_plus(phone: str) -> str:
        """Meta API requires phone without + prefix."""
        return phone.lstrip("+")
