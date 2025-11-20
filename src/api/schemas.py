from pydantic import BaseModel, Field

class RetrieveRequest(BaseModel):
    """Use pydantic to format query request (defualt application behavior)"""
    query: str = Field(..., min_length=1, max_length=500)
    max_results: int = Field(20, ge=1, le=100)
    year_min: int | None = Field(ge=1950, le=2100)
    parse_pdfs: bool = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "spider silk properties",
                "max_results": 50,
            }
        }
