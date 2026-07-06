from pathlib import Path
from datetime import date, datetime
from mudpeter.db import extract_keywords_and_fulltexts
from mudpeter.utils.utils import create_variants_from_template
import pandas as pd

def export_fulltexts(root_directory: str | Path, 
                     engine, *, 
                     keyword: str | None = None,
                     beforedate: date | datetime | None =  None,
                     afterdate: date | datetime | None = None) -> list[tuple[str, str, Path]]:
    """ 
    Extracts fulltexts from database and writes them out into a root directory
    given by argument `directory`.
    
    It returns a list of tuples with entries for pmid, keyword, and full-text path.
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
        result.append((pmid, kwrd, target_file))
    
    return result

def create_oneshot_csv(root_directory: str | Path,
                       contexts: list[tuple[str, str, Path]], 
                       question: Path,
                       instructions: Path,
                       sep: str = ";",
                       keyword_specific: bool = False) -> None:
    """ 
    This function creates a csv file that can be consumed by library `oneshot`.
    It places the csv file into `root_directory`.
    
    Arguments `question` and `instructions` refer to text files containing 
    corresponding information for LLMs.
    
    If `keyword_specific` is `True` files referred to by `question` and `instructions` 
    are treated as `jinja2` templates containing placeholder `{{ keyword }}`. 
    
    Variations of the files are then created.
    """
    root = Path(root_directory)
    
    pfx = "[>]" # path prefix used by oneshot
    
    keyword_set = {k for _, k, _ in contexts}
    
    question_per_keyword = {kw:question for kw in keyword_set} # per default all question files are identical
    instructions_per_keyword = {kw:instructions for kw in keyword_set} # per default all instruction files are identical
    
    # if specified, keyword specific variants of question and instructions are created:
    if keyword_specific:
        # check question
        kw_specific_files = create_variants_from_template(question, keyword_set)
        if kw_specific_files:
            question_per_keyword = kw_specific_files
        # check instructions
        kw_specific_files = create_variants_from_template(instructions, keyword_set)
        if kw_specific_files:
            instructions_per_keyword = kw_specific_files
    
    oneshot_data = []
    
    for x in contexts:
        pmid, keyword, context_path = x
        oneshot_data.append((
            pmid, 
            f"{pfx}{instructions_per_keyword[keyword].as_posix()}", 
            f"{pfx}{context_path.as_posix()}", 
            f"{pfx}{question_per_keyword[keyword].as_posix()}"
            ))
    
    oneshot_dataframe = pd.DataFrame(oneshot_data, columns = ["qid", "instructions", "contexts", "questions"])
    
    export_file = root / "oneshot.csv"
    
    oneshot_dataframe.to_csv(export_file, index=False, sep=sep)

        
    
    
    