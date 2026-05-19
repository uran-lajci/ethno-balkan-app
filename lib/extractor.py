"""PDF genus extraction via OpenAI Responses API."""

import base64
import os

from openai import OpenAI

EXTRACTION_PROMPT = (
    "List every unique genus that appears in a table row of this paper. A genus is the first word of a Latin "
    "binomial (italicized scientific name) in the leftmost data column of any species/taxa table. Ignore "
    "mentions in running text, figure captions, references, and abstracts. Output one genus per line, "
    "alphabetically. Flag any spelling that looks like a typo (e.g., 'Faseolus' likely means 'Phaseolus')."
)

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")


def extract_genera_from_pdf(pdf_bytes: bytes, filename: str = "paper.pdf") -> dict:
    """
    Run the extraction prompt against a PDF.

    Returns:
        {
            "raw_output": str,         # full LLM text
            "lines": list[str],        # one entry per non-empty output line
            "input_tokens": int,
            "output_tokens": int,
            "cost_usd": float,
        }
    """
    client = OpenAI()
    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

    input_list = [{
        "role": "user",
        "content": [
            {"type": "input_text", "text": EXTRACTION_PROMPT},
            {"type": "input_file",
             "filename": filename,
             "file_data": f"data:application/pdf;base64,{pdf_b64}"},
        ],
    }]

    response = client.responses.create(
        model=MODEL,
        input=input_list,
        reasoning={"effort": "medium"},
    )

    raw = response.output_text or ""
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = (input_tokens * 5 + output_tokens * 30) / 1_000_000

    return {
        "raw_output": raw,
        "lines": lines,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
    }