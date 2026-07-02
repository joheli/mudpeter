import requests

class BioCError(Exception):
    pass

def bioc_fulltext(pmcid: str) -> dict:
    """
    Retrieves full text from BioC API

    Args:
        pmcid (str): Pubmed Central ID

    Returns:
        dict: the full text in json
    """
    if not pmcid:
        raise ValueError("pmcid must be present!")
    
    url = f"https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/{pmcid}/unicode"
    
    r = requests.get(url, timeout=10)
    
    if r.status_code == 404:
        # pmcid not in bioc api
        raise BioCError(f"Pubmed Central ID not found in BioC API: {pmcid}")
    if not r.ok:
        raise BioCError(
            f"BioC API request failed ({r.status_code}): {r.text}"
        )

    try:
        data = r.json()
        passages = data[0]['documents'][0]['passages']
    except ValueError as e:
        raise BioCError(f"Invalid JSON from BioC API: {e}") from e
    
    return passages

def restructure(psgs: dict) -> dict[str]:
    """
    restructures passages

    Args:
        psgs (dict): raw passages delivered by bioc

    Returns:
        dict: a simplified, restructured container for full text data
    """
    # empty container
    sections = {}
    p_rst = {}
    
    try:
        # iterate through all passages
        for p in psgs:
            # extract section type
            section = p['infons']['section_type'] or p['type'] or "unspecified"
            # extract text
            text = p['text'] or ""
            # extract offset
            offset = p['offset']
            # populate sections
            # .setdefault - pattern to append something to to a list (default empty list is created if key `section` not present) without checking if key exists
            sections.setdefault(section, []).append((offset, text))
    except ValueError as e:
        raise BioCError(f"Invalid JSON from BioC API: {e}") from e # this pattern chains BioCError to ValueError
            
    # sort sections
    for section, chunks in sections.items():
        # sort by offset
        chunks.sort(key = lambda x: x[0]) # as first item x[0] of the tuple (offset, text) returns the offset
        p_rst[section] = "\n".join(t for _, t in chunks if t.strip()) # ignore offset, was only used to sort the tuples, just take text
    
    # return a dictionary containing sections as keys
    return p_rst

# just for testing
def main():
    pmcid = "PMC11442336"
    pmcid2 = "PMC12073844"
    psgs = bioc_fulltext(pmcid=pmcid)
    p_r = restructure(psgs = psgs)
    print(p_r)
    #ft[0]['documents'][0]['passages']
    #ft[0]['documents'][0]['passages'][0]['infons']['section_type']
    #ft[0]['documents'][0]['passages'][0]['text']
    #psgs[2]['offset']
    
if __name__=="__main__":
    main()