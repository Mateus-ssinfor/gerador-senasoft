import os
from datetime import datetime, timedelta
from models import db, Proposal

def cleanup_expired(retention_days: int) -> int:
    now = datetime.utcnow()
    cutoff = now - timedelta(days=retention_days)

    expired = Proposal.query.filter(Proposal.created_at < cutoff).all()
    removed = 0

    for p in expired:
        if p.pdf_path and os.path.exists(p.pdf_path):
            try:
                os.remove(p.pdf_path)
            except Exception:
                pass

        db.session.delete(p)
        removed += 1

    if removed:
        db.session.commit()

    return removed

import time
from pathlib import Path

def cleanup_tmp_contracts(tmp_dir: str, max_age_hours: int = 24) -> int:
    """
    Apaga PDFs de contrato temporários mais antigos que max_age_hours.
    Retorna quantos apagou.
    """
    p = Path(tmp_dir)
    if not p.exists():
        return 0

    now = time.time()
    cutoff = now - (max_age_hours * 3600)

    removed = 0
    for f in p.glob("*.pdf"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        except Exception:
            pass

    return removed