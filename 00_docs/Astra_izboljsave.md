# Kako bi izboljšal tracking infrastrukturo

> Enostranski predlog za dvig zanesljivosti mobilne marketinške analitike — iz perspektive
> data engineerja, ki postavlja podatkovno plast med aplikacijo, MMP-ji in backendom.

## 1. Event taxonomy (enotna shema dogodkov)

Glavni vir neskladij je, da app, MMP in backend govorijo *različne jezike* (`af_purchase`
vs `purchase` vs `txn_completed`). Predlog:

- **Enoten event slovar** v verzioniranem registru (npr. dbt seed ali schema registry):
  `event_name`, `category` (lifecycle / monetization / engagement), `required_params`,
  `revenue_bearing` (bool), `owner`.
- **Stabilen `event_id`** generiran na klientu (UUID) → omogoča idempotentno deduplikacijo
  na vseh slojih (klient retry, MMP S2S, backend) brez heuristike po času.
- **Obvezni konteksti**: `customer_user_id`, `device_id`, `platform`, `app_version`,
  `event_time` (UTC, ISO-8601), `client_sent_time` + `server_received_time` (za merjenje zamika).
- **Naming konvencija** `domain.object.action` (npr. `monetization.subscription.started`)
  in CI lint, ki zavrne nove dogodke izven sheme.

## 2. SKAN conversion value shema

SKAdNetwork 6 bitov (0–63) je redka, a dragocena valuta — izkoristiti jo je treba namensko:

- **Bitno kodiranje**: bita 0–2 = monetizacijski razred (no-rev / low / mid / high LTV),
  bita 3–4 = engagement (registracija, ključno dejanje), bit 5 = redownload/retention zastava.
- **Mapiranje na napovedani LTV**, ne le na prihodek prvih ur — model trenira coarse vrednost
  iz zgodnjih signalov proti dejanskemu D30 LTV iz determinističnih kohort.
- **Crowd anonymity zavedanje**: pri kampanjah pod Applovim pragom je `conversion_value` NULL
  (v tem projektu ~4 kampanje, 100 % NULL). Pipeline mora te primere **eksplicitno označiti**
  (`has_crowd_anonymity`) in jih NE tretirati kot ničelno konverzijo.
- **Postback okna 0/1/2** modeliramo ločeno — pozni postbacki popravljajo zgodnje ocene.

## 3. Reconciliation MMP ↔ backend

Backend je vir resnice za prihodek; MMP je vir resnice za atribucijo. Uskladi ju namensko:

- **Dnevni discrepancy report** (v tem projektu `rec_revenue_discrepancy`): prihodek MMP vs
  backend po kanalu × dan, z `delta_%` in zastavico nad pragom (5 %). V vzorcu MMP **precenjuje
  prihodek za ~10–14 %** glede na backend potrjeni prihodek.
- **Attribution gap** (`rec_attribution_gap`): dogodki brez MMP atribucije (~9 %, organski/ATT
  opt-out) — obstajajo v prihodku, a jih noben kanal ne sme prevzeti; sicer napihnejo ROAS.
- **Deduplikacija** po stabilnem `event_id` (ne po času) in **obravnava poznih dogodkov**
  (event izven 21-dnevnega okna → ločen `is_late_event`, da ne popači dnevnih kohort).
- **Tri-perspektivni ROAS** (`mart_privacy_roas_gap`): MMP vs backend vs SKAN drug ob drugem,
  da je jasno, *kateremu številu in zakaj* zaupamo.

## 4. Alerting na neskladja

Reconciliation je vreden le, če nekdo *ukrepa*. Predlog operativne plasti:

- **dbt testi kot kontrola kakovosti** (že implementirano): `not_null`, `unique`,
  `relationships`, `accepted_values`, custom (negativni revenue, cv izven 0–63, poraba brez
  installov) + `source freshness`.
- **Pragovni alerti**: če dnevni `revenue_delta_%` > 5 % ali attribution gap > 10 % →
  obvestilo (Slack/email) z naborom prizadetih kampanj.
- **Anomaly detection** na CPI/ROAS (npr. odklon > 3σ od 7-dnevnega povprečja) za zgodnje
  zaznavanje pokvarjenega trackinga ali klikovne prevare.
- **Orkestracija** (Airflow): dnevno `simulacija → ingestion → dbt run → dbt test → alert`,
  z zaustavitvijo objave martov ob padlih kontrolah (circuit breaker).

---

**Bistvo**: marketinški vpogled je zanesljiv le toliko, kolikor je zanesljiva podatkovna plast
pod njim. Vrednost prinašam tam — enoten event model, namenska SKAN shema, avtomatiziran
reconciliation in alerting med MMP-ji in backendom.
