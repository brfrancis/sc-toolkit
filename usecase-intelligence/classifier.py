"""
Use case classifier
Calls a fine-tuned OpenAI model to map a customer workflow description
to a canonical use case from the taxonomy.

Architecture:
  1. Primary call  — fine-tuned model classifies the description
  2. Challenger    — GPT-4o validates / challenges the classification
  3. Retry logic   — if primary and challenger disagree beyond threshold,
                     escalate with additional context
"""

import os
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

FINETUNED_MODEL = os.environ.get("FINETUNED_MODEL_ID", "")  # set in PythonAnywhere env vars


def classify(use_case_name: str, description: str) -> dict:
    """
    Classify a customer workflow description against the use case taxonomy.

    Returns:
        {
            "primary":    str,   # fine-tuned model classification
            "challenger": str,   # GPT-4o challenger classification
            "agreed":     bool,  # whether primary and challenger agree
            "final":      str,   # resolved classification
            "confidence": float  # agreement signal (1.0 = full agreement)
        }
    """
    prompt = (
        f"Given the information below, could you classify which use case this is?\n"
        f" Use Case Name: {use_case_name}\n"
        f" Customer's Process: {description}\n"
        f" Please just give the use case name from the list of use cases provided to you."
    )

    # Primary — fine-tuned model
    primary_response = client.chat.completions.create(
        model=FINETUNED_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    primary = primary_response.choices[0].message.content.strip()

    # Challenger — GPT-4o
    # TODO: implement challenger call with taxonomy context
    # TODO: implement retry / escalation logic on disagreement

    return {
        "primary":    primary,
        "challenger": None,   # populated when challenger is implemented
        "agreed":     None,
        "final":      primary,
        "confidence": None,
    }
