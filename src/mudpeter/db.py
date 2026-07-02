from contextlib import contextmanager
from datetime import datetime, UTC
from typing import Iterable
from sqlmodel import SQLModel, Session, create_engine, select
from pathlib import Path

from mudpeter.models import Publication


def make_sqlite_url(sqlite_path: str) -> str:
    """ 
    `make_sqlite_url` takes a string and returns a "database_url" for sqlite.
    The database_url is then used to get an engine, see below.
    """
    if not sqlite_path:
        raise ValueError("sqlite_path must be a non-empty path")
    # basic checks
    # is sqlite_path pointing to a dir?
    path = Path(sqlite_path)
    if path.exists() and not path.is_file():
        raise ValueError(f"sqlite_path must not be a directory: {sqlite_path}")
    # does parent directory exist?
    if not path.parent.exists():
        raise ValueError(f"parent directory does not exist: {path.parent}")
    # return the path
    return f"sqlite:///{sqlite_path}"


def get_engine(database_url: str, *, echo: bool = False):
    """ 
    `get_engine` creates an instance of a sqlmodel engine - it needs a `database_url`
    Theoretically it could create engines for backends other than sqlite - although for this project other backends are not planned.
    """
    if not database_url:
        raise ValueError("database_url must be provided")
    # the following is just an adjustment for sqlite - as theoretically, sqlmodel could access other backends (e.g. Postgres) in the future
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite:///") else None
    return create_engine(database_url, echo=echo, connect_args=connect_args)


def init_db(engine) -> None:
    """ 
    Create all tables stored in the metadata
    """
    SQLModel.metadata.create_all(engine)


@contextmanager
def session_scope(engine):
    """ 
    This pattern allows the build-up and tear-down of sessions to be standardized
    """
    session = Session(engine)
    try:
        yield session
        # everything after yield is executed for after leaving a "with" clause, see below
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        # in all cases, exception or no, the session is finally closed
        session.close()


def upsert_publications(engine, publications: Iterable[Publication]) -> int:
    """
    Insert or update publications by pmid. Returns number of rows processed.
    """
    processed = 0
    with session_scope(engine) as session:      # see above for session scope
        for pub in publications:
            if not getattr(pub, "pmid", None):
                continue # continue means: jump to next iteration, skipping the lines below
            
            # try to retrieve a record with the same pmid
            existing = session.exec(select(Publication).where(Publication.pmid == pub.pmid)).first()
            if existing:
                existing.pmcid = pub.pmcid or existing.pmcid # resorts to existing.pmcid if pub.pmcid is "falsy", i.e. None, "", 0, False, empty [] etc.
                existing.doi = pub.doi or existing.doi
                existing.title = pub.title or existing.title
                existing.abstract = pub.abstract or existing.abstract
                existing.journal = pub.journal or existing.journal
                existing.publication_date = pub.publication_date or existing.publication_date
                existing.authors = pub.authors or existing.authors
                existing.pdf_url = pub.pdf_url or existing.pdf_url
                if pub.full_text:
                    existing.full_text = pub.full_text
                existing.updated_at = datetime.now(tz=UTC)
                session.add(existing)
            else:
                session.add(pub)
            processed += 1
    return processed

# not sure if this def is needed:
def get_publication_by_pmid(engine, pmid: str) -> None | Publication: # DELETE mark for possible deletion
    with session_scope(engine) as session:
        return session.exec(select(Publication).where(Publication.pmid == pmid)).first()
