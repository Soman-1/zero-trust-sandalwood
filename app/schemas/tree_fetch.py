from pydantic import BaseModel

class TreeFetchResponse(BaseModel):
    """Response from external fetch operation.

    Attributes:
        total_fetched: Total records retrieved from external APIs.
        registered: Number of new trees successfully registered.
        duplicates: Number of records ignored due to duplication.
    """
    total_fetched: int
    registered: int
    duplicates: int
