from pathlib import Path
from ai_video_production.errors import ProductError, ProductErrorCategory
from ai_video_production.schema_contracts import validate_instance

SCHEMA=Path(__file__).parents[1]/"schemas"/"error-envelope.schema.json"

def test_product_error_envelope_is_schema_valid():
    err=ProductError("ERR_SECURITY_PATH_DENIED","denied",ProductErrorCategory.SECURITY,False,details={"logical_uri":"asset://x"})
    validate_instance(err.to_envelope(),SCHEMA)
