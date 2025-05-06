from src.lib.constants import PROJECT_ROOT


with open(PROJECT_ROOT / "IndigoBook_escaped.md", "r") as f:
    INDIGO_BOOK = f.read()


IDENTIFY_CITATION_SYSTEM_PROMPT = (
    """
    The task is to extract each and every citation clause/sentence verbatim. Output these citation clauses and sentences in the given JSON structure. 
    
    Definitions: 
        - A citation refers to the core components identifying a legal authority—typically including the case name, reporter information, court, year, and possibly explanatory parentheticals, weight of authority parentheticals (concurring, dissenting, etc.), or procedural information (reversed, affirmed, cert granted, and their abbreviations). 
        - A citation clause or citation sentence, by contrast, is the full grammatical unit in which that citation appears. It includes any introductory signal ('e.g.', 'see', 'see, e.g.', 'see, also', 'cf.', 'compare ... with', 'contra', 'but see', 'but cf.', 'see generally'), connecting punctuation, and additional language—such as explanations of the citation’s relevance—that together form a complete clause or sentence. In short, the citation is the bibliographic reference; the citation clause/sentence is the complete syntactic structure that incorporates it.
        - A citation clause or citation sentence is usually embedded in text in one of the following patterns and in all cases, you must extract only a single citation clause or citation sentence itself (note how semicolons separate citation clauses that are otherwise part of one sentence; they must be extracted separately): 
            - $proposition. $citation_clause_or_citation_sentence. 
            - $proposition, $citation_clause_or_citation_sentence, $additional_content. 
            - $proposition. $citation_clause_or_citation_sentence1; $citation_clause_or_citation_sentence2; $citation_clause_or_citation_sentence3. 
        - Multiple citation clauses or citation sentences may all relate to the same sentence, proposition, or clause being cited. Regardless, treat each such citation clause or citation sentence as distinct and extract them one at a time, respecting boundaries marked by commas, semicolons, periods, etc. 
        - A citation sentence or citation clause may consist entirely of the term "Id" (perhaps with asterisks or a period); you must extract this special citation sentence/clause when used as such. 

    Guidance:
        - Extract verbatim the full span corresponding to each individual citation clause or citation sentence, not just the citation itself. 
        - Include in the extraction any markdown characters (e.g., asterisks), html tags (e.g., <i>), or other indicia of formatting for the relevant citation clause or sentence. 
        - Include in the extraction all parentheticals for the citation; there may be several. 
        - Include in the extraction the punctuation that terminates the citation clause or sentence (e.g., a period, comma, semicolon, etc.).
        - Exclude from the extraction any content that belongs to the sentence, proposition, or clause being cited, but do not separate procedural information even if includes a citation to a distinct procedural stage. 
        - Be tolerant of typos and minor errors. For example, treat "see e.g." as an introductory signal, even though it should technically be written as "see, e.g.". 
        - It is critical that you extract each and every citation clause or citation sentence, even if duplicative or another citation clause or citation sentence; your extraction be complete.

    Edge cases to handle:
        - Case name split from other citation components: In *Fenton v. Quaboag Country Club*, the court held that the house owners were entitled to an abatement of the trespasses by flying golf balls. 233 N.E.2d 216, 219 (Mass. 1968). -> *Fenton v. Quaboag Country Club*, 233 N.E.2d 216, 219 (Mass. 1968).
        - Short form citation: We have previously declined this relief, *Malletier*, 500 F. Supp. 2d at 281, and must do so again here. -> *Malletier*, 500 F. Supp. 2d at 281,
        - Procedural information is part of a single integrated citation: The Supreme Court has previously declined to resolve this split in opinions. *Energy & Env't Legal Inst. v. Epel*, 43 F. Supp. 3d 1171 (D. Colo. 2014), *aff'd*, 793 F.3d 1169 (10th Cir.), *cert. denied*, 136 S. Ct. 595 (2015). -> *Energy & Env't Legal Inst. v. Epel*, 43 F. Supp. 3d 1171 (D. Colo. 2014), *aff'd*, 793 F.3d 1169 (10th Cir.), *cert. denied*, 136 S. Ct. 595 (2015).
        - The "compare ... with" signal includes at least two citations: Compare I.R.C. § 312 (2014) with I.R.C. § 318 (2014). -> ["Compare I.R.C. § 312 (2014)", "with I.R.C. § 318 (2014)."]

    Examples of errors to avoid:
        - Including the sentence to be cited in addition to the citation sentence or citation clause: "The distinction between actual and red flag knowledge is objective. *Viacom Int'l, Inc. v. YouTube, Inc.*, 676 F.3d 19, 31 (2d Cir. 2012)."
        - Omitting leading markdown characters when present: See*, *Dep't of Revenue v. James B. Beam Distilling Co.*, 377 U.S. 341, 349 (1964) (7–2 decision) (Black, J., dissenting) (disagreeing with Justice Goldberg as to the relative merits of bourbon and scotch). 
        - Including markdown characters when not present: *but see *People v. Foranyic*, 74 Cal. Rptr. 2d 804, 807 (Ct. App. 1998) (police have probable cause to detain someone they see riding a bike at 3 a.m., carrying an axe); 
        - Omitting terminating punctuation when present: *C.f.* I.R.C. § 312 (2014) 
        - Including terminating punctuation when not present: Pl.'s Compl. ¶ 12, ECF No. 147 
        - Omitting parentheticals, procedural information, or signals when present: *Dep't of Revenue v. James B. Beam Distilling Co.*, 377 U.S. 341, 349 (1964) 
        - Including parentheticals, procedural information, or signals when not present or when part of a distinct citation
    """
)

CITATION_GUIDANCE_SYSTEM_PROMPT = (
    f"""
    The task is to identify guidance for whatever citation the user provides to you. 
    
    Use the contents of the citation manual below to identify relevant guidance and provide an explanation of why that guidance is relevant.
    
    <citation_manual>
    {INDIGO_BOOK}
    </citation_manual>
    
    Be fulsome in your search and provide all potentially relevant guidance; your output will be the sole information 
    available 
    to downstream tasks that will attempt to correct any errors in the citation, so you must include everything that downstream processes could even potentially find useful in correcting the citation (or leaving parts of it unchanged because those parts are already correct).
     
    Respond in the given JSON structure.
    """
)