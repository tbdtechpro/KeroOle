# O'Reilly Learning – Search API Documentation

> Generated: 2026-03-28  
> Source: Observed network behavior via browser automation on learning.oreilly.com

---

## 1. Autocomplete (Typeahead) Endpoint

**Endpoint:** `GET https://learning.oreilly.com/search/api/v2/autocomplete/`

**Triggered by:** Typing in the search bar (debounced keystrokes)

### Query Parameters

| Parameter  | Description                                   | Example              |
|------------|-----------------------------------------------|----------------------|
| `q`        | Search query string (URL-encoded)             | `Python`, `machine%20learning` |
| `language` | Language filter for suggestions               | `en`               |
| `aia_only` | Restrict to AI Answers content only           | `false`            |

### Example Requests

```
GET /search/api/v2/autocomplete/?q=Python&language=en&aia_only=false
GET /search/api/v2/autocomplete/?q=machine%20learning&language=en&aia_only=false
GET /search/api/v2/autocomplete/?q=JavaScript&language=en&aia_only=false
```

### Response Structure

Returns HTTP `200` with grouped suggestions. Observed categories:
- **Titles** — specific book/course/video names matching the query
- **Skills** — topic/skill keyword suggestions

---

## 2. Main Search Results — URL-Based (Server-Rendered)

The search results page is **server-side rendered**. There is no separate client-side REST call to fetch results — all search parameters are encoded entirely in the page URL.

**Base URL:** `https://learning.oreilly.com/search/`

### Query Parameters — Full Reference

| Parameter          | Type               | Description                                      | Default     |
|--------------------|--------------------|--------------------------------------------------|-------------|
| `q`               | string             | Search query (URL-encoded)                       | _(required)_ |
| `rows`            | integer            | Results per page                                 | `100`       |
| `page`            | integer            | Page number (1-based)                            | `1`         |
| `language`        | string             | Language filter                                  | `en`        |
| `type`            | string (repeatable)| Content type filter — can be specified multiple times | _(all types)_ |
| `order_by`        | string             | Sort order                                       | `relevance` |
| `publication_date` | string            | Date range filter                                | _(all dates)_ |
| `average_rating`  | integer            | Minimum average star rating                      | _(no minimum)_ |

### Full URL Examples

```
/search/?q=Python&rows=100&language=en
/search/?q=Python&type=book&rows=100&language=en
/search/?q=machine%20learning&type=book&rows=10&order_by=published_at&page=2
/search/?q=machine%20learning&type=book&order_by=published_at&rows=10&publication_date=last-6-months
/search/?q=JavaScript&type=book&rows=10&publication_date=last-6-months&average_rating=4
/search/?q=Docker&type=book&type=case_studies&type=conferences&type=video_other&rows=10&language=en
```

---

## 3. Content Type Values (`type` parameter)

| `type` Value       | Description                          |
|----------------------|--------------------------------------|
| `book`             | Books                                |
| `live_course`      | Live / scheduled courses             |
| `on_demand_course` | On-demand video courses              |
| `academies`        | Academy learning paths               |
| `live_events`      | Live events                          |
| `case_studies`     | Case study videos                    |
| `conferences`      | Conference recordings                |
| `video_other`      | Other video content                  |
| `audiobook`        | Audiobooks                           |
| `shortcuts`        | O'Reilly Shortcuts                   |
| `playlist`         | Expert Playlists                     |

> **Note:** Specifying `type=video` is expanded server-side into its constituent subtypes  
> (`case_studies`, `conferences`, `video_other`).

---

## 4. Filter Facets & URL Parameters

### Format Filter
Filters are **additive** (OR logic). Use repeated `type=` parameters to select multiple formats.

### Publication Date (`publication_date` param)

| Value              | Meaning                    |
|--------------------|----------------------------|
| `early-release`  | Early Access content       |
| `last-6-months`  | Published in last 6 months |
| `last-year`      | Published in last year     |
| `last-2-years`   | Published in last 2 years  |
| _(omit param)_     | View all dates             |

### Ratings (`average_rating` param)

| Value | Meaning  |
|-------|----------|
| `4` | 4★ & up  |
| `3` | 3★ & up  |
| `2` | 2★ & up  |
| `1` | 1★ & up  |

### Sort Order (`order_by` param)

