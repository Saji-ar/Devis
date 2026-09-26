"""Generation et lecture des devis Excel, FIDELE au template (logo, styles, pied de page).

IMPORTANT : on n'utilise PAS openpyxl pour ECRIRE le fichier final, car openpyxl supprime
le logo (image ancree) et le tableau stylise. On fait de la "chirurgie XML" sur une copie
du template : on clone la ligne du tableau des produits, on decale les lignes suivantes, et
on laisse tout le reste (logo, styles, formules de total, pied de page) intact.

openpyxl sert uniquement a la LECTURE (scan d'un .xlsx cree/modifie a la main).
"""
import math
import os
import re
import shutil
import zipfile
from datetime import date, datetime
from pathlib import Path
from xml.sax.saxutils import escape

import openpyxl

from .config import settings
from .schemas import DevisData, LigneDevis

# --- Constantes liees a la structure du template ---
HEADER_ROW = 17
BODY_ROW = 18          # 1ere (et unique) ligne de corps du tableau dans le template
ROW_FORMULA = "Tableau1[[#This Row],[Prix Unit HT]]*Tableau1[[#This Row],[Quantité]]"
# Estimation de hauteur de ligne pour le texte multiligne (colonne Produit large).
_CHARS_PER_LINE = 55
_LINE_PT = 16
_PAD_PT = 8


# ============================ ECRITURE ============================


def _est_height(text: str) -> float:
    lines = 0
    for seg in (text or "").split("\n"):
        lines += max(1, math.ceil(len(seg) / _CHARS_PER_LINE))
    return max(16.0, lines * _LINE_PT + _PAD_PT)


def _num(v) -> str:
    """Formate un nombre pour le XML (entier sans .0)."""
    if v is None:
        return "0"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _ensure_border_styles(styles_xml: str) -> tuple[str, dict]:
    """Ajoute des cellXfs avec bordure (boite complete, borderId=1) pour le tableau.

    Rend le quadrillage INDEPENDANT du 'style de tableau' Excel : certaines versions de
    LibreOffice (ex. sur Raspberry Pi) ne dessinent pas les bordures issues du style de
    tableau. On applique donc des bordures explicites sur l'en-tete et le corps.
    """
    base = int(re.search(r'<cellXfs count="(\d+)">', styles_xml).group(1))
    xfs = [
        # A (produit) : texte, retour a la ligne, bordure
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" '
        'applyAlignment="1"><alignment wrapText="1"/></xf>',
        # nombre / general avec bordure (sert pour B et l'en-tete)
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1"/>',
        # D (TVA) : format pourcentage 164, bordure
        '<xf numFmtId="164" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1"/>',
        # C et E : euro (numFmt 44), bordure
        '<xf numFmtId="44" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1"/>',
    ]
    styles_xml = styles_xml.replace(f'<cellXfs count="{base}">',
                                    f'<cellXfs count="{base + len(xfs)}">', 1)
    styles_xml = styles_xml.replace('</cellXfs>', ''.join(xfs) + '</cellXfs>', 1)
    return styles_xml, {
        "A": base, "B": base + 1, "header": base + 1, "D": base + 2, "C": base + 3, "E": base + 3,
    }


def _body_row_xml(r: int, ligne: LigneDevis, st: dict) -> str:
    h = _est_height(ligne.produit)
    produit = escape(ligne.produit or "")
    tva_frac = (ligne.tva_pct or 0) / 100.0
    return (
        f'<row r="{r}" spans="1:5" ht="{h:.0f}" customHeight="1" x14ac:dyDescent="0.2">'
        f'<c r="A{r}" s="{st["A"]}" t="inlineStr"><is><t xml:space="preserve">{produit}</t></is></c>'
        f'<c r="B{r}" s="{st["B"]}"><v>{_num(ligne.quantite)}</v></c>'
        f'<c r="C{r}" s="{st["C"]}"><v>{_num(ligne.prix_unit_ht)}</v></c>'
        f'<c r="D{r}" s="{st["D"]}"><v>{tva_frac}</v></c>'
        f'<c r="E{r}" s="{st["E"]}"><f>{ROW_FORMULA}</f></c>'
        f'</row>'
    )


