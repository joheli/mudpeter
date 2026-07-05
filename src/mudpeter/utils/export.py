from pathlib import Path
from mudpeter.db import extract_keywords_and_fulltexts

def export_fulltexts(root_directory: str | Path, engine, keyword: str|None = None):
    """ 
    Extracts fulltexts from database and writes them out into a root directory
    given by argument `directory`
    """
    root = Path(root_directory)
    root.mkdir(parents=True, exist_ok=True)
    
    fulltexts = extract_keywords_and_fulltexts(engine, keyword=keyword)
    
    for kwrd, pmid, fulltext in fulltexts:
        target_dir = root / kwrd
        target_dir.mkdir(parents=True, exist_ok=True)   # create directory per keyword
        target_file = target_dir / f"{pmid}.txt"
        target_file.write_text(fulltext, encoding="utf-8")

        
    
    
    