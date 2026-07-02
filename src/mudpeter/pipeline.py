from typing import Iterable

from mudpeter.pubmed.articles import search_pubmed, fetch_article_infos
from mudpeter.models import Publication, publication_from_pubmed_dict
from mudpeter.fulltext.retrieve import try_fulltext_from_pmc, try_fulltext_from_unpaywall_pdf


def fetch_publications_from_pubmed(*, term: str, email: str, retmax: int, batch_size: int) -> list[Publication]:
    """ 
    `fetch_publications_from_pubmed` is a wrapper for `fetch_article_infos`.
    It adds argument `batch_size` which allows the retrieval to take place in batches.
    """
    webenv, query_key, count = search_pubmed(term, email, retmax=retmax)
    pubs: list[Publication] = []
    retstart = 0
    limit = min(count, retmax)

    while retstart < limit:
        batch = fetch_article_infos(
            webenv,
            query_key,
            email,
            retmax=min(batch_size, limit - retstart),
            retstart=retstart,
        )
        for d in batch:
            # Check if Publication is returned at all - this is not the case if pmid is None! See `publication_from_pubmed`
            d_pub = publication_from_pubmed_dict(d)
            if d_pub:
                pubs.append(d_pub)
        retstart += batch_size

    return pubs


def enrich_publications_with_fulltext(
    publications: Iterable[Publication],
    *,
    email_for_unpaywall: str,
    enabled: bool = True, # why would this be needed? from config?
    prefer_pmc: bool = True,
    use_pdf: bool = True,
    max_chars: int | None = None,
) -> list[Publication]:
    """ 
    `enrich_publications_with_fulltext` takes the list of `Publication` from `fetch_publications_from_pubmed`
    and enriches them with fulltext from either bioc API or pdf.
    
    If successful, fields `fulltext` and `pdf_url` of the `Publication` objects are updated.
    """
    if not enabled:
        return list(publications)

    out: list[Publication] = []
    for pub in publications:
        fulltext = None
        pdf_url = None

        if prefer_pmc:
            res = try_fulltext_from_pmc(pub.pmcid, max_chars=max_chars)
            if res.full_text:
                fulltext = res.full_text

        if (not fulltext) and use_pdf:
            res = try_fulltext_from_unpaywall_pdf(pub.doi, email=email_for_unpaywall, max_chars=max_chars)
            if res.pdf_url:
                pdf_url = res.pdf_url
            if res.full_text:
                fulltext = res.full_text

        pub.full_text = fulltext
        pub.pdf_url = pdf_url
        out.append(pub)

    return out
