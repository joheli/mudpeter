from pathlib import Path
from typing import Annotated
import tomllib  
from pydantic import BaseModel, Field, model_validator


class PubMedConfig(BaseModel):
    term: Annotated[str, Field(description="PubMed search term/query")] # setting no default means: this field is mandatory
    email: Annotated[str, Field(description="Email for NCBI Entrez usage")]
    keyword: Annotated[str, Field(default="ungrouped", description="Database field allowing grouping/categorization of returned articles")]
    retmax: Annotated[int, Field(default=100, ge=1, le=100000)]
    batch_size: Annotated[int, Field(default=50, ge=1, le=1000)]


class DatabaseConfig(BaseModel):
    sqlite_path: Annotated[str | None, Field(default=None, description="Path to SQLite file")]
    echo: bool = False

class FullTextConfig(BaseModel):
    enabled: bool = True
    prefer_pmc: bool = True
    use_pdf: bool = True
    max_chars: Annotated[int | None, Field(default=500_000, ge=1)] # i guess default should rather be None...
    

class AppConfig(BaseModel):
    pubmed: PubMedConfig
    database: DatabaseConfig
    fulltext: FullTextConfig = FullTextConfig()

    @classmethod
    def from_toml(cls, path: str | Path) -> "AppConfig":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(str(p))
        data = tomllib.loads(p.read_text(encoding="utf-8"))
        return cls.model_validate(data)
