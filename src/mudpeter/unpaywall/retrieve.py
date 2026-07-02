import requests

class UnpaywallError(Exception):
    pass

def get_unpaywall_doi(doi: str, email: str) -> dict:
    """
    Look up a DOI in the Unpaywall API and return the JSON record as a dict.
    Raises UnpaywallError on HTTP or API-level errors.
    """
    if not doi:
        raise ValueError("DOI must be a non-empty string")
    if not email:
        raise ValueError("email is required by the Unpaywall API")

    base_url = "https://api.unpaywall.org/v2"
    url = f"{base_url}/{doi}"
    params = {"email": email}

    r = requests.get(url, params=params, timeout=10)

    if r.status_code == 404:
        # DOI not in Unpaywall
        raise UnpaywallError(f"DOI not found in Unpaywall: {doi}")
    if not r.ok:
        raise UnpaywallError(
            f"Unpaywall request failed ({r.status_code}): {r.text}"
        )

    try:
        data = r.json()
    except ValueError as e:
        raise UnpaywallError(f"Invalid JSON from Unpaywall: {e}") from e

    # optional sanity check: Unpaywall echoes the DOI in the response
    if "doi" in data and data["doi"].lower() != doi.lower():
        raise UnpaywallError(
            f"Response DOI mismatch: requested {doi}, got {data.get('doi')}"
        )

    return data

# just for testing
def main():
    doi1 = "10.7759/cureus.61622"
    doi2 = "10.1016/j.jaccas.2024.102525"
    doi3 = "10.1155/crdi/5407160"
    email = "joheli@gmx.net"
    record = get_unpaywall_doi(doi = doi1, email = email)
    best_oa_location = record.get("best_oa_location")
    pdf_url = best_oa_location.get("url_for_pdf", None)
    if pdf_url:
        print(f"The pdf url is: {pdf_url}")
    else:
        print("Sorry.")
    
if __name__=="__main__":
    main()
