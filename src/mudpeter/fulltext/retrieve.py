from dataclasses import dataclass

from ..pubmed.bioc import bioc_fulltext, restructure
from ..unpaywall.retrieve import get_unpaywall_doi
from ..pdf.extract import extract_text_from_pdf_url


@dataclass
class FullTextResult:
    full_text: str | None = None
    source: str | None = None  # "pmc" | "pdf" | None
    pdf_url: str | None = None
    error: str | None = None


def _sections_to_plain_text(sections: dict[str]) -> str:
    """ 
    This helper function converts the bioc-restructured output into text.
    
    It specifically accomodates the output of bioc.restructure (which restructures content from bioc_fulltext)
    """
    preferred = [
        "TITLE", "title",
        "ABSTRACT", "abstract",
        "INTRO", "introduction",
        "METHODS", "methods",
        "RESULTS", "results",
        "DISCUSS", "discussion",
        "CONCL", "conclusion",
        "REFERENCES", "references",
        "unspecified",
    ]
    out: list[str] = []     # list to contain the full text
    used: set[str] = set()  # set to contain the section keys used and intersecting with list `preferred`

    # the following attempts to order the text sections according to `preferred`
    # first loop through preferred
    for k in preferred:
        # if sections contains a corresponding key AND the contents are not empty ...
        if k in sections and str(sections[k]).strip():
            # ... then append the section to list `out` but prepend the name of the section
            out.append(f"{k}\n{str(sections[k]).strip()}")
            # also, add the key to set `used`
            used.add(k)
            
    # Iterate through all sections to catch those that do *not* appear in `used`!
    # e.g. sections like "FUNDING" or "CASE REPORT", etc!
    for k, v in sections.items():
        # Check if key is already present in set `used` - if yes, skip the remainder of the loop, i.e. jump to the next iteration (`continue`)!
        if k in used:
            continue
        # Similarly, if text (`v`) is None or empty, jump to the next iteration (`continue`)!
        if not v or not str(v).strip():
            continue
        # Here only sections remain that have keys differing from `preferred`, i.e. not present in set `used`:
        # Append the content of these sections to list `out` but prepend the name of the section (as above)
        out.append(f"{k}\n{str(v).strip()}")
        
    # finally, lump everything up in one giant str to return
    return "\n\n".join(out).strip()


def try_fulltext_from_pmc(pmcid: str | None, *, max_chars: int | None = None) -> FullTextResult:
    """ 
    `try_fulltext_from_pmc` uses module pubmed.bioc to get the passages from the BioC API,
    restructure them and use above function `_sections_to_plain_text` to generate one big happy 
    str.
    This str is then packaged into a FullTextResult object.
    """
    if not pmcid:
        return FullTextResult(error="no pmcid")

    try:
        passages = bioc_fulltext(pmcid)
        sections = restructure(passages)
        text = _sections_to_plain_text(sections)
        if max_chars is not None:
            text = text[:max_chars]
        if not text.strip():
            return FullTextResult(error="pmc returned empty text")
        return FullTextResult(full_text=text, source="pmc")
    except Exception as e:
        return FullTextResult(error=f"pmc error: {e}")
    
    
def try_fulltext_from_unpaywall_pdf(doi: str | None, *, email: str, max_chars: int | None = None) -> FullTextResult:
    """ 
    Alternatively, the full text is extracted from a pdf over a url provided by unpaywall.
    Chances are slim but we have to try, don't we?
    
    Function `extract_text_from_pdf_url` from pdf.extract is used to get the text from a url referring to a pdf.
    """
    if not doi:
        return FullTextResult(error="no doi")

    try:
        rec = get_unpaywall_doi(doi, email=email)
        best = rec.get("best_oa_location") or {}
        pdf_url = best.get("url_for_pdf")
        if not pdf_url:
            return FullTextResult(error="no pdf url in unpaywall")

        text = extract_text_from_pdf_url(pdf_url, max_chars=max_chars)
        if not text.strip():
            return FullTextResult(pdf_url=pdf_url, error="pdf extracted empty text")
        return FullTextResult(full_text=text, source="pdf", pdf_url=pdf_url)
    except Exception as e:
        return FullTextResult(error=f"pdf/unpaywall error: {e}")
    
# TODO: Here a function is missing that processes a pdf file or - even better - a directory with pdfs, no?
# Maybe the pdfs should contain the pubmed_id in their file nams - what do you think?
