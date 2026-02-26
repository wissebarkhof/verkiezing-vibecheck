"""Generate or update an election YAML from the official Kiesraad candidate CSV.

The CSV is the authoritative source for which parties and candidates appear on
the ballot.  The YAML is the enriched config used by the rest of the pipeline;
it adds websites, logos, program PDFs, social handles, seat counts, topics, etc.

When an existing YAML is found the script *merges*:
  - Party / candidate names and positions come from the CSV.
  - All other party fields (website, logo, program_pdf, current_seats, …) and
    candidate fields (bluesky, linkedin) are preserved from the YAML.
  - New parties / candidates are appended; nothing is deleted.

Usage:
    # First run — create YAML from scratch:
    uv run python scripts/generate_election_yaml.py --gemeente Amsterdam
    uv run python scripts/generate_election_yaml.py --gemeente Rotterdam
    # For tricky gemeente names (CSV name ≠ desired slug):
    uv run python scripts/generate_election_yaml.py \\
        --gemeente "'s-Gravenhage" --city den-haag \\
        --election-name "Gemeenteraadsverkiezingen Den Haag 2026"

    # Subsequent runs — merge CSV updates into existing YAML:
    uv run python scripts/generate_election_yaml.py --gemeente Amsterdam

    # Custom paths:
    uv run python scripts/generate_election_yaml.py \\
        --gemeente Amsterdam \\
        --csv data/raw_data/Kandidatenlijsten_GR2026.csv \\
        --output data/elections/gemeenteraad-2026/amsterdam.yml

    # Preview without writing:
    uv run python scripts/generate_election_yaml.py --gemeente Amsterdam --dry-run
"""

import argparse
import csv
import logging
import re
import sys
import unicodedata
from pathlib import Path

from ruamel.yaml import YAML

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Default paths
DEFAULT_CSV = Path("data/raw_data/Kandidatenlijsten_GR2026.csv")
DEFAULT_RAADZETELS_CSV = Path("data/raw_data/Raadzetels_GR2026.csv")
DEFAULT_OUTPUT_DIR = Path("data/elections/gemeenteraad-2026")

# Election metadata template used when creating a YAML from scratch.
ELECTION_TEMPLATE = {
    "name": "",   # filled in at runtime from --election-name or derived
    "city": "",   # lowercased gemeente name
    "date": "",   # filled in from --date
}


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------


def load_total_seats(raadzetels_csv: Path, gemeente: str) -> int | None:
    """Return the total council seat count for a gemeente from the Raadzetels CSV."""
    gemeente_norm = _normalize(gemeente)
    try:
        with open(raadzetels_csv, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh, delimiter=";")
            for row in reader:
                if _normalize(row.get("GemeenteNaam", "")) == gemeente_norm:
                    return int(row["AantalZetels"])
    except (FileNotFoundError, KeyError, ValueError):
        pass
    return None

