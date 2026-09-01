# Set-Export für KI-Review: Nutzung und Best Practices

> English version: [export-set-usage.md](export-set-usage.md)

Wie [`scripts/export_set.py`](../scripts/export_set.py) benutzt wird
und wie ein KI-gestütztes Review auf der Exportdatei abläuft.

## Zweck

`scripts/export_set.py` schreibt EIN Content-Set als Snapshot in eine
einzige YAML- (Default) oder JSON-Datei, damit ein KI-Assistent (oder
ein Mensch) das ganze Set in einem Durchgang prüfen kann: Syntax,
Korrektheit, Konsistenz über die Lektionen hinweg.

Der Export ist ein **Nur-Lese-Snapshot, KEIN Re-Import-Format**. Das
Skript schreibt nie nach `sets/`, und nichts liest den Export zurück.
Änderungen fließen ausschließlich über die einzelnen schema-validierten
Lektions-JSONs unter `sets/` ein.

## Nutzung

```bash
make export ARGS="<set-slug> [--lang <lang>] [--format yaml|json] [--out PFAD] [--split-size N]"
# oder direkt (Fallback; innerhalb der venv aus dem Quick Start):
python3 scripts/export_set.py <set-slug> [--lang <lang>] [--format yaml|json] [--out PFAD] [--split-size N]
```

| Argument | Bedeutung | Default |
| --- | --- | --- |
| `<set-slug>` | Set-Id aus dem Wurzel-`manifest.yaml` (z. B. `fuehrerschein-uebung-from-de`) oder der Ordnername des Set-Pfads (z. B. `fuehrerschein-uebung` für `sets/de/fuehrerschein-uebung`) | Pflicht |
| `--lang` | Quellsprachen-Verzeichnis (`sets/<lang>/`), das einen Ordnernamen-Slug eindeutig macht, der unter mehreren Quellsprachen existiert | `de` |
| `--format` | Ausgabeformat: `yaml` oder `json` | `yaml` |
| `--out` | Pfad der Ausgabedatei (nicht kombinierbar mit `--split-size`) | `exports/<set-slug>-<lang>-<timestamp>.<format>` |
| `--split-size` | Export in mehrere Dateien von je hoechstens N Lektionen aufteilen, statt einer Datei | aus (eine Datei) |

Beispiele:

```bash
# Standardfall: YAML-Export nach exports/ (das Set liegt unter sets/de/)
make export ARGS="fuehrerschein-uebung"
# -> exports/fuehrerschein-uebung-de-<timestamp>.yaml

# Sonderfall: JSON an einen eigenen Pfad (nur wenn ein Tooling explizit JSON braucht)
make export ARGS="fuehrerschein-uebung --format json --out /tmp/review.json"

# Kleines/grosses Set: in Teile von je hoechstens 2 Lektionen aufteilen,
# fuer eine KI mit begrenztem Kontextfenster
make export ARGS="fuehrerschein-uebung --split-size 2"
# -> exports/fuehrerschein-uebung-de-<timestamp>-part01-of-3.yaml, part02-of-3, part03-of-3
```

Ohne `--out` landet die Datei in `exports/` nach dem Muster
`<set-slug>-<lang>-<timestamp>.<format>` (bei `--split-size` je eine
Datei pro Teil nach `<set-slug>-<lang>-<timestamp>-partNN-of-MM.<format>`).
Das Verzeichnis `exports/` wird bei Bedarf angelegt und ist
**gitignored**: Exportdateien sind Wegwerf-Artefakte fürs Review und
werden nie committet.

Jeder von `--split-size` geschriebene Teil ist eigenstaendig: er traegt
seine eigene `review_instructions`-Kopie sowie die Felder
`part`/`of`/`lesson_count`/`total_lesson_count`, sodass jeder einzelne
Teil fuer sich, in beliebiger Reihenfolge, an eine KI zum Review
gegeben werden kann.

Ein unbekannter oder mehrdeutiger Slug bricht mit Exit-Code 2 und
einer Liste der verfügbaren Sets ab. Umlaute und alle anderen
Nicht-ASCII-Zeichen bleiben echtes UTF-8.

## Workflow: KI-Review durchführen

1. **Export erzeugen:**

   ```bash
   make export ARGS="fuehrerschein-uebung"
   ```

2. **Exportdatei öffnen** und im `review_instructions`-Block am Anfang
   der Datei den Abschnitt "Quellkapitel" finden.

3. **Quellkapitel manuell einfügen**, falls die Aufgaben gegen ein
   Lehrbuch-Kapitel oder anderes Referenzmaterial geschrieben wurden,
   das nicht in diesem Repo liegt. Das ist wichtig: ohne Kapitel prüft
   die KI fachliche Aussagen nur gegen ihr Allgemeinwissen, nicht
   gegen die tatsächliche Lehrgrundlage (siehe die Prioritätsregel im
   `review_instructions`-Block).

4. **Die komplette Datei an eine KI geben.** Der Export ist
   selbsttragend: das eingebettete Feld `review_instructions` sagt der
   KI ihre Rolle, die Prüfkategorien und das erwartete Output-Format,
   es braucht keinen zusätzlichen Prompt.

5. **Ergebnis durchgehen:** eine Befundliste pro Lektion, jeder Befund
   mit Schweregrad (KRITISCH/MITTEL/GERING) und einem konkreten
   Verbesserungsvorschlag.

6. **Akzeptierte Vorschläge MANUELL übernehmen**, in die einzelnen
   schema-validierten Lektions-JSONs unter `sets/`. Die Exportdatei
   nie zurückspielen: nichts liest sie ein.

7. **Nach jeder Content-Änderung die Validatoren erneut laufen
   lassen:**

   ```bash
   python3 scripts/validate_content.py
   node scripts/validate_with_engine.mjs .
   ```

   Das KI-Review ist eine zusätzliche semantische Ebene; es ersetzt
   die technischen Validatoren nicht.

## Best Practices

- **Der Export ist ein Snapshot, kein Live-Dokument.** Nach jeder
  inhaltlichen Änderung neu exportieren; nie einen alten Export
  weiterprüfen lassen.
- **Quellkapitel bei jedem Review neu einfügen**, wenn es sich
  geändert hat; nicht aus einem alten Export kopieren.
- **Große Sets in Portionen prüfen** (z. B. 8-10 Lektionen pro
  Durchgang), wenn der Kontext der verwendeten KI begrenzt ist - dafür
  `--split-size` nutzen, statt den Export von Hand zu zerschneiden.
- **YAML als Standard belassen**; JSON nur, wenn ein Tooling das
  explizit braucht.
- **Kein Copy-Paste von KI-Vorschlägen ohne Gegenlesen.** Die KI
  liefert Vorschläge, keine fertigen Wahrheiten, gerade bei
  Fachinhalten ohne Quellkapitel.
- **Exportdateien nie committen.** Sie sind Wegwerf-Artefakte fürs
  Review; genau dafür ist `exports/` gitignored.
- **Befunde ohne Quellkapitel entsprechend einordnen.** Inhaltliche
  Befunde, die nur gegen Allgemeinwissen geprüft wurden, verdienen
  geringeres Vertrauen. Die KI kennzeichnet das selbst im Output
  ("geprüft gegen Allgemeinwissen, kein Quellkapitel vorhanden");
  beim Gegenlesen trotzdem im Kopf behalten.
