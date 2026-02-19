import logging
import time

import litellm

from app.config import settings

logger = logging.getLogger(__name__)

_RETRY_DELAYS = [2, 5, 10]  # seconds between attempts on overload/server errors

# Default models — override via env vars if needed
CHAT_MODEL = "anthropic/claude-sonnet-4-5-20250929"
EMBEDDING_MODEL = "openai/text-embedding-3-small"


def _complete(prompt: str, system: str = "", model: str = CHAT_MODEL) -> str:
    """Call LLM via LiteLLM and return the response text.

    Retries up to 3 times with increasing delays on server overload (529).
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    last_exc = None
    for attempt, delay in enumerate([0] + _RETRY_DELAYS):
        if delay:
            logger.warning(f"LLM overloaded, retrying in {delay}s (attempt {attempt + 1}/4)...")
            time.sleep(delay)
        try:
            response = litellm.completion(model=model, messages=messages, temperature=0.3)
            return response.choices[0].message.content
        except (litellm.InternalServerError, litellm.ServiceUnavailableError) as e:
            last_exc = e
    raise last_exc


SYSTEM_PROMPT = (
    "Je bent een behulpzame assistent die informatie geeft over de "
    "gemeenteraadsverkiezingen in Amsterdam 2026. "
    "Antwoord altijd in het Nederlands. Wees beknopt en feitelijk."
)


def summarize_program(party_name: str, program_text: str) -> str:
    """Generate a Dutch summary of a party's election program."""
    # Truncate to ~12k chars to stay within context limits
    text = program_text[:12000]
    prompt = (
        f"Hieronder staat (een deel van) het verkiezingsprogramma van {party_name} "
        f"voor de gemeenteraadsverkiezingen Amsterdam 2026.\n\n"
        f"Geef een samenvatting van maximaal 300 woorden. Benoem de belangrijkste "
        f"standpunten en thema's. Schrijf in het Nederlands.\n\n"
        f"---\n{text}\n---"
    )
    return _complete(prompt, system=SYSTEM_PROMPT)


def compare_topics(topic: str, party_positions: dict[str, str]) -> dict[str, str]:
    """Generate a per-party comparison for a given topic.

    party_positions: {party_name: relevant_text_excerpt}
    Returns: {party_name: summary_of_position}
    """
    parts = []
    for party, text in party_positions.items():
        excerpt = text[:3000]
        parts.append(f"### {party}\n{excerpt}")

    prompt = (
        f"Onderwerp: {topic}\n\n"
        f"Hieronder staan relevante fragmenten uit de verkiezingsprogramma's "
        f"van verschillende partijen over dit onderwerp.\n\n"
        + "\n\n".join(parts)
        + "\n\n"
        f"Geef per partij een samenvatting van hun standpunt over '{topic}' "
        f"in 2-3 zinnen. Antwoord in JSON-formaat: "
        f'{{"partijnaam": "samenvatting standpunt", ...}}'
    )
    import json

    response = _complete(prompt, system=SYSTEM_PROMPT)
    # Try to parse JSON from the response
    try:
        # Strip markdown code fences if present
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]
        return json.loads(cleaned)
    except (json.JSONDecodeError, IndexError):
        logger.warning(f"Failed to parse comparison JSON for topic '{topic}'")
        return {"raw_response": response}


def summarize_social_posts(candidate_name: str, posts: list[str]) -> str:
    """Summarize a candidate's recent Bluesky posts in Dutch."""
    posts_text = "\n\n".join(f"- {p}" for p in posts)
    prompt = (
        f"Hieronder staan recente berichten van {candidate_name} op Bluesky.\n\n"
        f"{posts_text}\n\n"
        f"Geef een samenvatting van 2-3 zinnen over de thema's en standpunten die "
        f"deze kandidaat op social media deelt. Schrijf in het Nederlands."
    )
    return _complete(prompt, system=SYSTEM_PROMPT)


