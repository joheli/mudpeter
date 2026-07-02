import calendar
from Bio import Entrez

def search_pubmed(term, email, retmax=100) -> tuple[str, str, int]:
    """
    `search_pubmed` is the starting point of every query. 
    It sends a query to pubmed and returns webenv, query_key, and count of records
    
    webenv and query_key are needed for article information, see below `fetch_article_infos`
    """
    Entrez.email = email
    with Entrez.esearch(
        db="pubmed",
        term=term,
        usehistory="y",
        retmax=retmax
    ) as handle:
        record = Entrez.read(handle)
    webenv = record["WebEnv"]
    query_key = record["QueryKey"]
    count = int(record["Count"])
    print(f"Found {count} results. Using WebEnv/query_key for cached fetching.")
    return webenv, query_key, count

def get_pmcid_from_article(pubmeddata):
    """
    Helper function:
    Attempt to get PMCID from PubmedData/ArticleIdList if present
    """
    try:
        for aid in pubmeddata.get("ArticleIdList", []):
            if (("IdType" in aid and aid["IdType"] == "pmc") or
                (isinstance(aid, dict) and aid.get("IdType") == "pmc")):
                return aid if isinstance(aid, str) else aid.get("#text", None)
            # Sometimes ArticleIdList is a list of str, sometimes dicts
            elif isinstance(aid, str) and aid.lower().startswith("pmc"):
                return aid
    except Exception:
        pass
    return None

def get_pmcid_via_elink(pmid, email):
    """
    Helper function - Fallback: 
    Retrieve PMCID using Entrez.elink
    """
    Entrez.email = email
    try:
        with Entrez.elink(dbfrom="pubmed", db="pmc", linkname="pubmed_pmc", id=pmid) as link_handle:
            link_record = Entrez.read(link_handle)
            dbs = link_record[0].get("LinkSetDb")
            if dbs and len(dbs) > 0 and 'Link' in dbs[0] and dbs[0]['Link']:
                return "PMC" + dbs[0]["Link"][0]["Id"]
    except Exception:
        pass
    return None

def normalize_date(year, month, day) -> str:
    """
    Helper function:
    Create a presentable string representing the date of publication
    """
    if not year:
        return None
    if not month:
        month_num = 1
    else:
        try:
            month_num = int(month)
        except ValueError:
            month_str = month[:3].title()
            if month_str in calendar.month_abbr:
                month_num = list(calendar.month_abbr).index(month_str)
            else:
                month_num = 1
    if not day:
        day = "1"
    return f"{year}-{month_num:02d}-{int(day):02d}"

def fetch_article_infos(webenv: str, query_key: str, email: str, retmax:int = 10, retstart:int = 0) -> list[dict[str, str]]:
    """ 
    `fetch_article_infos` gets all relevant article information from pubmed.
    It follows up a search initiated in `search_pubmed` (above).
    
    The function requires webenv and query_key supplied by `search_pubmed` (see above). 
    It also requires email, retmax, and reststart.
    
    The resulting list[dict[str, str]] can be converted to a `Publication` dataclass - see models.py for that.
    """
    Entrez.email = email
    with Entrez.efetch(
        db="pubmed",
        rettype="xml",
        retmode="xml",
        retmax=retmax,
        retstart=retstart,
        webenv=webenv,
        query_key=query_key,
    ) as handle:
        records = Entrez.read(handle)
    results = []
    for rec in records["PubmedArticle"]:
        # extract the article
        article = rec["MedlineCitation"]
        
        # extract article info
        art_info = article["Article"]
        
        # extract pubmed id (PMID)
        pmid_val = article["PMID"]

        # extract title
        title = art_info.get('ArticleTitle', 'N/A')

        # Abstract
        abstract_field = art_info.get('Abstract', {}).get('AbstractText', [])
        if isinstance(abstract_field, list):
            abstract = " ".join(str(x) for x in abstract_field)
        else:
            abstract = str(abstract_field)

        # extract authors and put into list
        authors = []
        for author in art_info.get('AuthorList', []):
            parts = []
            if 'ForeName' in author:
                parts.append(author['ForeName'])
            if 'LastName' in author:
                parts.append(author['LastName'])
            author_str = ' '.join(parts)
            if author_str:
                authors.append(author_str)

        # extract publication date using helper function `normalize_date`
        pub_date = None
        if 'ArticleDate' in art_info and len(art_info['ArticleDate']) > 0:
            d = art_info['ArticleDate'][0]
            pub_date = normalize_date(d.get('Year', ''), d.get('Month', ''), d.get('Day', ''))
        elif 'Journal' in art_info and 'JournalIssue' in art_info['Journal'] and 'PubDate' in art_info['Journal']['JournalIssue']:
            pd = art_info['Journal']['JournalIssue']['PubDate']
            pub_date = normalize_date(pd.get('Year', ''), pd.get('Month', ''), pd.get('Day', ''))

        # extract PubmedData for further processing downstream
        pubmeddata = rec.get("PubmedData", {})
        
        # Try to extract PMCID from PubmedData or alternatively via elink
        pmcid = get_pmcid_from_article(pubmeddata)
        if pmcid is None:
            pmcid = get_pmcid_via_elink(pmid_val, email)

        # Try to extract DOI from PubmedData
        doi = None
        article_ids = pubmeddata.get("ArticleIdList", [])
        for aid in article_ids:
            if aid.attributes.get("IdType") == "doi":
                doi = str(aid)
                break

        # extranct Journal name
        journal = art_info.get('Journal', {}).get('Title')
        
        # put results into a dict, which is appended to result
        results.append({
            'PMID': str(pmid_val),
            'PMCID': str(pmcid),
            'DOI': doi,
            'Title': str(title),
            'Abstract': abstract,
            'Authors': authors,
            'Journal': journal,
            'PublicationDate': pub_date
        })
        
    # results is a list of dict[str, str]
    return results

# for testing only
def main():
    email = "joheli@gmx.net"
    search_term = "Granulicatella adiacens case reports[pt] AND free full text[Filter]"
    webenv, query_key, count = search_pubmed(search_term, email, retmax=100)
    print(f"\n\nThe search retrieved {count} records.\n\n")
    article_infos = fetch_article_infos(webenv, query_key, email, retmax=10, retstart=0)
    i = 1
    for info in article_infos:
        print(f"\n\nRecord {i}:\n {info}")
        i += 1

# for testing only   
if __name__=="__main__":
    main()