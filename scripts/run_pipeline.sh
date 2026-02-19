#!/usr/bin/env bash
# Full data ingestion pipeline for Verkiezing Vibecheck.
#
# Usage:
#   ./scripts/run_pipeline.sh                        # run all steps for all parties
#   ./scripts/run_pipeline.sh --from step5           # resume from a specific step
#   ./scripts/run_pipeline.sh --party BIJ1           # run all steps for one party only
#   ./scripts/run_pipeline.sh --party BIJ1 --from step5
#
# Steps:
#   step1  ingest           Load YAML + PDFs into DB
#   step2  hydrate-bluesky  Find candidate Bluesky handles, write to YAML
#   step3  hydrate-linkedin Find candidate LinkedIn URLs, write to YAML
#   step4  ingest-again     Re-ingest YAML so hydrated fields land in DB
#   step5  embeddings       Generate pgvector embeddings for document chunks
#   step6  summaries        Generate AI party program summaries
#   step7  comparisons      Generate AI topic comparisons (skipped when --party is set)
#   step8  social           Fetch Bluesky posts + AI social summaries
#   step9  linkedin         Fetch LinkedIn posts per candidate
#   step10 motions          Fetch council motions from Notubiz (always runs unfiltered)
#   step11 motion-summaries Generate AI motion summaries per party

set -euo pipefail

STEPS=(step1 step2 step3 step4 step5 step6 step7 step8 step9 step10 step11)
FROM_STEP=""
PARTY=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --from)
            FROM_STEP="$2"
            shift 2
            ;;
        --party)
            PARTY="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Usage: $0 [--from <stepN>] [--party <abbreviation>]"
            exit 1
            ;;
    esac
done

# Build optional --party flag to pass down to scripts
PARTY_ARG=()
if [[ -n "$PARTY" ]]; then
    PARTY_ARG=(--party "$PARTY")
    echo "Party filter: $PARTY"
fi

# Determine which steps to skip
skip=true
if [[ -z "$FROM_STEP" ]]; then
    skip=false
fi

run_step() {
    local step_id="$1"
    local label="$2"
    shift 2
    local cmd=("$@")

    if [[ "$skip" == true ]]; then
        if [[ "$step_id" == "$FROM_STEP" ]]; then
            skip=false
        else
            echo "⏭  Skipping $step_id: $label"
            return
        fi
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  $step_id: $label"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    "${cmd[@]}"
}

run_step step1  "Ingest YAML + PDFs into DB" \
    uv run python scripts/ingest.py ${PARTY_ARG[@]:+"${PARTY_ARG[@]}"}

run_step step2  "Hydrate Bluesky handles (writes to YAML)" \
    uv run python scripts/hydrate_bluesky_handles.py ${PARTY_ARG[@]:+"${PARTY_ARG[@]}"}

run_step step3  "Hydrate LinkedIn URLs (writes to YAML)" \
    uv run python scripts/hydrate_linkedin_urls.py ${PARTY_ARG[@]:+"${PARTY_ARG[@]}"}

run_step step4  "Re-ingest YAML so hydrated fields land in DB" \
    uv run python scripts/ingest.py ${PARTY_ARG[@]:+"${PARTY_ARG[@]}"}

run_step step5  "Generate pgvector embeddings" \
    uv run python scripts/generate_embeddings.py ${PARTY_ARG[@]:+"${PARTY_ARG[@]}"}

run_step step6  "Generate AI party program summaries" \
    uv run python scripts/generate_summaries.py ${PARTY_ARG[@]:+"${PARTY_ARG[@]}"}

if [[ -n "$PARTY" ]]; then
    # Advance the skip pointer if --from step7 was specified
    if [[ "$skip" == true && "$FROM_STEP" == "step7" ]]; then
        skip=false
    fi
    echo ""
    echo "⏭  Skipping step7: Generate AI topic comparisons (cross-party, not applicable to single-party run)"
else
    run_step step7  "Generate AI topic comparisons" \
        uv run python scripts/generate_comparisons.py
fi

run_step step8  "Fetch Bluesky posts + AI social summaries" \
    uv run python scripts/fetch_social.py ${PARTY_ARG[@]:+"${PARTY_ARG[@]}"}

run_step step9  "Fetch LinkedIn posts per candidate" \
    uv run python scripts/fetch_linkedin.py ${PARTY_ARG[@]:+"${PARTY_ARG[@]}"}

run_step step10 "Fetch council motions from Notubiz" \
    uv run python scripts/fetch_motions.py

run_step step11 "Generate AI motion summaries per party" \
    uv run python scripts/generate_motion_summaries.py ${PARTY_ARG[@]:+"${PARTY_ARG[@]}"}

echo ""
echo "✓ Pipeline complete"
