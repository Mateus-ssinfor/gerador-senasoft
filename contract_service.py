import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from docxtpl import DocxTemplate

from utils import data_pt_br, inteiro_formatado_pt_br, numero_milhar_pt_br, extenso_pt_br, moeda_formatada_pt_br

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

def gerar_contrato_pdf(template_docx_path: str, output_pdf_path: str, dados: dict) -> None:
    tpl = DocxTemplate(template_docx_path)

    # Franquia (número + extenso)
    franquia_int = inteiro_formatado_pt_br(dados["FRANQUIA"])
    franquia_fmt = numero_milhar_pt_br(franquia_int)
    franquia_ext = extenso_pt_br(franquia_int)

    # Valor mensal (formatado + extenso)
    valor_fmt, valor_ext = moeda_formatada_pt_br(dados["VALOR_MENSAL"])

    context = {
        "DENOMINACAO": dados["DENOMINACAO"],
        "CPF_CNPJ": dados["CPF_CNPJ"],
        "ENDERECO": dados["ENDERECO"],
        "TELEFONE": dados["TELEFONE"],
        "EMAIL": dados["EMAIL"],
        "EQUIPAMENTO": dados["EQUIPAMENTO"],
        "ACESSORIOS": dados["ACESSORIOS"],
        "DATA_INICIO": dados["DATA_INICIO"],
        "DATA_TERMINO": dados["DATA_TERMINO"],
        "FRANQUIA_FORMATADA": franquia_fmt,
        "FRANQUIA_EXTENSO": franquia_ext,
        "VALOR_MENSAL_FORMATADO": valor_fmt,
        "VALOR_MENSAL_EXTENSO": valor_ext,
        "DATA_ASSINATURA": data_pt_br(datetime.now()),
    }

    tpl.render(context)

    with tempfile.TemporaryDirectory() as tmp:
        docx_out = str(Path(tmp) / "contrato_preenchido.docx")
        tpl.save(docx_out)

        pdf_tmp = _convert_docx_to_pdf(docx_out, tmp)

        Path(output_pdf_path).parent.mkdir(parents=True, exist_ok=True)
        with open(pdf_tmp, "rb") as src, open(output_pdf_path, "wb") as dst:
            dst.write(src.read())