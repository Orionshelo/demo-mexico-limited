# Mexico Limited - Backend API

Esta es la API del backend desarrollada en Flask para calcular la similitud por coseno entre las necesidades de los emprendedores y los servicios ofrecidos por Mexico Limited.

## Requisitos

- Python 3.9+
- Flask
- scikit-learn
- flask-cors

## Instalación

1. Activa el entorno virtual:
   En Windows:
   ```bash
   venv\Scripts\activate
   ```
   En macOS/Linux:
   ```bash
   source venv/bin/activate
   ```

2. Instala las dependencias si no lo has hecho:
   ```bash
   pip install Flask scikit-learn flask-cors supabase
   ```

## Ejecución

Para correr el servidor localmente en el puerto 5000:
```bash
python app.py
```

## Endpoints

### `POST /api/match`
Calcula la compatibilidad entre las necesidades del usuario y los servicios del catálogo.

**Request:**
```json
{
  "needs": "Necesito ayuda para vender más por redes sociales y tomar fotos de mis productos."
}
```

**Response:**
```json
{
  "matches": [
    {
      "id": "2",
      "name": "Fotografía con Inteligencia Artificial",
      ...
      "match_score": 24.5
    },
    ...
  ]
}
```
