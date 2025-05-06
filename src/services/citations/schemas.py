IDENTIFY_CITATION_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "full_span": {
                "type": "string",
                "description": "The full span of a single citation clause or sentence.",
            },
            "source_type": {
                "type": "string",
                "description": "The type of source cited by the single citation clause or sentence.",
                "enum": ["case", "statute", "regulation", "law_journal", "article", "rules", "id", "other"],
            },
        },
        "required": ["full_span", "source_type"],
    },
}

CITATION_GUIDANCE_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "guidance": {
                "type": "string",
                "description": "Text extracted from the citation manual that is potentially applicable to the citation.",
            },
            "explanation": {
                "type": "string",
                "description": "The reason why the text extracted from the citation manual is potentially applicable. For example, if the citation contains an error and the extracted text identifies the error or the way manner in which the error needs to be corrected, explain this in sufficient detail to enable someone to understand the error or make the correction.",
            },
        },
        "required": ["guidance", "explanation"],
    },
}

CITATION_CORRECTION_SCHEMA = {
    "type": "string",
    "description": "The corrected citation, using the provided guidance. Limit your changes to those indicated by the guidance. Do not make any other corrections. Return the full citation, as updated by your corrections."

}
