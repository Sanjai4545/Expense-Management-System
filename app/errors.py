from typing import Optional, Dict, Any


class ApiError(Exception):
    """Uniform API Error exception."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        fields: Optional[Dict[str, str]] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.fields = fields

    def to_dict(self) -> Dict[str, Any]:
        err: Dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.fields is not None:
            err["fields"] = self.fields
        return {"error": err}
