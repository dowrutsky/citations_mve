import logging
import json
import hashlib

from src.services.gemini.api import get_gemini_structured_response, GeminiRequest, GeminiCompletionResponse
from src.services.citations.prompts import IDENTIFY_CITATION_SYSTEM_PROMPT, CITATION_GUIDANCE_SYSTEM_PROMPT
from src.services.citations.schemas import IDENTIFY_CITATION_SCHEMA, CITATION_GUIDANCE_SCHEMA, CITATION_CORRECTION_SCHEMA


logger = logging.getLogger(__name__)


async def identify_citations_in_text(
        text: str,
        model: str = "gemini-2.0-flash",
) -> GeminiCompletionResponse:
    # TODO: enforce token limit on text; flash 2.0 will not reliably do this task on very large contexts
    job_id = f"identify: {hashlib.sha256(text.encode('utf-8')).hexdigest()}"

    request = GeminiRequest(
        schema=IDENTIFY_CITATION_SCHEMA,
        messages=[{"role": "user", "parts": [{"text": text}]}],
        gemini_model=model,
        system_prompt=IDENTIFY_CITATION_SYSTEM_PROMPT,
        log_context=job_id,
    )
    response = await get_gemini_structured_response(request)

    return response


async def get_case_citation_guidance(
        full_span: str,
        model: str = "gemini-2.5-flash-preview-04-17",
) -> GeminiCompletionResponse:
    # TODO: enforce token limit on text; flash 2.0 will not reliably do this task on very large contexts
    job_id = f"guidance: {hashlib.sha256(full_span.encode('utf-8')).hexdigest()}"

    request = GeminiRequest(
        schema=CITATION_GUIDANCE_SCHEMA,
        messages=[{"role": "user", "parts": [{"text": full_span}]}],
        gemini_model=model,
        system_prompt=CITATION_GUIDANCE_SYSTEM_PROMPT,
        log_context=job_id,
    )
    response = await get_gemini_structured_response(request)

    return response


async def correct_case_citation(
        full_span: str,
        guidance: list[dict],
        model: str = "gemini-2.5-flash-preview-04-17",
) -> GeminiCompletionResponse:
    job_id = f"correct: {hashlib.sha256(full_span.encode('utf-8')).hexdigest()}"

    prompt = f"""
    The task is to correct the citation provided to you by the user. 
    
    Use the guidance below (and only the guidance below) to correct the citation; do not make any changes other than those indicated by the guidance.
    
    Guidance: \n<guidance>{json.dumps(guidance, indent=4)}\n</guidance>
    """

    request = GeminiRequest(
        schema=CITATION_CORRECTION_SCHEMA,
        messages=[{"role": "user", "parts": [{"text": full_span}]}],
        gemini_model=model,
        system_prompt=prompt,
        log_context=job_id,
    )
    response = await get_gemini_structured_response(request)

    return response


async def test(text: str, golden_list: list[dict]) -> None:
    identify_citations_response = await identify_citations_in_text(text)
    actual_list: list[dict] = identify_citations_response.json_message
    try:
        assert sorted(actual_list, key=lambda el: el["full_span"]) == sorted(golden_list, key=lambda el: el["full_span"])
    except AssertionError:
        logger.error(f"Did not get expected citations from text!")
        logger.debug(
            f'Expected: \n{sorted(golden_list, key=lambda el: el["full_span"])}\n---\n'
            f'Actual:\n{sorted(actual_list, key=lambda el: el["full_span"])}')
    for citation in actual_list:
        if citation["source_type"] == "case":
            full_span = citation["full_span"]
            guidance = await get_case_citation_guidance(full_span)
            corrected = await correct_case_citation(full_span, guidance.json_message)
            logger.info(f"ori:\n{full_span}\n---\ncorrected:\n{corrected.json_message}")

    return


if __name__ == "__main__":
    import asyncio

    from src.services.citations.test_data import DATA

    msg_fmt = "%(asctime)s.%(msecs)03d %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(
        encoding="utf-8", level=logging.INFO, format=msg_fmt, datefmt=date_fmt,
        handlers=[logging.FileHandler("citations.log"), logging.StreamHandler()], force=True, )
    logger = logging.getLogger(__name__)

    TEXT, GOLDEN = DATA[0]
    asyncio.run(test(TEXT, json.loads(GOLDEN)))
