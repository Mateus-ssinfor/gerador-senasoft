import os
import re

def _safe_name(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r'[\\/*?:"<>|]', "", name)  # tira caracteres inválidos
    return name

def proposal_pdf_path(storage_dir: str, cliente: str, created_at, proposal_id: int) -> str:
    cliente = _safe_name(cliente)
    return os.path.join(storage_dir, f"PROPOSTA - {cliente}.pdf")