| Value            | Meaning              |
|------------------|----------------------|
| _(omit param)_   | Relevance (default)  |
| `published_at` | Publication date     |
| `popularity`   | Popularity           |
| `rating`       | Rating               |
| `date_added`   | Date added           |
| `last_updated` | Last updated         |

### Level Filter
Uses a range slider (Beginner → Intermediate → Advanced). URL parameter name not confirmed in this session.

### Language Filter
Includes an internal search field with available languages (Chinese, Dutch, English, etc.) and per-language result counts.

---

## 5. Pagination

| Mechanism          | Detail                                   |
|--------------------|------------------------------------------|
| Page size          | `rows` param: `10`, `25`, `50`, `100` |
| Page number        | `page` param: 1-based integer          |
| Result count label | Displayed as `1 - {rows} of {total}`  |
| Navigation         | Server-rendered page links with `page=N` |

---

## 6. Supporting API Endpoints (Internal)

| Endpoint                                                          | Method | Purpose                                            |
|-------------------------------------------------------------------|--------|----------------------------------------------------|
| `/search/api/interactions/`                                     | POST   | Logs user interaction events (telemetry)           |
| `/api/v1/reports/batch/`                                        | POST   | Batch page-view analytics reporting                |
| `/api/v2/metadata/?include_facets=true&has_future_live_event=true` | GET | Fetches metadata/facets on new searches            |
| `/api/v3/collections/`                                          | GET    | Fetches user's personal collections/playlists      |
| `/api/v3/collections/{urn}/cover/`                              | GET    | Fetches cover art for a specific collection        |
| `/api/v2/collections/cover-image/api-url?image1=...&image2=...` | GET   | Generates cover collage for multi-book collections |
| `/covers/urn:orm:{type}:{ID}/160h/?format=webp`                 | GET    | Individual content cover image (WebP, 160px tall)  |

### Cover Image URL Format

```
https://learning.oreilly.com/covers/urn:orm:book:{ISBN-13}/160h/?format=webp
https://learning.oreilly.com/covers/urn:orm:video:{ID}/160h/?format=webp
```

---

## 7. Result Card Properties (Observed in UI)

| Field               | Notes                                                |
|---------------------|------------------------------------------------------|
| Title               | Linked to content page                               |
| Author(s)           | Linked, comma-separated for multiple authors         |
| Publisher           | Linked                                               |
| Publication Date    | Month + Year                                         |
| Content Type        | Book, On-demand course, Expert Playlist, Live Event  |
| Page Count          | For books only                                       |
| Duration            | For video/courses (e.g., `62h 31m`)                |
| Star Rating         | Average float, displayed as filled stars             |
| Review Count        | Integer                                              |
| Description Excerpt | Query terms bolded in the snippet                    |
| Languages Available | Shown for multilingual content (e.g., `+5 more`)  |
| URN Identifier      | `urn:orm:book:{ISBN}` — used in cover image URLs   |

---

## 8. Key Integration Notes

1. **Authentication:** No API key was observed in public search requests. Full content access is likely gated by session authentication cookies.
2. **URL-driven:** Search is entirely URL-driven — construct and navigate to a search URL directly without any POST requests.
3. **Multi-value types:** Stack multiple `type=` parameters to filter across several content types simultaneously.
4. **Autocomplete is the only true REST endpoint** observed in the search flow; the results page itself is server-rendered HTML.
5. **Analytics calls** (Amplitude, Google Analytics) fire on each search action — telemetry only, not relevant for integration.
6. **Filters persist across queries:** Active filters (type, publication_date, etc.) are preserved when a new search query is submitted.

---

## 9. Searches Performed During This Session

| Query              | Filters Applied                                              | Results |
|--------------------|--------------------------------------------------------------|---------|
| `Python`         | None                                                         | 19,605  |
| `Python`         | type=book                                                    | 13,989  |
| `machine learning` | type=book                                                  | 49,314  |
| `machine learning` | type=book, order_by=published_at, rows=10                  | 49,314  |
| `machine learning` | type=book, publication_date=last-6-months                  | 1,094   |
| `JavaScript`     | type=book, publication_date=last-6-months                    | 551     |
| `JavaScript`     | type=book, publication_date=last-6-months, average_rating=4  | 39      |
| `Docker`         | type=book + video subtypes, language=en                      | 4,895   |
