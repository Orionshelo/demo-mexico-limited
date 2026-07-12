# Simulación del Sistema de Pagos — Panel de Aprobación

**Fecha:** 2026-07-12
**Estado:** Aprobado — listo para plan de implementación

## Contexto y Problema

En producción, el método de cobro es **transferencia bancaria + comprobante validado por un humano**:

1. El lead califica → estado `PENDIENTE_PAGO`; el agente envía datos bancarios (BBVA / CLABE) por WhatsApp.
2. El lead transfiere y manda una **foto del comprobante** → el orchestrator marca `Estatus_Pago = Comprobante Enviado` y envía email al ejecutivo.
3. **[Hueco manual]** Un ejecutivo revisa el comprobante y pone `Estatus_Pago = Aprobado` a mano en Google Sheets.
4. El cron `payment_watcher` detecta el "Aprobado" y dispara el onboarding automático (Template 3 de WhatsApp).

El paso 3 es 100% manual. No existe una API de pago que confirme la transferencia; depende de una persona. Para una **demo**, ese hueco rompe el flujo automático de punta a punta: no hay quién apruebe el pago en vivo.

## Objetivo

Sustituir la validación humana del comprobante por un **panel de administración con un botón "Aprobar pago"**, para que el presentador dispare la aprobación en vivo y el flujo llegue solo hasta el onboarding.

**Premisa clave:** el panel NO mockea los demás servicios. Google Sheets, WhatsApp, OpenAI y SendGrid seguirán usando sus APIs reales una vez configuradas. El panel solo reemplaza al humano que aprueba, que es el único eslabón sin API.

## Decisiones de Diseño (confirmadas)

| Decisión | Elección |
|----------|----------|
| Método de pago real (producción) | Transferencia + comprobante validado por humano (se mantiene) |
| Disparo de aprobación en la demo | Botón en panel de administración |
| Ubicación del panel | Página HTML autocontenida servida por Flask (backend) |
| Alcance | Lista de pendientes + Aprobar + Rechazar |
| Momento del onboarding | Al instante tras aprobar (no espera el cron de 5 min) |
| Autenticación | Ninguna (panel abierto, máxima simplicidad para la demo) |

## Arquitectura

Un **Blueprint nuevo de Flask** en `backend/api/admin/admin_panel.py` con estas rutas:

| Ruta | Método | Responsabilidad |
|------|--------|-----------------|
| `/admin` | GET | Sirve una página HTML autocontenida (sin build ni Next.js): tabla de leads con comprobante pendiente + botones Aprobar/Rechazar. |
| `/admin/api/pending` | GET | Devuelve JSON con los leads en `Estatus_Pago = Comprobante Enviado`. |
| `/admin/api/approve/<row>` | POST | Marca `Estatus_Pago = Aprobado` y dispara el onboarding de ese lead al instante. |
| `/admin/api/reject/<row>` | POST | Marca `Estatus_Pago = Rechazado` y notifica al lead por WhatsApp. |

La página HTML hace `fetch` a sus propios endpoints y se auto-refresca cada ~10 segundos, de modo que cuando el lead envía su comprobante en vivo aparece solo en la tabla.

## Flujo de Datos

```
Lead manda comprobante (WhatsApp)
        │  (orchestrator existente: _handle_payment_receipt)
        ▼
Estatus_Pago = "Comprobante Enviado"  ──►  aparece en /admin (auto-refresh)
        │
   [Presentador hace clic "Aprobar"]
        ▼
POST /admin/api/approve/<row>
        │  set Estatus_Pago = "Aprobado"
        ▼
process_lead_onboarding(lead)   ← lógica reutilizada del payment_watcher
        │  envía Template 3 (Onboarding) + set Onboarding_Enviado=TRUE
        │  + set Estatus = "Onboarding Enviado"
        ▼
   Lead recibe onboarding automático 🎉
```

**Rechazar:** `POST /admin/api/reject/<row>` → set `Estatus_Pago = Rechazado` + mensaje de WhatsApp al lead
("No pudimos validar tu comprobante, ¿podrías reenviarlo por favor?").

## Componentes y Cambios

### 1. `backend/services/sheets/sheets_client.py`
Nuevo método `get_pending_payment_approvals()`: retorna los leads con `Estatus_Pago = Comprobante Enviado`.
Calcado del `get_approved_payments_pending_onboarding()` ya existente (mismo patrón de escaneo por columna).

### 2. `backend/jobs/payment_watcher.py`
Refactor: extraer una función `process_lead_onboarding(lead, sheets, whatsapp) -> bool` que envía el
onboarding de **un solo lead** (Template 3 + actualización de estado). `check_approved_payments()` la llama en
su bucle (comportamiento del cron sin cambios), y el panel la llama directo para el disparo instantáneo.
Esto evita duplicar la lógica de onboarding.

### 3. `backend/api/admin/admin_panel.py` (nuevo)
- Blueprint `admin_panel_bp`.
- Ruta `/admin` que devuelve la página HTML (string embebido o template mínimo).
- Endpoints JSON `pending` / `approve` / `reject`.
- Página HTML: tabla con columnas Nombre, Empresa, Teléfono, Monto, Fecha; botones Aprobar (verde) y
  Rechazar (rojo); auto-refresh cada 10 s; deshabilita botones mientras la petición está en curso.

### 4. `backend/api/admin/__init__.py` (nuevo)
Paquete Python vacío para el nuevo módulo.

### 5. `backend/app.py`
Registrar `admin_panel_bp` junto a los otros blueprints en `create_app()`.

### 6. `backend/tests/test_admin_panel.py` (nuevo)
Tests de los endpoints con `SheetsClient` y `WhatsAppClient` mockeados:
- `pending` devuelve solo los leads con comprobante enviado.
- `approve` marca Aprobado y llama a `process_lead_onboarding`.
- `reject` marca Rechazado y envía mensaje de WhatsApp.
- `approve`/`reject` sobre una fila inexistente responde con error controlado.

## Manejo de Errores y Robustez

- Si Google Sheets o WhatsApp fallan, el endpoint responde `500` con un mensaje JSON; la UI muestra un
  aviso visible y NO rompe la página (el auto-refresh sigue).
- Los botones se deshabilitan mientras la petición está en curso para evitar doble-clic → doble onboarding.
- `approve`/`reject` validan que la fila exista y que el lead esté efectivamente en `Comprobante Enviado`
  antes de actuar (idempotencia básica: aprobar dos veces no reenvía onboarding).

## Fuera de Alcance (YAGNI)

- Autenticación / token del panel (elegido: sin token).
- Visualización de la imagen del comprobante dentro del panel (el comprobante llega por email al ejecutivo).
- Integración con pasarela de pago real (Stripe/MercadoPago); el método real se mantiene como transferencia.
- Estilos "premium" glassmorphism; el panel es interno, basta con un estilo limpio y legible.
