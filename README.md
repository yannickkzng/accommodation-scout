# Accommodation Scout GPT Backend

Backend-MVP für einen Custom GPT, der verfügbare Hotels, Apartments und Ferienunterkünfte anhand persönlicher Kriterien sucht, normalisiert, bewertet und als strukturierte Ergebnisse an eine GPT Action zurückgibt.

## Was dieses Paket enthält

- FastAPI Backend mit Endpoint `POST /search-accommodations`
- Pydantic-Datenmodell für Suchanfragen und Ergebnisse
- Mock-Provider für sofortige lokale Tests ohne API-Keys
- Provider-Schnittstellen für Booking.com, Expedia, Amadeus und Hotelbeds
- Filterlogik für Verfügbarkeit, Preis, Mindestbewertung, Unterkunftstypen und Must-haves
- Scoring-Engine für Bewertung, Lage, Preis-Leistung, Storno-Flexibilität, Ausstattung und Risiken
- Deduplizierung ähnlicher Unterkünfte über Name, Adresse und Koordinaten
- OpenAPI-Schema für die GPT Action
- GPT-Instructions zum direkten Einfügen in den GPT Builder

## Architektur

```text
Custom GPT
  ↓ Action-Aufruf
POST /search-accommodations
  ↓
FastAPI Backend
  ↓
Provider Connectoren: Booking / Expedia / Amadeus / Hotelbeds / Mock
  ↓
Normalisierung → Filter → Deduplizierung → Scoring → Top-Ergebnisse
  ↓
GPT formuliert die Empfehlung
```

## Lokaler Start

### 1. Projekt entpacken

```bash
cd accommodation-scout
```

### 2. Virtuelle Umgebung erstellen

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# oder unter Windows PowerShell:
# .venv\Scripts\Activate.ps1
```

### 3. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### 4. `.env` anlegen

```bash
cp .env.example .env
```

Für lokale Tests kannst du die Datei unverändert lassen. Dann wird der Mock-Provider genutzt.

### 5. Server starten

```bash
uvicorn app.main:app --reload --port 8000
```

### 6. Test-Request senden

```bash
curl -X POST http://localhost:8000/search-accommodations \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "Florenz",
    "checkin": "2026-09-12",
    "checkout": "2026-09-16",
    "adults": 2,
    "rooms": 1,
    "max_total_price": 900,
    "currency": "EUR",
    "min_rating": 8.5,
    "accommodation_types": ["hotel", "apartment"],
    "must_haves": ["free_cancellation"],
    "nice_to_haves": ["breakfast", "central_location"],
    "no_gos": ["noise_complaints", "high_deposit"],
    "sort_preference": "best_value"
  }'
```

## GPT Action einrichten

1. ChatGPT öffnen
2. GPT erstellen
3. Instructions aus `gpt/GPT_INSTRUCTIONS.md` einfügen
4. Action hinzufügen
5. OpenAPI-Schema aus `gpt/openapi-action.yaml` einfügen
6. `servers.url` auf deine produktive Backend-URL ändern
7. Authentifizierung konfigurieren
8. Testen

Wichtig: Bei lokalem Test über ChatGPT brauchst du eine öffentlich erreichbare URL, z. B. über Deployment oder einen sicheren Tunnel. Für Produktion besser nicht dauerhaft über einen lokalen Tunnel arbeiten.

## Authentifizierung

Standardmäßig ist lokale Entwicklung offen. Für Produktion setze in `.env`:

```env
ACCOMMODATION_SCOUT_API_TOKEN=dein-sicherer-token
```

Dann muss jeder Request diesen Header enthalten:

```http
Authorization: Bearer dein-sicherer-token
```

## Provider anbinden

Die Dateien in `app/providers/` sind bewusst getrennt. Pro Plattform baust du einen eigenen Connector, der am Ende `AccommodationResult` Objekte zurückgibt.

Aktuell aktiv:

- `MockProvider`: sofort lauffähig

Vorbereitet:

- `BookingProvider`
- `ExpediaProvider`
- `AmadeusProvider`
- `HotelbedsProvider`

Die echten Anbieter-APIs haben jeweils eigene Zugangsvoraussetzungen, Feldnamen, Preislogiken und Nutzungsbedingungen. Deshalb sind die Connectoren als Adapter vorbereitet, aber nicht mit erfundenen Endpunkten implementiert.

## Nächste sinnvolle Ausbaustufen

1. Amadeus als ersten echten Provider anbinden, weil der Developer-Zugang meist am einfachsten zu testen ist.
2. Booking.com oder Expedia als Affiliate-/Partnerquelle ergänzen.
3. Deduplizierung über Telefonnummer, Chain-ID oder Anbieter-Mapping verbessern.
4. Review-Analyse mit echten Review-Snippets erweitern.
5. Preis-Historie speichern, um Deals besser zu erkennen.
6. Persönliches Nutzerprofil speichern: Mindestbewertung, Lieblingslagen, No-Gos, Budgetlogik.

## Sicherheit und Genauigkeit

Das Backend soll die Quelle der Wahrheit sein. GPT soll keine Preise, Verfügbarkeit oder Storno-Regeln erfinden. Wenn Daten fehlen, werden sie als `unknown` oder `nicht gefunden` markiert.
