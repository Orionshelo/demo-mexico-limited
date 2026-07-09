"""
Tests para el parser de payloads de WhatsApp.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.whatsapp.payload_parser import parse_webhook_payload, WhatsAppMessage


class TestParseWebhookPayload:
    """Tests for parse_webhook_payload function."""

    def test_text_message(self):
        """Parse a standard text message."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "contacts": [{
                            "wa_id": "5215512345678",
                            "profile": {"name": "Juan Pérez"}
                        }],
                        "messages": [{
                            "from": "5215512345678",
                            "id": "wamid.abc123",
                            "timestamp": "1719000000",
                            "type": "text",
                            "text": {"body": "Hola, quiero información"}
                        }]
                    }
                }]
            }]
        }

        messages = parse_webhook_payload(payload)
        assert len(messages) == 1

        msg = messages[0]
        assert msg.phone == "+5215512345678"
        assert msg.display_name == "Juan Pérez"
        assert msg.message_type == "text"
        assert msg.text == "Hola, quiero información"
        assert msg.message_id == "wamid.abc123"

    def test_image_message(self):
        """Parse an image message (payment receipt)."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "contacts": [{"wa_id": "5215512345678", "profile": {"name": "Ana"}}],
                        "messages": [{
                            "from": "5215512345678",
                            "id": "wamid.img456",
                            "timestamp": "1719000001",
                            "type": "image",
                            "image": {
                                "id": "media_id_123",
                                "mime_type": "image/jpeg",
                                "caption": "Mi comprobante de pago"
                            }
                        }]
                    }
                }]
            }]
        }

        messages = parse_webhook_payload(payload)
        assert len(messages) == 1

        msg = messages[0]
        assert msg.message_type == "image"
        assert msg.media_id == "media_id_123"
        assert msg.media_mime_type == "image/jpeg"
        assert msg.text == "Mi comprobante de pago"

    def test_button_reply_message(self):
        """Parse a button reply from a template."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "contacts": [{"wa_id": "5215512345678", "profile": {"name": "Carlos"}}],
                        "messages": [{
                            "from": "5215512345678",
                            "id": "wamid.btn789",
                            "timestamp": "1719000002",
                            "type": "button",
                            "button": {
                                "text": "Sí, es mexicano",
                                "payload": "btn_mexican_yes"
                            }
                        }]
                    }
                }]
            }]
        }

        messages = parse_webhook_payload(payload)
        assert len(messages) == 1

        msg = messages[0]
        assert msg.message_type == "button_reply"
        assert msg.text == "Sí, es mexicano"
        assert msg.button_payload == "btn_mexican_yes"

    def test_no_messages_in_payload(self):
        """Status updates (delivered, read) don't have messages."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "statuses": [{
                            "id": "wamid.abc",
                            "status": "delivered"
                        }]
                    }
                }]
            }]
        }

        messages = parse_webhook_payload(payload)
        assert len(messages) == 0

    def test_empty_payload(self):
        """Empty payload should return empty list."""
        messages = parse_webhook_payload({})
        assert len(messages) == 0

    def test_multiple_messages(self):
        """Payload with multiple messages."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "contacts": [{"wa_id": "5215512345678", "profile": {"name": "Test"}}],
                        "messages": [
                            {
                                "from": "5215512345678",
                                "id": "wamid.1",
                                "timestamp": "1719000000",
                                "type": "text",
                                "text": {"body": "Mensaje 1"}
                            },
                            {
                                "from": "5215512345678",
                                "id": "wamid.2",
                                "timestamp": "1719000001",
                                "type": "text",
                                "text": {"body": "Mensaje 2"}
                            }
                        ]
                    }
                }]
            }]
        }

        messages = parse_webhook_payload(payload)
        assert len(messages) == 2
        assert messages[0].text == "Mensaje 1"
        assert messages[1].text == "Mensaje 2"

    def test_reaction_message_ignored(self):
        """Reaction messages should be filtered out."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "contacts": [{"wa_id": "5215512345678", "profile": {"name": "Test"}}],
                        "messages": [{
                            "from": "5215512345678",
                            "id": "wamid.react",
                            "timestamp": "1719000000",
                            "type": "reaction",
                            "reaction": {"emoji": "👍"}
                        }]
                    }
                }]
            }]
        }

        messages = parse_webhook_payload(payload)
        assert len(messages) == 0

    def test_phone_normalization(self):
        """Phone numbers should be normalized with + prefix."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "contacts": [{"wa_id": "5215512345678", "profile": {"name": "Test"}}],
                        "messages": [{
                            "from": "5215512345678",
                            "id": "wamid.phone",
                            "timestamp": "1719000000",
                            "type": "text",
                            "text": {"body": "Test"}
                        }]
                    }
                }]
            }]
        }

        messages = parse_webhook_payload(payload)
        assert messages[0].phone.startswith("+")

    def test_interactive_button_reply(self):
        """Parse an interactive button reply."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "contacts": [{"wa_id": "5215512345678", "profile": {"name": "Test"}}],
                        "messages": [{
                            "from": "5215512345678",
                            "id": "wamid.interactive",
                            "timestamp": "1719000000",
                            "type": "interactive",
                            "interactive": {
                                "type": "button_reply",
                                "button_reply": {
                                    "id": "btn_yes",
                                    "title": "Sí"
                                }
                            }
                        }]
                    }
                }]
            }]
        }

        messages = parse_webhook_payload(payload)
        assert len(messages) == 1
        assert messages[0].message_type == "interactive"
        assert messages[0].text == "Sí"
        assert messages[0].button_payload == "btn_yes"

    def test_document_message(self):
        """Parse a document message."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "contacts": [{"wa_id": "5215512345678", "profile": {"name": "Test"}}],
                        "messages": [{
                            "from": "5215512345678",
                            "id": "wamid.doc",
                            "timestamp": "1719000000",
                            "type": "document",
                            "document": {
                                "id": "doc_media_123",
                                "mime_type": "application/pdf",
                                "caption": "Factura"
                            }
                        }]
                    }
                }]
            }]
        }

        messages = parse_webhook_payload(payload)
        assert len(messages) == 1
        assert messages[0].message_type == "document"
        assert messages[0].media_id == "doc_media_123"
        assert messages[0].media_mime_type == "application/pdf"