def _shift_row(row_xml: str, delta: int) -> str:
    row_xml = re.sub(r'(<row [^>]*\br=")(\d+)(")',
                     lambda m: m.group(1) + str(int(m.group(2)) + delta) + m.group(3), row_xml)
    row_xml = re.sub(r'(r="[A-E])(\d+)(")',
                     lambda m: m.group(1) + str(int(m.group(2)) + delta) + m.group(3), row_xml)
    return row_xml


def _build_sheet(xml: str, lignes: list[LigneDevis], st: dict) -> str:
    n = max(len(lignes), 1)
    delta = n - 1
    sd = re.search(r'<sheetData>(.*)</sheetData>', xml, re.S)
    rows = re.findall(r'<row\b[^>]*?(?:/>|>.*?</row>)', sd.group(1), re.S)

    out = []
    for rx in rows:
        rn = int(re.search(r'<row [^>]*\br="(\d+)"', rx).group(1))
        if rn == HEADER_ROW:
            # Bordures explicites sur l'en-tete du tableau (A17:E17).
            rx = re.sub(r'<c r="([A-E]17)"(?![^>]*\bs=)', rf'<c r="\1" s="{st["header"]}"', rx)
            out.append(rx)
        elif rn < BODY_ROW:
            out.append(rx)
        elif rn == BODY_ROW:
            for i in range(n):
                ligne = lignes[i] if i < len(lignes) else LigneDevis()
                out.append(_body_row_xml(BODY_ROW + i, ligne, st))
        else:
            out.append(_shift_row(rx, delta) if delta else rx)

    xml = xml[:sd.start()] + "<sheetData>" + "".join(out) + "</sheetData>" + xml[sd.end():]
    xml = re.sub(r'<dimension ref="[^"]*"/>', f'<dimension ref="A2:E{26 + delta}"/>', xml)
    # Force le recalcul en retirant les valeurs en cache des cellules a formule.
    xml = re.sub(r'(<c\b[^>]*?)\s+t="(?:e|str)"([^>]*>\s*<f)', r'\1\2', xml)
    xml = re.sub(r'(</f>)<v>.*?</v>', r'\1', xml)
    return xml


def _set_cell_text(xml: str, coord: str, text: str, style: str = None, keep_style: bool = False) -> str:
    """Ecrit une chaine dans une cellule (au-dessus du tableau).

    keep_style=True : conserve le style deja present sur la cellule du template (pour
    respecter le format defini par l'utilisateur), sinon applique `style`.
    """
    if keep_style:
        m = re.search(rf'<c r="{coord}"[^>]*?\bs="(\d+)"', xml)
        if m:
            style = m.group(1)
    s_attr = f' s="{style}"' if style is not None else ''
    cell = (f'<c r="{coord}"{s_attr} t="inlineStr"><is>'
            f'<t xml:space="preserve">{escape(text)}</t></is></c>' if text
            else f'<c r="{coord}"{s_attr}/>')
    if re.search(rf'<c r="{coord}"[^>]*/>', xml):
        return re.sub(rf'<c r="{coord}"[^>]*/>', cell, xml, count=1)
    if re.search(rf'<c r="{coord}"', xml):
        return re.sub(rf'<c r="{coord}".*?</c>', cell, xml, count=1, flags=re.S)
    row = int(coord[1:])
    if re.search(rf'<row r="{row}"[^>]*>', xml):
        return re.sub(rf'(<row r="{row}"[^>]*>)', rf'\1{cell}', xml, count=1)
    # Ligne absente : on l'insere a sa position (avant la 1ere ligne de numero superieur),
    # pour garder l'ordre croissant exige par le format xlsx.
    new_row = f'<row r="{row}" spans="1:5" x14ac:dyDescent="0.2">{cell}</row>'
    for existing in sorted(set(int(m) for m in re.findall(r'<row r="(\d+)"', xml))):
        if existing > row:
            return re.sub(rf'(<row r="{existing}")', rf'{new_row}\1', xml, count=1)
    return xml


def _set_client(xml: str, nom: str, tel: str, email: str) -> str:
    # Bloc client : garde le style du template s'il existe, sinon aligne a droite (s=1).
    xml = _set_cell_text(xml, "E10", nom, style="1", keep_style=True)
    xml = _set_cell_text(xml, "E11", tel, style="1", keep_style=True)
    xml = _set_cell_text(xml, "E12", email, style="1", keep_style=True)
    return xml


