"""Development diagnostics contain schema names and error codes, never values."""
import logging
import os

def safe_errors(error, fields):
    allowed=set(fields)
    result=[]
    for item in error.errors(include_input=False,include_context=False,include_url=False):
        loc=["body"]+[str(part) if part in allowed else "unknown_field" for part in item["loc"] if isinstance(part,str)]
        result.append({"loc":loc,"type":item["type"],"msg":item["msg"]})
    return result

def log_validation(scope,error,fields):
    if os.getenv("XEA_DEBUG_VALIDATION")=="1":
        entries=safe_errors(error,fields)
        logging.getLogger("app.validation").warning("Validation rejected: schema=%s fields=%s codes=%s",
            scope,[e["loc"] for e in entries],[e["type"] for e in entries])
