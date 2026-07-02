from datetime import datetime, UTC
from typing import Annotated
from sqlmodel import SQLModel, Field, Column
from sqlalchemy.types import JSON, Text

class Publication(SQLModel, table=True):
    """
    Database representation of a publication record.

    Notes:
        - `pmid` is the primary key
        - authors are stored as JSON list of strings.
        - full_text can be large; stored as TEXT.
    """
    __tablename__ = "publications"

    # identifiers
    pmid: Annotated[str, Field(primary_key=True)] # primary key!
    pmcid: Annotated[str | None, Field(default=None, index=True)]
    doi: Annotated[str | None, Field(default=None, index=True)]

    # bibliographic metadata
    title: Annotated[str | None, Field(default=None)]
    abstract: Annotated[str | None, Field(default=None)]
    journal: Annotated[str | None, Field(default=None)]
    publication_date: Annotated[str | None, Field(default=None, description="ISO date YYYY-MM-DD when available")]

    authors: Annotated[list[str], Field(default_factory=list, sa_column=Column(JSON))]

    # enrichment
    pdf_url: Annotated[str | None, Field(default=None)]
    full_text: Annotated[str | None, Field(default=None, sa_column=Column(Text))]

    # bookkeeping
    created_at: Annotated[datetime, Field(default_factory=lambda: datetime.now(tz = UTC))]
    updated_at: Annotated[datetime, Field(default_factory=lambda: datetime.now(tz = UTC), sa_column_kwargs={"onupdate": lambda: datetime.now(tz=UTC)})]

def publication_from_pubmed_dict(d: dict[str, str]) -> Publication | None:
    """
    Map a dict produced by mudpeter.pubmed.articles.fetch_article_infos into a Publication model.
    If pubmed id ("PMID") should be None or empty (falsy), None is returned.
    """
    pmcid_raw = d.get("PMCID")
    pmcid = None
    if pmcid_raw not in (None, "None"):
        pmcid = str(pmcid_raw).strip() or None
        
    if not d.get("PMID"):
        return 

    return Publication(
        pmid=str(d.get("PMID")).strip(), 
        pmcid=pmcid,
        doi=(str(d.get("DOI")).strip() if d.get("DOI") else None),
        title=(str(d.get("Title")).strip() if d.get("Title") else None),
        abstract=(str(d.get("Abstract")).strip() if d.get("Abstract") else None),
        journal=(str(d.get("Journal")).strip() if d.get("Journal") else None),
        publication_date=(str(d.get("PublicationDate")).strip() if d.get("PublicationDate") else None),
        authors=list(d.get("Authors") or []),
    )
