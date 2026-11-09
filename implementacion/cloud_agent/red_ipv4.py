"""
implementacion/cloud_agent/red_ipv4.py
======================================
Usa IPv4 para los hosts de IBM Cloud.

us-south.ml.cloud.ibm.com publica direcciones IPv6 antes que las IPv4. En una red sin
salida IPv6, cada conexión nueva espera ~21 s (timeout TCP de Windows) antes de probar
IPv4, y el cliente HTTP abre una conexión nueva tras 5 s de inactividad: casi cada
pregunta del chat tardaba 20 s y cargar el modelo, 45 s.

Afecta solo a *.cloud.ibm.com, dentro de este proceso. Si un host no tuviera IPv4,
se devuelven sus direcciones sin filtrar.
"""

from __future__ import annotations

import socket

SUFIJO_IBM = ".cloud.ibm.com"

_getaddrinfo_original = socket.getaddrinfo


def _getaddrinfo_ipv4(host, *args, **kwargs):
    direcciones = _getaddrinfo_original(host, *args, **kwargs)
    if isinstance(host, str) and host.lower().endswith(SUFIJO_IBM):
        return [d for d in direcciones if d[0] == socket.AF_INET] or direcciones
    return direcciones


def preferir_ipv4_en_ibm() -> None:
    """Instala el filtro. Llamarla más de una vez no tiene efecto adicional."""
    socket.getaddrinfo = _getaddrinfo_ipv4
