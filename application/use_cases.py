import random
import uuid
from core.entities import RespuestaFactura

class FacturacionUseCases:
    @staticmethod
    def validar_factura(xml_factura: str) -> RespuestaFactura:
        if xml_factura and "<Factura" in xml_factura:
            return RespuestaFactura(
                estado="VALIDADA",
                mensaje="Factura validada correctamente",
                clave_acceso=None
            )
        else:
            return RespuestaFactura(
                estado="ERROR",
                mensaje="XML de factura inválido",
                clave_acceso=None
            )

    @staticmethod
    def generar_factura_xml(id_compra: str) -> RespuestaFactura:
        if not id_compra:
            return RespuestaFactura(
                estado="ERROR",
                mensaje="El ID de compra es requerido",
                clave_acceso=None
            )
            
        clave_simulada = f"FAC-2026-{random.randint(1000, 9999)}"
        return RespuestaFactura(
            estado="VALIDADA",
            mensaje="Factura generada correctamente",
            clave_acceso=clave_simulada
        )

    @staticmethod
    def consultar_comprobante(id_compra: str) -> RespuestaFactura:
        if not id_compra:
            return RespuestaFactura(
                estado="ERROR",
                mensaje="El ID de compra es requerido",
                clave_acceso=None
            )
            
        clave_simulada = f"FAC-2026-{random.randint(1000, 9999)}"
        return RespuestaFactura(
            estado="AUTORIZADA",
            mensaje="Comprobante consultado exitosamente",
            clave_acceso=clave_simulada
        )