def _fr(d) -> str:
    """Date au format francais jj/mm/aaaa (ecrite en texte pour un affichage fiable)."""
    return d.strftime("%d/%m/%Y") if d else ""


def _set_prestation(xml: str, date_prestation) -> str:
    # B16 = date de prestation, en texte (garde le style du template s'il existe).
    if not date_prestation:
        return xml
    return _set_cell_text(xml, "B16", "   " + _fr(date_prestation), style="1", keep_style=True)


def _generate_xlsx(dest_path: Path, lignes: list[LigneDevis], set_header, template: Path = None) -> Path:
    """Coeur commun de generation (devis et factures) : copie le template, applique
    bordures + tableau, laisse `set_header(xml, st)` remplir les champs specifiques, rezippe."""
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    work = dest_path.with_suffix(".work")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    with zipfile.ZipFile(template or settings.template_file) as z:
        z.extractall(work)

    styles_p = work / "xl/styles.xml"
    styles_xml, st = _ensure_border_styles(styles_p.read_text(encoding="utf-8"))
    styles_p.write_text(styles_xml, encoding="utf-8")

    sheet_p = work / "xl/worksheets/sheet1.xml"
    xml = sheet_p.read_text(encoding="utf-8")
    xml = _build_sheet(xml, lignes, st)
    xml = set_header(xml)
    sheet_p.write_text(xml, encoding="utf-8")

    wb_p = work / "xl/workbook.xml"
    wbx = wb_p.read_text(encoding="utf-8")
    if "fullCalcOnLoad" not in wbx:
        wbx = re.sub(r'<calcPr ', '<calcPr fullCalcOnLoad="1" ', wbx, count=1)
    wb_p.write_text(wbx, encoding="utf-8")

    tbl_p = work / "xl/tables/table1.xml"
    n = max(len(lignes), 1)
    txml = tbl_p.read_text(encoding="utf-8")
    txml = re.sub(r'ref="A17:E\d+"', f'ref="A17:E{HEADER_ROW + n}"', txml)
    tbl_p.write_text(txml, encoding="utf-8")

    cc = work / "xl/calcChain.xml"
    if cc.exists():
        cc.unlink()
        ct_p = work / "[Content_Types].xml"
        ct_p.write_text(re.sub(r'<Override PartName="/xl/calcChain.xml"[^>]*/>', '',
                               ct_p.read_text(encoding="utf-8")), encoding="utf-8")
        wr_p = work / "xl/_rels/workbook.xml.rels"
        wr_p.write_text(re.sub(r'<Relationship [^>]*calcChain[^>]*/>', '',
                               wr_p.read_text(encoding="utf-8")), encoding="utf-8")

    if dest_path.exists():
        dest_path.unlink()
    with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(work):
            for f in files:
                full = Path(root) / f
                z.write(full, full.relative_to(work).as_posix())
    shutil.rmtree(work)
    return dest_path


def write_devis(data: DevisData, dest_path: Path) -> Path:
    """Genere un .xlsx de devis a partir des donnees structurees."""
    def header(xml: str) -> str:
        # E2 = date du devis, au format jj/mm/aaaa (texte), en gardant le style du template.
        xml = _set_cell_text(xml, "E2", _fr(data.date_devis), keep_style=True)
        xml = _set_prestation(xml, data.date_prestation)
        xml = _set_client(xml, data.client_nom, data.client_tel, data.client_email)
        return xml
    return _generate_xlsx(dest_path, data.lignes, header)