def summarize_linkedin_posts(candidate_name: str, posts: list[str]) -> str:
    """Summarize a candidate's recent LinkedIn posts in Dutch."""
    posts_text = "\n\n".join(f"- {p}" for p in posts)
    prompt = (
        f"Hieronder staan recente berichten van {candidate_name} op LinkedIn.\n\n"
        f"{posts_text}\n\n"
        f"Geef een samenvatting van 2-3 zinnen over de thema's en standpunten die "
        f"deze kandidaat op LinkedIn deelt. Schrijf in het Nederlands."
    )
    return _complete(prompt, system=SYSTEM_PROMPT)


def summarize_linkedin_profile(candidate_name: str, profile_data: dict) -> str:
    """Summarize a candidate's LinkedIn profile in Dutch."""
    parts = []
    if profile_data.get("headline"):
        parts.append(f"Headline: {profile_data['headline']}")
    if profile_data.get("bio"):
        parts.append(f"Bio: {profile_data['bio']}")
    if profile_data.get("current_position"):
        parts.append(f"Huidige functie: {profile_data['current_position']}")
    if profile_data.get("current_company"):
        parts.append(f"Huidig bedrijf: {profile_data['current_company']}")
    if profile_data.get("experiences"):
        exp_texts = []
        for exp in profile_data["experiences"][:5]:
            exp_str = exp.get("title", "")
            if exp.get("company"):
                exp_str += f" bij {exp['company']}"
            if exp.get("description"):
                exp_str += f" — {exp['description'][:200]}"
            exp_texts.append(exp_str)
        parts.append("Werkervaring:\n" + "\n".join(f"- {e}" for e in exp_texts))
    if profile_data.get("skills"):
        skill_names = [s.get("name", "") for s in profile_data["skills"][:10] if s.get("name")]
        if skill_names:
            parts.append(f"Skills: {', '.join(skill_names)}")

    profile_text = "\n\n".join(parts)
    prompt = (
        f"Hieronder staat LinkedIn-profielinformatie van {candidate_name}, "
        f"kandidaat voor de gemeenteraadsverkiezingen Amsterdam 2026.\n\n"
        f"{profile_text}\n\n"
        f"Geef een beknopte samenvatting van 2-4 zinnen over de professionele "
        f"achtergrond en expertise van deze kandidaat. Schrijf in het Nederlands."
    )
    return _complete(prompt, system=SYSTEM_PROMPT)


def summarize_party_motions(party_name: str, motions_text: str) -> str:
    """Summarize a party's submitted motions and amendments in Dutch."""
    # Truncate to ~12k chars to stay within context limits
    text = motions_text[:12000]
    prompt = (
        f"Hieronder staat een overzicht van moties en amendementen ingediend door "
        f"{party_name} in de Amsterdamse gemeenteraad.\n\n"
        f"{text}\n\n"
        f"Geef een samenvatting van maximaal 200 woorden over de belangrijkste "
        f"thema's en prioriteiten die deze partij via moties en amendementen "
        f"naar voren brengt. Schrijf in het Nederlands."
    )
    return _complete(prompt, system=SYSTEM_PROMPT)


def answer_question(question: str, context_chunks: list[str]) -> str:
    """RAG: answer a question using retrieved document chunks."""
    context = "\n\n---\n\n".join(context_chunks)
    prompt = (
        f"Beantwoord de volgende vraag op basis van de onderstaande fragmenten "
        f"uit verkiezingsprogramma's van Amsterdamse partijen.\n\n"
        f"Vraag: {question}\n\n"
        f"Relevante fragmenten:\n{context}\n\n"
        f"Geef een helder en beknopt antwoord in het Nederlands. "
        f"Gebruik geen heading of titel — begin direct met de inhoud. "
        f"Gebruik gewone alinea's of een bulletlijst met streepjes (- item) als dat past. "
        f"Als de fragmenten onvoldoende informatie bevatten, geef dat dan aan."
    )
    return _complete(prompt, system=SYSTEM_PROMPT)
