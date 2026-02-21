import os
import re
from datetime import datetime
from pathlib import Path

def safe_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[^\w\s\-\.]", "", name, flags=re.UNICODE)
    name = re.sub(r"\s+", " ", name)
    return name[:120] if name else "cliente"

def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)

def proposal_pdf_path(storage_dir: str, client_name: str, created_at: datetime, proposal_id: int) -> str:
    ensure_dir(storage_dir)
    base = safe_filename(client_name)
    stamp = created_at.strftime("%Y%m%d")
    filename = f"PROPOSTA - {base} - {stamp} - #{proposal_id}.pdf"
    return os.path.join(storage_dir, filename)