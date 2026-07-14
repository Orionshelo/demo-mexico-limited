"""
Cliente de Google Sheets para operaciones CRUD sobre leads.

Usa gspread con autenticación Service Account para leer/escribir
en la hoja de cálculo que actúa como base de datos del sistema.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import gspread
from google.oauth2.service_account import Credentials

from config import (
    GOOGLE_SHEETS_CREDENTIALS_FILE,
    GOOGLE_SHEETS_CREDENTIALS_JSON,
    GOOGLE_SHEETS_SPREADSHEET_ID,
    GOOGLE_SHEETS_WORKSHEET_NAME,
)
from .schema import (
    LEAD_COLUMNS,
    LeadStatus,
    PaymentStatus,
    get_column_index,
    build_header_row,
)

logger = logging.getLogger(__name__)

# Scopes requeridos para Google Sheets API
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class SheetsClient:
    """
    Wrapper sobre gspread para operaciones con leads en Google Sheets.

    Supports two auth modes:
    1. JSON env var (GOOGLE_SHEETS_CREDENTIALS_JSON) — for Render/Cloud
    2. Credentials file (credentials.json) — for local development

    Usage:
        client = SheetsClient()
        client.insert_lead({
            "Nombre": "Juan Pérez",
            "Correo": "juan@example.com",
            "Telefono": "+525512345678",
            "Empresa": "Artesanías MX",
        })
    """

    def __init__(
        self,
        credentials_file: str = GOOGLE_SHEETS_CREDENTIALS_FILE,
        spreadsheet_id: str = GOOGLE_SHEETS_SPREADSHEET_ID,
        worksheet_name: str = GOOGLE_SHEETS_WORKSHEET_NAME,
    ):
        self._credentials_file = credentials_file
        self._spreadsheet_id = spreadsheet_id
        self._worksheet_name = worksheet_name
        self._client: Optional[gspread.Client] = None
        self._worksheet: Optional[gspread.Worksheet] = None

    def _get_worksheet(self) -> gspread.Worksheet:
        """Lazy-initializes and returns the worksheet."""
        if self._worksheet is not None:
            return self._worksheet

        try:
            # Try JSON env var first (Render/Cloud), then file (local dev)
            if GOOGLE_SHEETS_CREDENTIALS_JSON:
                creds_info = json.loads(GOOGLE_SHEETS_CREDENTIALS_JSON)
                creds = Credentials.from_service_account_info(
                    creds_info, scopes=SCOPES
                )
                logger.info("Authenticated with Google via env var (CREDENTIALS_JSON).")
            else:
                creds = Credentials.from_service_account_file(
                    self._credentials_file, scopes=SCOPES
                )
                logger.info("Authenticated with Google via credentials file.")

            self._client = gspread.authorize(creds)
            spreadsheet = self._client.open_by_key(self._spreadsheet_id)

            # Try to open the worksheet, create it if it doesn't exist
            try:
                self._worksheet = spreadsheet.worksheet(self._worksheet_name)
            except gspread.exceptions.WorksheetNotFound:
                logger.info(
                    f"Worksheet '{self._worksheet_name}' not found, creating it."
                )
                self._worksheet = spreadsheet.add_worksheet(
                    title=self._worksheet_name, rows=1000, cols=len(LEAD_COLUMNS)
                )
                # Write header row
                self._worksheet.update(
                    range_name="A1",
                    values=[build_header_row()],
                )

            return self._worksheet

        except Exception as e:
            logger.error(f"Error connecting to Google Sheets: {e}")
            raise

    # ── CRUD Operations ───────────────────────────────────────────

    def insert_lead(self, data: dict[str, Any]) -> int:
        """
        Inserta un nuevo lead en la siguiente fila disponible.

        Args:
            data: Diccionario con campos del lead (las claves deben coincidir
                  con los nombres en LEAD_COLUMNS).

        Returns:
            Número de fila donde se insertó el lead.
        """
        ws = self._get_worksheet()

        # Build row respecting column order
        row: list[str] = []
        for col_name in LEAD_COLUMNS:
            if col_name == "Fecha_Registro":
                row.append(
                    data.get(
                        col_name,
                        datetime.now(timezone.utc).isoformat(),
                    )
                )
            elif col_name == "Estatus":
                row.append(data.get(col_name, LeadStatus.NUEVO.value))
            elif col_name == "Estatus_Pago":
                row.append(data.get(col_name, PaymentStatus.PENDIENTE.value))
            elif col_name == "Onboarding_Enviado":
                row.append(data.get(col_name, "FALSE"))
            elif col_name == "Historial_Conversacion":
                # Serialize conversation history as JSON
                hist = data.get(col_name, [])
                row.append(json.dumps(hist, ensure_ascii=False) if hist else "[]")
            else:
                row.append(str(data.get(col_name, "")))

        ws.append_row(row, value_input_option="USER_ENTERED")
        row_number = len(ws.get_all_values())
        logger.info(f"Lead inserted at row {row_number}: {data.get('Telefono', 'N/A')}")
        return row_number

    def find_lead_by_phone(self, phone: str) -> Optional[dict[str, Any]]:
        """
        Busca un lead por número de teléfono.

        Args:
            phone: Número de teléfono (e.g., "+525512345678").

        Returns:
            Diccionario con los datos del lead y su número de fila (_row),
            o None si no se encuentra.
        """
        ws = self._get_worksheet()
        phone_col_index = get_column_index("Telefono")

        try:
            cell = ws.find(phone, in_column=phone_col_index)
            if cell is None:
                return None

            row_values = ws.row_values(cell.row)
            lead = {"_row": cell.row}
            for i, col_name in enumerate(LEAD_COLUMNS):
                if i < len(row_values):
                    lead[col_name] = row_values[i]
                else:
                    lead[col_name] = ""

            # Deserialize conversation history
            if lead.get("Historial_Conversacion"):
                try:
                    lead["Historial_Conversacion"] = json.loads(
                        lead["Historial_Conversacion"]
                    )
                except json.JSONDecodeError:
                    lead["Historial_Conversacion"] = []

            return lead

        except gspread.exceptions.CellNotFound:
            return None

    def update_lead(self, row: int, fields: dict[str, Any]) -> None:
        """
        Actualiza campos específicos de un lead dado su número de fila.

        Args:
            row: Número de fila en la hoja (1-indexed, sin contar header).
            fields: Diccionario de {nombre_columna: valor}.
        """
        ws = self._get_worksheet()

        for col_name, value in fields.items():
            col_index = get_column_index(col_name)

            # Serialize complex types
            if isinstance(value, (list, dict)):
                value = json.dumps(value, ensure_ascii=False)

            ws.update_cell(row, col_index, str(value))

        logger.info(f"Lead at row {row} updated: {list(fields.keys())}")

    def get_all_leads(self) -> list[dict[str, Any]]:
        """
        Retorna todos los leads registrados en la hoja.

        Returns:
            Lista de diccionarios con datos del lead y _row.
        """
        ws = self._get_worksheet()
        all_values = ws.get_all_values()

        if len(all_values) <= 1:
            return []

        leads = []
        for row_num, row_values in enumerate(all_values[1:], start=2):
            lead = {"_row": row_num}
            for i, col_name in enumerate(LEAD_COLUMNS):
                if i < len(row_values):
                    lead[col_name] = row_values[i]
                else:
                    lead[col_name] = ""
            leads.append(lead)

        return leads

    def get_leads_by_status(
        self, status: str, additional_filter: Optional[dict[str, str]] = None
    ) -> list[dict[str, Any]]:
        """
        Retorna todos los leads con un estatus específico.

        Args:
            status: Valor del estatus a filtrar (e.g., "Aprobado").
            additional_filter: Filtros adicionales opcionales {columna: valor}.

        Returns:
            Lista de diccionarios con datos del lead y _row.
        """
        ws = self._get_worksheet()
        all_values = ws.get_all_values()

        if len(all_values) <= 1:
            return []

        # header = all_values[0]
        leads = []
        status_col_idx = get_column_index("Estatus") - 1  # 0-indexed

        for row_num, row_values in enumerate(all_values[1:], start=2):
            if len(row_values) <= status_col_idx:
                continue

            if row_values[status_col_idx] != status:
                continue

            # Apply additional filters
            if additional_filter:
                skip = False
                for col_name, expected_value in additional_filter.items():
                    col_idx = get_column_index(col_name) - 1
                    if col_idx < len(row_values) and row_values[col_idx] != expected_value:
                        skip = True
                        break
                if skip:
                    continue

            lead = {"_row": row_num}
            for i, col_name in enumerate(LEAD_COLUMNS):
                if i < len(row_values):
                    lead[col_name] = row_values[i]
                else:
                    lead[col_name] = ""

            leads.append(lead)

        return leads

    def get_approved_payments_pending_onboarding(self) -> list[dict[str, Any]]:
        """
        Retorna leads cuyo pago fue aprobado pero no se ha enviado onboarding.
        Usado por el cron job de payment_watcher.
        """
        ws = self._get_worksheet()
        all_values = ws.get_all_values()

        if len(all_values) <= 1:
            return []

        payment_col_idx = get_column_index("Estatus_Pago") - 1
        onboarding_col_idx = get_column_index("Onboarding_Enviado") - 1

        leads = []
        for row_num, row_values in enumerate(all_values[1:], start=2):
            if len(row_values) <= max(payment_col_idx, onboarding_col_idx):
                continue

            is_approved = row_values[payment_col_idx] == PaymentStatus.APROBADO.value
            not_onboarded = row_values[onboarding_col_idx] in ("FALSE", "", "false")

            if is_approved and not_onboarded:
                lead = {"_row": row_num}
                for i, col_name in enumerate(LEAD_COLUMNS):
                    if i < len(row_values):
                        lead[col_name] = row_values[i]
                    else:
                        lead[col_name] = ""
                leads.append(lead)

        return leads

    def append_to_conversation(self, row: int, role: str, message: str) -> None:
        """
        Agrega un mensaje al historial de conversación del lead.

        Args:
            row: Número de fila del lead.
            role: "user" o "assistant".
            message: Texto del mensaje.
        """
        ws = self._get_worksheet()
        hist_col_idx = get_column_index("Historial_Conversacion")

        current_value = ws.cell(row, hist_col_idx).value
        try:
            history = json.loads(current_value) if current_value else []
        except json.JSONDecodeError:
            history = []

        history.append(
            {
                "role": role,
                "content": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        ws.update_cell(
            row, hist_col_idx, json.dumps(history, ensure_ascii=False)
        )

    def ensure_headers_exist(self) -> None:
        """Verifica que la primera fila tenga los headers correctos."""
        ws = self._get_worksheet()
        first_row = ws.row_values(1)

        if first_row != LEAD_COLUMNS:
            logger.info("Headers missing or incorrect, writing them.")
            ws.update(
                range_name="A1",
                values=[build_header_row()],
            )
