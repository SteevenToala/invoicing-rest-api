from dataclasses import dataclass
from typing import Optional

@dataclass
class RespuestaFactura:
    estado: str
    mensaje: str
    clave_acceso: Optional[str] = None
