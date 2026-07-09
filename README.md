# mudpeter

mudpeter is a small command-line tool for building a local collection of PubMed articles. Given a PubMed search query, it downloads publication metadata, tries to enrich each record with available full text, and stores the results in a local SQLite database. Full texts can also be exported as plain `.txt` files for downstream reading, searching, or text-mining workflows.

The name is deliberately modest: mudpeter does not try to be a complete literature-review platform. It is a practical helper for researchers, clinicians, students, and data analysts who want to turn a PubMed query into a local, inspectable dataset.

## What mudpeter does

At a high level, mudpeter can:

- search PubMed with the same kind of query string you would type into the PubMed website;
- download basic article metadata such as PMID, PMCID, DOI, title, abstract, journal, authors, and publication date;
- optionally look for full text in PubMed Central through the NCBI BioC API;
- optionally fall back to open-access PDFs discovered through Unpaywall and extract text from those PDFs;
- save everything into a SQLite database;
- update existing database rows when the same PMID is seen again;
- export saved full texts as ordinary text files, grouped by keyword.

## Prerequisites

You need:

- Python 3.13 or newer;
- [`uv`](https://docs.astral.sh/uv/) version 0.11.0 or newer;
- an email address to use with the NCBI Entrez and Unpaywall APIs.

The email address is required because the external services mudpeter talks to ask API users to identify themselves. It does not need to be a special API key.

## Installation

Install the current development version directly from this repository:

```bash
uv pip install git+https://github.com/joheli/mudpeter.git
```

After installation, check that the command is available:

```bash
mudpeter --help
```

## Quick start

Create a small TOML configuration file, for example `mudpeter.toml`, containing a PubMed search term, your email address, a path for the SQLite database, and whether full-text retrieval should be enabled. Then run `mudpeter run --config mudpeter.toml`. mudpeter will search PubMed, fetch matching article records in batches, try to attach full text where possible, create or update the SQLite database, and print a short summary when it is done.

A minimal configuration looks like this:

```toml
[pubmed]
term = "Granulicatella adiacens case reports[pt] AND free full text[Filter]"
email = "your.name@example.com"
keyword = "granulicatella"
retmax = 25
batch_size = 10

[database]
sqlite_path = "mudpeter.db"
echo = false

[fulltext]
enabled = true
prefer_pmc = true
use_pdf = true
max_chars = 500000
```

Run it:

```bash
mudpeter run --config mudpeter.toml
```

Export saved full texts later:

```bash
mudpeter export --config mudpeter.toml --export_directory exported_texts
```

To export only records belonging to one keyword group:

```bash
mudpeter export --config mudpeter.toml --export_directory exported_texts --keyword granulicatella
```

## Configuration explained

mudpeter is driven by a TOML config file. TOML is a simple text format made of sections such as `[pubmed]` and key-value pairs such as `retmax = 25`.

### `[pubmed]`

`term` is the PubMed query. This can be a simple phrase such as `endocarditis` or a more specific PubMed query using field tags and filters.

`email` is passed to NCBI Entrez and Unpaywall so those services know who is making requests.

`keyword` is a local label stored with every publication retrieved during the run. It is useful when you use the same database for several searches. For example, you might run one query with `keyword = "endocarditis"` and another with `keyword = "case_reports"`, then export only one group later.

`retmax` is the maximum number of PubMed records mudpeter should retrieve for this run.

`batch_size` controls how many records are fetched from PubMed at a time. Smaller batches can be easier on remote services; larger batches may finish faster.

### `[database]`

`sqlite_path` is the path to the local SQLite database file. SQLite is a file-based database, so this can be as simple as `"mudpeter.db"`.

`echo` controls SQL logging from SQLModel/SQLAlchemy. Most users should leave this as `false`. Set it to `true` only when debugging database behavior.

### `[fulltext]`

`enabled` controls whether mudpeter tries to retrieve full text after downloading metadata. If this is `false`, mudpeter only stores bibliographic metadata and abstracts.

`prefer_pmc` tells mudpeter to try PubMed Central first when a PMCID is available. This usually gives cleaner structured text than PDF extraction.

`use_pdf` tells mudpeter to try the PDF route when PMC/BioC full text is not available. The PDF route uses the article DOI, asks Unpaywall for an open-access PDF URL, downloads the PDF, and extracts text from it.

`max_chars` limits the amount of full text stored per article. This can help keep the database smaller. Use `null` if you do not want to truncate full texts.

## Commands

### `mudpeter run`

```bash
mudpeter run --config mudpeter.toml
```

Runs the full pipeline:

1. read and validate the TOML configuration;
2. connect to the configured SQLite database;
3. create database tables if needed;
4. search PubMed;
5. fetch article metadata;
6. optionally enrich records with full text;
7. insert new records or update existing records by PMID.

Useful options:

```bash
mudpeter run --config mudpeter.toml --dry-run
```

`--dry-run` performs the PubMed/full-text work but does not write to the database. This is useful when testing a query.

```bash
mudpeter run --config mudpeter.toml --no-init-db
```

`--no-init-db` skips automatic table creation.

### `mudpeter validate-config`

```bash
mudpeter validate-config mudpeter.toml
```

Reads a config file and prints the parsed configuration. Use this when you want to check that your TOML file is valid before running a download.

### `mudpeter export`

```bash
mudpeter export --config mudpeter.toml --export_directory exported_texts
```

Exports full texts from the SQLite database to `.txt` files. mudpeter creates one subdirectory per keyword and writes one file per PMID:

```text
exported_texts/
└── granulicatella/
    ├── 12345678.txt
    └── 23456789.txt
```

Use `--keyword` to export only one keyword group.

## How mudpeter works

This section explains the pipeline in more detail for readers who are new to PubMed, APIs, or local databases.

### 1. PubMed search

A run starts with the search term from `[pubmed].term`. mudpeter sends that term to PubMed through Biopython's Entrez interface. PubMed returns three important pieces of information:

- the total number of matching records;
- a `WebEnv` value;
- a `QueryKey` value.

`WebEnv` and `QueryKey` are PubMed history-server values. Instead of downloading every search result immediately, mudpeter asks PubMed to keep the search result set available temporarily and then uses these values to fetch records from that result set in batches.

### 2. Batched metadata retrieval

After the initial search, mudpeter fetches records in batches. Each batch is requested as PubMed XML and converted into ordinary Python data. For each article, mudpeter tries to extract:

- PMID, the PubMed identifier;
- PMCID, the PubMed Central identifier, when available;
- DOI, the digital object identifier, when available;
- title;
- abstract;
- author names;
- journal title;
- publication date.

The batch size is controlled by `batch_size`, and the overall maximum number of records is controlled by `retmax`.

### 3. Publication objects

Each PubMed record is converted into a `Publication` object. This object is both the in-memory representation of an article and the database model used by SQLModel.

The PMID is the primary key. That means mudpeter treats one PMID as one unique publication row. If a later run sees the same PMID again, mudpeter updates the existing row instead of blindly inserting a duplicate.

The optional `keyword` from the config is attached to each publication. This gives you a simple way to group records by search topic inside one database.

### 4. Full-text enrichment

If `[fulltext].enabled` is true, mudpeter tries to add full text to each publication.

The preferred route is PubMed Central through the NCBI BioC API. This route requires a PMCID. The BioC response contains article passages with section information. mudpeter groups those passages into sections such as title, abstract, introduction, methods, results, discussion, conclusion, references, and any other sections it finds. It then turns the structured sections into plain text.

If no PMC/BioC full text is found and `use_pdf` is true, mudpeter tries a second route. It uses the article DOI to query Unpaywall. If Unpaywall reports an open-access PDF URL, mudpeter downloads the PDF and extracts text with PyMuPDF.

Full-text retrieval is best-effort. Some articles have no PMCID, no DOI, no open PDF, a PDF that blocks downloading, or a PDF whose text cannot be extracted cleanly. In those cases, mudpeter still keeps the metadata record and simply leaves `full_text` empty.

### 5. SQLite persistence

mudpeter stores records in a local SQLite database. SQLite is useful here because it is just a file: easy to copy, inspect, back up, or query with other tools.

The main table is `publications`. It stores identifiers, bibliographic metadata, the local keyword, the PDF URL when found, the extracted full text when available, and bookkeeping timestamps.

> [!TIP]
> I use [Datasette](https://datasette.io/) to explore the contents of sqlite databases.
> After installing with `pip install datasette` view the database with `datasette serve mydatabase.db`
> on `http://localhost:8001`.

When writing records, mudpeter performs an upsert by PMID:

- if the PMID is not already present, it inserts a new row;
- if the PMID already exists, it updates missing or newer fields on the existing row;
- if new full text is found, it replaces the stored full text for that PMID.

This makes it safe to re-run the same query as your configuration evolves.

### 6. Exporting text files

The database is the main storage layer, but many text-analysis tools prefer plain files. The `export` command reads rows with non-empty full text and writes them to a directory. Files are grouped by keyword, and each filename is the PMID plus `.txt`.

For example, a record with `keyword = "granulicatella"` and `pmid = "12345678"` becomes:

```text
exported_texts/granulicatella/12345678.txt
```

This layout is intended to be simple and script-friendly.

## Notes and limitations

mudpeter can only retrieve full text that is available through supported open routes. A PubMed record existing does not mean that full text is freely available.

PDF extraction can be imperfect. PDFs are designed for visual layout, not always for clean machine-readable text. PMC/BioC text is usually preferable when available.

Be considerate with external APIs. Use reasonable `retmax` and `batch_size` values, include your real email address, and avoid repeated large runs unless necessary.

## Help

For an overview of available commands and options, run:

```bash
mudpeter --help
```

For command-specific help, run for example:

```bash
mudpeter run --help
mudpeter export --help
```

## ToDos

I am working on the following additions - so do hang on to your hats:

### High priority

- [x] ~~Add option to export a csv file to be batch-processed by [oneshot](https://github.com/joheli/oneshot) - this would facilitate automated analysis by LLMs~~ _Done (Version 0.0.6)! See `mudpeter export --help`_.
- [x] ~~Allow keyword-specific instructions and questions for _oneshot_~~ _Done (Version 0.0.7)_
- [ ] Check ordering of full-text output from BioC API
- [ ] Add logging by loguru

### Medium priority

- [ ] Limit calls to Pubmed and BioC API 
- [ ] Add option to manually add pdfs that can be extracted and added to the full-texts
- [ ] Allow documents to be parsed by [docling-serve](https://github.com/docling-project/docling-serve) in addition to [pymupdf](https://github.com/pymupdf/pymupdf)