def _normalize(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace, remove punctuation."""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = nfkd.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-z0-9\s]", "", ascii_text.lower())
    return " ".join(cleaned.split())


def _candidate_name(roepnaam: str, tussenv: str, achternaam: str) -> str:
    parts = [p for p in (roepnaam, tussenv, achternaam) if p.strip()]
    return " ".join(parts)


def load_csv(csv_path: Path, gemeente: str) -> dict[int, dict]:
    """Parse the Kiesraad CSV and return parties keyed by list number.

    Returns:
        {list_number: {
            "list_name": str,           # official CSV name
            "candidates": [
                {"position": int, "name": str},
                ...
            ]
        }}
    """
    gemeente_norm = _normalize(gemeente)
    parties: dict[int, dict] = {}

    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        for row in reader:
            if _normalize(row.get("GemeenteNaam", "")) != gemeente_norm:
                continue
            try:
                list_num = int(row["LijstNummer"])
                cand_num = int(row["KandidaatNummer"])
            except (ValueError, KeyError):
                continue

            if list_num not in parties:
                parties[list_num] = {
                    "list_name": row.get("LijstNaam", "").strip(),
                    "candidates": [],
                }

            name = _candidate_name(
                row.get("Roepnaam", ""),
                row.get("Tussenvoegsel", ""),
                row.get("Achternaam", ""),
            )
            parties[list_num]["candidates"].append(
                {"position": cand_num, "name": name}
            )

    # Sort candidates by position within each party
    for p in parties.values():
        p["candidates"].sort(key=lambda c: c["position"])

    return parties


# ---------------------------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------------------------

def _strip_abbrev(name: str) -> str:
    """Remove trailing parenthetical like '(PvdA)' or '(1W1T)' from CSV names."""
    return re.sub(r"\s*\([^)]+\)\s*$", "", name).strip()


def _find_yaml_party(
    csv_list_num: int,
    csv_list_name: str,
    yaml_parties: list,
) -> dict | None:
    """Find the best matching party in the YAML list.

    Matching strategy (in order):
    1. list_number field (exact)
    2. Normalized name match after stripping parenthetical abbreviations
    3. CSV abbreviation (in parentheses) matches YAML abbreviation field
    """
    # Extract abbreviation from CSV name, e.g. "LP (Libertaire Partij)" → "LP"
    m = re.match(r"^([A-Za-z0-9]+)\s*\(", csv_list_name)
    csv_leading_abbrev = m.group(1).upper() if m else None

    # 1. list_number
    for p in yaml_parties:
        if p.get("list_number") == csv_list_num:
            return p

    # 2. Normalized full name
    csv_norm = _normalize(_strip_abbrev(csv_list_name))
    for p in yaml_parties:
        if _normalize(p.get("name", "")) == csv_norm:
            return p

    # 3. Leading token of CSV name matches YAML abbreviation
    if csv_leading_abbrev:
        for p in yaml_parties:
            if p.get("abbreviation", "").upper() == csv_leading_abbrev:
                return p

    return None


def _merge_candidates(
    csv_candidates: list[dict],
    yaml_candidates: list,
) -> list[dict]:
    """Return a merged candidate list.

    CSV is authoritative for names and positions.
    YAML enrichment (bluesky, linkedin) is preserved per position.
    """
    yaml_by_pos = {c.get("position"): c for c in (yaml_candidates or [])}

    merged = []
    for csv_cand in csv_candidates:
        pos = csv_cand["position"]
        existing = yaml_by_pos.get(pos, {})

        entry: dict = {
            "name": csv_cand["name"],
            "position": pos,
        }
        # Preserve enrichment fields
        for field in ("bluesky", "linkedin"):
            val = existing.get(field)
            if val:
                entry[field] = val

        merged.append(entry)

    return merged


# ---------------------------------------------------------------------------
# YAML build / merge
# ---------------------------------------------------------------------------

def _build_party_entry(
    csv_list_num: int,
    csv_list_name: str,
    csv_candidates: list[dict],
    existing: dict | None,
) -> dict:
    """Build a party dict, merging CSV data with any existing YAML enrichment."""
    # Prefer the YAML's curated name; fall back to CSV name (stripped of abbrev)
    name = (existing or {}).get("name") or _strip_abbrev(csv_list_name)

    # Derive abbreviation from parenthetical if present, else keep existing
    m = re.search(r"\(([^)]+)\)$", csv_list_name)
    csv_abbrev = m.group(1) if m else ""
    abbreviation = (existing or {}).get("abbreviation") or csv_abbrev

    entry: dict = {
        "name": name,
        "abbreviation": abbreviation,
        "list_number": csv_list_num,
    }

    # Preserve all optional enrichment fields from existing YAML
    for field in (
        "website",
        "logo",
        "program_pdf",
        "current_seats",
        "polled_seats",
        "poll_updated_at",
    ):
        val = (existing or {}).get(field)
        if val is not None:
            entry[field] = val

    entry["candidates"] = _merge_candidates(
        csv_candidates,
        (existing or {}).get("candidates", []),
    )

    return entry


def merge_yaml(
    csv_parties: dict[int, dict],
    existing_config: dict | None,
) -> dict:
    """Merge CSV party/candidate data into the existing YAML config (or create fresh)."""

    # Preserve top-level election metadata and other sections
    config: dict = {}
    if existing_config:
        # Keep election metadata
        config["election"] = dict(existing_config.get("election", {}))
    else:
        config["election"] = dict(ELECTION_TEMPLATE)

    existing_parties: list = (existing_config or {}).get("parties", [])

    new_parties = []
    for list_num in sorted(csv_parties):
        csv_party = csv_parties[list_num]
        existing = _find_yaml_party(list_num, csv_party["list_name"], existing_parties)

        party_entry = _build_party_entry(
            list_num,
            csv_party["list_name"],
            csv_party["candidates"],
            existing,
        )
        new_parties.append(party_entry)

        action = "updated" if existing else "added"
        logger.info(
            f"  [{action:7s}] #{list_num:2d} {party_entry['name']} "
            f"({len(party_entry['candidates'])} candidates)"
        )

    config["parties"] = new_parties

    # Preserve topics and polling_sources from existing YAML
    for section in ("topics", "polling_sources"):
        val = (existing_config or {}).get(section)
        if val:
            config[section] = val

    return config


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _derive_city_slug(gemeente: str) -> str:
    """Derive a URL-friendly city slug from a gemeente name.

    "'s-Gravenhage" → "den-haag" won't work automatically — use --city for that.
    "Amsterdam"     → "amsterdam"
    "Rotterdam"     → "rotterdam"
    """
    slug = gemeente.lower()
    slug = re.sub(r"[''`]", "", slug)   # remove apostrophes
    slug = re.sub(r"[^a-z0-9]+", "-", slug)  # non-alnum → hyphen
    return slug.strip("-")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate/update an election YAML from the Kiesraad candidate CSV"
    )
    parser.add_argument(
        "--gemeente",
        default="Amsterdam",
        help="Municipality name as it appears in the CSV (default: Amsterdam)",
    )
    parser.add_argument(
        "--city",
        default=None,
        help=(
            "City slug used for the YAML election.city field and output filename "
            "(default: derived from --gemeente, e.g. 'amsterdam'). "
            "Set explicitly for tricky names, e.g. --gemeente \"'s-Gravenhage\" --city den-haag"
        ),
    )
    parser.add_argument(
        "--election-name",
        default=None,
        dest="election_name",
        help="Full election name (default: 'Gemeenteraadsverkiezingen {Gemeente} 2026')",
    )
    parser.add_argument(
        "--date",
        default="2026-03-18",
        help="Election date in YYYY-MM-DD format (default: 2026-03-18)",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help=f"Path to the Kiesraad kandidatenlijsten CSV (default: {DEFAULT_CSV})",
    )
    parser.add_argument(
        "--raadzetels-csv",
        type=Path,
        default=DEFAULT_RAADZETELS_CSV,
        dest="raadzetels_csv",
        help=f"Path to the Kiesraad raadzetels CSV for total seat counts (default: {DEFAULT_RAADZETELS_CSV})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Path to the output YAML file "
            "(default: data/elections/gemeenteraad-2026/<city>.yml)"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and merge without writing to disk",
    )
    args = parser.parse_args()

    if not args.csv.exists():
        logger.error(f"CSV not found: {args.csv}")
        sys.exit(1)

    city_slug = args.city or _derive_city_slug(args.gemeente)
    output_path = args.output or (DEFAULT_OUTPUT_DIR / f"{city_slug}.yml")

    # Load CSV
    logger.info(f"Reading CSV: {args.csv}")
    csv_parties = load_csv(args.csv, args.gemeente)
    if not csv_parties:
        logger.error(f"No rows found for gemeente '{args.gemeente}' in {args.csv}")
        sys.exit(1)
    logger.info(f"Found {len(csv_parties)} parties for {args.gemeente}")

    # Load existing YAML (if any)
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False

    existing_config: dict | None = None
    if output_path.exists():
        logger.info(f"Merging into existing YAML: {output_path}")
        with open(output_path) as fh:
            existing_config = yaml.load(fh)
    else:
        logger.info(f"No existing YAML found — creating fresh: {output_path}")

    # Merge
    logger.info("Merging CSV data into YAML…")
    merged = merge_yaml(csv_parties, existing_config)

    # Fill in election metadata for new YAMLs (or when fields are empty)
    election_meta = merged.setdefault("election", {})
    if not election_meta.get("name"):
        election_meta["name"] = args.election_name or f"Gemeenteraadsverkiezingen {args.gemeente} 2026"
    if not election_meta.get("city"):
        election_meta["city"] = city_slug
    if not election_meta.get("date"):
        election_meta["date"] = args.date

    # Always (re)populate total_seats from the Raadzetels CSV
    total_seats = load_total_seats(args.raadzetels_csv, args.gemeente)
    if total_seats is not None:
        election_meta["total_seats"] = total_seats
        logger.info(f"Total council seats for {args.gemeente}: {total_seats}")
    elif args.raadzetels_csv.exists():
        logger.warning(f"Gemeente '{args.gemeente}' not found in {args.raadzetels_csv}")

    if args.dry_run:
        import io
        buf = io.StringIO()
        yaml.dump(merged, buf)
        print(buf.getvalue())
        logger.info("[dry-run] No file written")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as fh:
        yaml.dump(merged, fh)

    logger.info(f"Written to {output_path}")


if __name__ == "__main__":
    main()
