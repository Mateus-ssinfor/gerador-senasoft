from datetime import datetime
from num2words import num2words

_MESES = [
    "Janeiro","Fevereiro","Março","Abril","Maio","Junho",
    "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"
]

def data_pt_br(dt: datetime) -> str:
    return f"{dt.day} de {_MESES[dt.month-1]} de {dt.year}"

def moeda_pt_br(valor_str: str) -> tuple[str, str]:
    """
    Recebe '200' ou '200,50' ou '200.50' e retorna:
    ('R$ 200,00', 'duzentos')
    """
    s = valor_str.strip().replace("R$", "").strip()

    # Se veio "200,50" vira "200.50"
    if s.count(",") == 1 and s.count(".") == 0:
        s = s.replace(",", ".")
    # Se veio "1.234,56" remove milhar e troca decimal
    if s.count(".") >= 1 and s.count(",") == 1:
        s = s.replace(".", "").replace(",", ".")

    v = float(s)

    # R$ 1.234,56
    moeda = f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    inteiro = int(v)  # por extenso só do inteiro (200)
    ext = num2words(inteiro, lang="pt_BR") + " reais"

    return moeda, ext

from babel.numbers import format_decimal

def inteiro_formatado_pt_br(valor_str: str) -> int:
    s = valor_str.strip().replace("R$", "").strip()
    # 1.000 ou 1000
    s = s.replace(".", "")
    if s.isdigit():
        return int(s)
    # tenta float
    s = s.replace(",", ".")
    return int(float(s))

def numero_milhar_pt_br(n: int) -> str:
    # 1000 -> 1.000
    return format_decimal(n, locale="pt_BR")

def extenso_pt_br(n: int) -> str:
    return num2words(n, lang="pt_BR")

def moeda_formatada_pt_br(valor_str: str) -> tuple[str, str]:
    """
    Retorna:
    - "220,00"
    - "duzentos e vinte reais"
    """
    s = valor_str.strip().replace("R$", "").strip()

    if s.count(",") == 1 and s.count(".") == 0:
        s = s.replace(",", ".")
    if s.count(".") >= 1 and s.count(",") == 1:
        s = s.replace(".", "").replace(",", ".")

    v = float(s)
    moeda = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    inteiro = int(v)
    ext = num2words(inteiro, lang="pt_BR") + " reais"
    return moeda, ext

def data_curta_para_extenso(data_curta: str) -> str:
    """
    Entrada: '20/02/26' ou '20/02/2026'
    Saída:  '20 de Fevereiro de 2026'
    """
    s = data_curta.strip()
    partes = s.split("/")
    if len(partes) != 3:
        raise ValueError("Data inválida. Use dd/mm/aa.")

    dd = int(partes[0])
    mm = int(partes[1])
    aa = partes[2]

    if len(aa) == 2:
        # regra simples: 00-79 -> 2000-2079, 80-99 -> 1980-1999
        y = int(aa)
        ano = 2000 + y if y <= 79 else 1900 + y
    else:
        ano = int(aa)

    dt = datetime(ano, mm, dd)
    return data_pt_br(dt)