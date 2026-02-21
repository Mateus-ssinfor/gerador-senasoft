import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm

from utils import data_pt_br

import os
LIBREOFFICE_PATH = os.getenv("LIBREOFFICE_PATH", r"C:\Program Files\LibreOffice\program\soffice.exe")


def _convert_docx_to_pdf(docx_path: str, out_dir: str) -> str:
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    cmd = [
        LIBREOFFICE_PATH,
        "--headless",
        "--convert-to", "pdf",
        "--outdir", out_dir,
        docx_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "Falha ao converter para PDF.\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}\n"
        )

    pdf_name = Path(docx_path).with_suffix(".pdf").name
    pdf_path = str(Path(out_dir) / pdf_name)

    if not os.path.exists(pdf_path):
        raise RuntimeError("PDF não foi encontrado após conversão.")

    return pdf_path


def gerar_promissoria_pdf(
    template_docx_path: str,
    output_pdf_path: str,
    dados: dict,
    imagem_rg_path: str,
) -> None:
    """
    Preenche template_promissoria.docx e gera PDF final.
    Variáveis do template:
      {{ DATA }}          -> vencimento (por extenso)
      {{ NOME }}
      {{ CPF }}
      {{ ENDERECO }}
      {{ DATA_SISTEMA }}  -> hoje (por extenso)
      {{ IMAGEM_RG }}     -> imagem do documento
    """
    tpl = DocxTemplate(template_docx_path)

    context = {
        "DATA": dados["DATA"],  # já vem por extenso
        "NOME": dados["NOME"],
        "CPF": dados["CPF"],
        "ENDERECO": dados["ENDERECO"],
        "DATA_SISTEMA": data_pt_br(datetime.now()),
        "IMAGEM_RG": InlineImage(tpl, imagem_rg_path, width=Mm(185)),  # ajuste aqui se quiser maior/menor
    }

    tpl.render(context)

    with tempfile.TemporaryDirectory() as tmp:
        docx_out = str(Path(tmp) / "promissoria_preenchida.docx")
        tpl.save(docx_out)

        pdf_tmp = _convert_docx_to_pdf(docx_out, tmp)

        Path(output_pdf_path).parent.mkdir(parents=True, exist_ok=True)
        with open(pdf_tmp, "rb") as src, open(output_pdf_path, "wb") as dst:
            dst.write(src.read())