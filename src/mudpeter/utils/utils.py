from datetime import date, datetime

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