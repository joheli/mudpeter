from datetime import date, datetime
from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError
from pathlib import Path

def parse_date_or_datetime(value: str) -> date | datetime | None:
    """ 
    This function takes a string and converts it into `date` or `datetime`
    if it is of format `%Y-%m-%d` or `%Y-%m-%d %H:%M:%S`, respectively.
    """
    if not isinstance(value, str):
        return None

    value = value.strip()

    try:
        if len(value) == 10:
            return datetime.strptime(value, "%Y-%m-%d").date()
        if len(value) == 19:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

    return None

def is_probably_jinja_template(path: Path) -> bool:
    """ 
    This function checks whether a given file is probably a jinja template
    """
    if not path.is_file():
        return False

    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False

    if not any(marker in text for marker in ("{{", "{%", "{#")):
        return False

    env = Environment()

    try:
        env.parse(text)
    except TemplateSyntaxError:
        return False

    return True

def create_variants_from_template(template_file: Path, keywords: set[str]) -> dict[str, Path] | None:
    """ 
    This function takes a (possible) template file containing {{ keyword }} and creates
    variants of the template according to the set of keywords.
    
    It returns a dictionary with keywords as keys and the paths to the new file variants.
    """
    if not is_probably_jinja_template(template_file):
        return
    env = Environment(loader=FileSystemLoader(template_file.parent.absolute()))
    template = env.get_template(template_file.name)
    
    result = {}
    
    for keyword_v in keywords:
        rendered = template.render(keyword=keyword_v)
        variant_file = template_file.parent / f"{template_file.stem}_{keyword_v.lower().replace(" ", "_")}{template_file.suffix}"
        variant_file.write_text(rendered, encoding="utf-8")
        result[keyword_v] = variant_file
    
    return result
        
    