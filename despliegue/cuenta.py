"""El token personal del dueño y las cuentas en que nunca se publica (las de trabajo del CIP).

Los scripts de publicación solo leen el token de ``HF_TOKEN`` y se lo pasan explícito a ``huggingface_hub``: nunca usan
un token guardado en el disco (``~/.cache/huggingface/token``), que en la máquina del dueño es de una cuenta de trabajo.
"""

from __future__ import annotations

import os

CUENTAS_PROHIBIDAS = frozenset({"cip-itlicenses"})
PREFIJOS_PROHIBIDOS = ("cipotato",)
URL_TOKENS = "https://huggingface.co/settings/tokens"


class ErrorCuenta(RuntimeError):
    """El token no sirve para publicar: falta, es de otra cuenta, es de solo lectura o es de una cuenta de trabajo."""


def prohibida(nombre: str | None) -> bool:
    nombre = (nombre or "").strip().lower()
    return nombre in CUENTAS_PROHIBIDAS or nombre.startswith(PREFIJOS_PROHIBIDOS)


def token_personal(entorno=None) -> str:
    """El token de ``HF_TOKEN``. Sin él, un error que dice cómo crearlo (no se busca otro en el disco)."""
    token = ((os.environ if entorno is None else entorno).get("HF_TOKEN") or "").strip()
    if not token:
        raise ErrorCuenta(
            "Falta HF_TOKEN. Crea un token de tu cuenta PERSONAL con permiso de escritura en "
            f"{URL_TOKENS} y expórtalo: export HF_TOKEN=hf_... (no se usa el token guardado en el disco).")
    return token


def revisar_destino(usuario: str) -> None:
    """Sin red: el espacio de nombres donde se publicará no puede ser una cuenta de trabajo."""
    if prohibida(usuario):
        raise ErrorCuenta(f"«{usuario}» es una cuenta u organización de trabajo del CIP: aquí no se publica. "
                          "Usa tu cuenta personal de Hugging Face.")


def verificar_cuenta(info: dict, usuario: str) -> str:
    """Revisa la respuesta de ``whoami`` contra el destino. Devuelve el nombre de la cuenta del token."""
    revisar_destino(usuario)
    nombre = info.get("name") or ""
    organizaciones = [o.get("name") or "" for o in info.get("orgs") or []]
    if prohibida(nombre) or any(prohibida(o) for o in organizaciones):
        raise ErrorCuenta(
            f"El token de HF_TOKEN es de la cuenta «{nombre}», de trabajo o miembro de una organización del CIP "
            f"({', '.join(o for o in organizaciones if prohibida(o)) or nombre}). Usa un token de tu cuenta personal.")
    if usuario != nombre and usuario not in organizaciones:
        raise ErrorCuenta(f"El token de HF_TOKEN es de «{nombre}», no de «{usuario}». Pasa tu usuario de Hugging Face "
                          "o exporta el token de esa cuenta.")
    rol = ((info.get("auth") or {}).get("accessToken") or {}).get("role")
    if rol == "read":
        raise ErrorCuenta(f"El token de HF_TOKEN es de solo lectura. Crea uno con permiso de escritura en {URL_TOKENS}.")
    return nombre