def write_facture(data, dest_path: Path) -> Path:
    """Genere un .xlsx de facture. Les libelles (N°, echeance...) sont deja dans le template :
    on ecrit uniquement les VALEURS, en gardant le format des cellules du template."""
    def header(xml: str) -> str:
        xml = _set_cell_text(xml, "E2", _fr(data.date_facture), keep_style=True)   # date de facturation
        xml = _set_cell_text(xml, "E3", str(data.numero), keep_style=True)          # numero (brut)
        xml = _set_cell_text(xml, "E4", _fr(data.date_echeance), keep_style=True)   # date d'echeance
        xml = _set_prestation(xml, data.date_prestation)
        xml = _set_client(xml, data.client_nom, data.client_tel, data.client_email)
        return xml
    return _generate_xlsx(dest_path, data.lignes, header, template=settings.facture_template_file)

    # Force le recalcul complet a l'ouverture.
    wb_p = work / "xl/workbook.xml"
    wbx = wb_p.read_text(encoding="utf-8")
    if "fullCalcOnLoad" not in wbx:
        wbx = re.sub(r'<calcPr ', '<calcPr fullCalcOnLoad="1" ', wbx, count=1)
    wb_p.write_text(wbx, encoding="utf-8")

    # Etend la reference du tableau au nombre de lignes.
    tbl_p = work / "xl/tables/table1.xml"
    n = max(len(data.lignes), 1)
    txml = tbl_p.read_text(encoding="utf-8")
    txml = re.sub(r'ref="A17:E\d+"', f'ref="A17:E{HEADER_ROW + n}"', txml)
    tbl_p.write_text(txml, encoding="utf-8")

    # Supprime calcChain (recalcule automatiquement, evite les avertissements Excel).
    cc = work / "xl/calcChain.xml"
    if cc.exists():
        cc.unlink()
        ct_p = work / "[Content_Types].xml"
        ct_p.write_text(re.sub(r'<Override PartName="/xl/calcChain.xml"[^>]*/>', '',
                               ct_p.read_text(encoding="utf-8")), encoding="utf-8")
        wr_p = work / "xl/_rels/workbook.xml.rels"
        wr_p.write_text(re.sub(r'<Relationship [^>]*calcChain[^>]*/>', '',
                               wr_p.read_text(encoding="utf-8")), encoding="utf-8")

    if dest_path.exists():
        dest_path.unlink()
    with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(work):
            for f in files:
                full = Path(root) / f
                z.write(full, full.relative_to(work).as_posix())
    shutil.rmtree(work)
    return dest_path


# ============================ LECTURE (scan) ============================

def _to_float(v) -> float:
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(" ", "").replace(" ", "").replace(",", "."))
    except ValueError:
        return 0.0


def _parse_date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str) and v.strip():
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
            try:
                return datetime.strptime(v.strip(), fmt).date()
            except ValueError:
                continue
    return None


def _read_lignes(ws) -> list[LigneDevis]:
    last_row = BODY_ROW
    if "Tableau1" in ws.tables:
        m = re.search(r':E(\d+)', ws.tables["Tableau1"].ref)
        if m:
            last_row = int(m.group(1))
    lignes: list[LigneDevis] = []
    for r in range(BODY_ROW, last_row + 1):
        produit = ws.cell(row=r, column=1).value
        prix = _to_float(ws.cell(row=r, column=3).value)
        qte = _to_float(ws.cell(row=r, column=2).value)
        if (produit is None or str(produit).strip() == "") and prix == 0.0:
            continue
        lignes.append(LigneDevis(
            produit=str(produit or ""), quantite=qte, prix_unit_ht=prix,
            tva_pct=round(_to_float(ws.cell(row=r, column=4).value) * 100, 2),
        ))
    return lignes


def _read_client(ws) -> tuple[str, str, str]:
    return (str(ws["E10"].value or "").strip(),
            str(ws["E11"].value or "").strip(),
            str(ws["E12"].value or "").strip())


def read_devis(src_path: Path) -> DevisData:
    """Relit un .xlsx de devis (potentiellement modifie a la main) vers DevisData."""
    wb = openpyxl.load_workbook(src_path, data_only=True)
    ws = wb.active
    nom, tel, email = _read_client(ws)
    return DevisData(
        date_devis=_parse_date(ws["E2"].value) or date.today(),
        date_prestation=_parse_date(ws["B16"].value),
        client_nom=nom, client_tel=tel, client_email=email,
        lignes=_read_lignes(ws),
    )


def read_facture(src_path: Path):
    """Relit un .xlsx de facture vers FactureData (le numero vient du nom de fichier)."""
    from .schemas import FactureData
    wb = openpyxl.load_workbook(src_path, data_only=True)
    ws = wb.active
    nom, tel, email = _read_client(ws)
    return FactureData(
        numero=str(ws["E3"].value or "").strip(),      # numero en E3 (info ; le scan utilise le nom de fichier)
        date_facture=_parse_date(ws["E2"].value) or date.today(),
        date_echeance=_parse_date(ws["E4"].value),     # echeance en E4 (date brute)
        date_prestation=_parse_date(ws["B16"].value),
        client_nom=nom, client_tel=tel, client_email=email,
        lignes=_read_lignes(ws),
    )
