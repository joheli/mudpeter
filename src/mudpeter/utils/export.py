from pathlib import Path
from datetime import date, datetime
from mudpeter.db import extract_keywords_and_fulltexts
import pandas as pd

def export_fulltexts(root_directory: str | Path, 
                     engine, *, 
                     keyword: str | None = None,
                     beforedate: date | datetime | None =  None,
                     afterdate: date | datetime | None = None) -> list[tuple[str, Path]]:
    """ 
    Extracts fulltexts from database and writes them out into a root directory
    given by argument `directory`
    """
    root = Path(root_directory)
    root.mkdir(parents=True, exist_ok=True)
    
    fulltexts = extract_keywords_and_fulltexts(engine, keyword=keyword, afterdate=afterdate, beforedate=beforedate)
    
    result = []
    
    for kwrd, pmid, fulltext in fulltexts:
        target_dir = root / kwrd
        target_dir.mkdir(parents=True, exist_ok=True)   # create directory per keyword
        target_file = target_dir / f"{pmid}.txt"
        target_file.write_text(fulltext, encoding="utf-8")
        result.append((pmid, target_file))
    
    return result

def create_oneshot_csv(root_directory: str | Path,
                       contexts: list[tuple[str, Path]], 
                       question: Path,
                       instructions: Path,
                       sep: str = ";") -> None:
    root = Path(root_directory)
    
    pfx = "[>]" # path prefix used by oneshot
    
    oneshot_data = []
    
    for x in contexts:
        oneshot_data.append((x[0], f"{pfx}{instructions.as_posix()}", f"{pfx}{x[1].as_posix()}", f"{pfx}{question.as_posix()}"))
    
    oneshot_dataframe = pd.DataFrame(oneshot_data, columns = ["qid", "instructions", "contexts", "questions"])
    
    export_file = root / "oneshot.csv"
    
    oneshot_dataframe.to_csv(export_file, index=False, sep=sep)

        
    
    
    