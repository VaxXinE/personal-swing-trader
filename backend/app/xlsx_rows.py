"""Read tabular text cells from a bounded .xlsx workbook (OOXML, no macros or formulas).

This intentionally supports only the features used by IDX listing exports: shared/inline
strings, cached numeric values and multiple worksheets. Unknown/encrypted Excel formats
fail closed. No executable spreadsheet content is evaluated.
"""
from __future__ import annotations

import posixpath
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

XLSX_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
MAX_COMPRESSED_BYTES = 8_000_000
MAX_INFLATED_BYTES = 36_000_000
MAX_SHEET_BYTES = 24_000_000
MAX_ROWS = 5_000
MAX_COLUMNS = 70
_CELL = re.compile(r"^([A-Z]{1,3})([1-9][0-9]*)$")

class WorkbookFormatError(ValueError):
    pass


def _xml(zf: zipfile.ZipFile, filename: str) -> ET.Element:
    try:
        return ET.fromstring(zf.read(filename))
    except (KeyError, ET.ParseError, ValueError, RuntimeError) as exc:
        raise WorkbookFormatError("Invalid Excel XML data") from exc


def _text(element: ET.Element) -> str:
    return "".join(node.text or "" for node in element.iter(f"{{{XLSX_NS}}}t"))


def _shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = _xml(zf, "xl/sharedStrings.xml")
    return [_text(si) for si in root.findall(f"{{{XLSX_NS}}}si")]


def _sheet_files(zf: zipfile.ZipFile) -> list[str]:
    workbook = _xml(zf, "xl/workbook.xml")
    rel_root = _xml(zf, "xl/_rels/workbook.xml.rels")
    relationships = {}
    for item in rel_root.findall(f"{{{PKG_REL_NS}}}Relationship"):
        rid, target, kind = item.get("Id"), item.get("Target", ""), item.get("Type", "")
        if rid and kind.endswith("/worksheet") and item.get("TargetMode") != "External":
            # OOXML relationship targets are relative to xl/workbook.xml.
            path = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
            if path.startswith("xl/worksheets/") and ".." not in path.split("/"):
                relationships[rid] = path
    result = []
    for sheet in workbook.findall(f"{{{XLSX_NS}}}sheets/{{{XLSX_NS}}}sheet"):
        path = relationships.get(sheet.get(f"{{{DOC_REL_NS}}}id"))
        if path and path in zf.namelist():
            result.append(path)
    if not result:
        raise WorkbookFormatError("No readable worksheets in Excel workbook")
    return result


def _col_index(label: str) -> int:
    index = 0
    for character in label:
        index = index * 26 + ord(character) - ord("A") + 1
    return index - 1


def _read_sheet(zf: zipfile.ZipFile, filename: str, shared: list[str]) -> list[list[str]]:
    root = _xml(zf, filename)
    output = []
    for row in root.findall(f".//{{{XLSX_NS}}}sheetData/{{{XLSX_NS}}}row"):
        if len(output) >= MAX_ROWS:
            raise WorkbookFormatError("Excel worksheet exceeds 5000 rows")
        values = [""] * MAX_COLUMNS
        for cell in row.findall(f"{{{XLSX_NS}}}c"):
            match = _CELL.fullmatch(cell.get("r", ""))
            if not match:
                continue
            column = _col_index(match.group(1))
            if column >= MAX_COLUMNS:
                continue
            typ = cell.get("t", "")
            if typ == "inlineStr":
                inline = cell.find(f"{{{XLSX_NS}}}is")
                value = _text(inline) if inline is not None else ""
            else:
                node = cell.find(f"{{{XLSX_NS}}}v")
                value = node.text if node is not None and node.text else ""
                if typ == "s":
                    try:
                        value = shared[int(value)]
                    except (ValueError, IndexError) as exc:
                        raise WorkbookFormatError("Invalid shared string index") from exc
            values[column] = value.strip()
        if any(values):
            # Preserve the sparse columns for proper Kode/Nama mapping.
            output.append(values)
    return output


def read_xlsx_tables(path: Path) -> list[list[list[str]]]:
    """Return nonempty worksheet rows; never evaluate formulas or execute workbook code."""
    if path.suffix.lower() != ".xlsx":
        raise WorkbookFormatError("Only .xlsx Excel workbooks are supported")
    if not path.is_file():
        raise WorkbookFormatError("Excel file not found")
    if path.stat().st_size > MAX_COMPRESSED_BYTES:
        raise WorkbookFormatError("Excel file exceeds 8 MB limit")
    try:
        with zipfile.ZipFile(path) as zf:
            infos = zf.infolist()
            if len(infos) > 1000 or sum(info.file_size for info in infos) > MAX_INFLATED_BYTES:
                raise WorkbookFormatError("Excel archive exceeds safety limits")
            if any(info.file_size > MAX_SHEET_BYTES for info in infos):
                raise WorkbookFormatError("Excel archive contains an oversized component")
            if any("vbaproject" in info.filename.lower() for info in infos):
                raise WorkbookFormatError("Macro-containing workbook is not accepted")
            shared = _shared_strings(zf)
            tables = [_read_sheet(zf, sheet, shared) for sheet in _sheet_files(zf)]
            return [rows for rows in tables if rows]
    except (zipfile.BadZipFile, OSError, ET.ParseError) as exc:
        raise WorkbookFormatError("Invalid or unreadable Excel file") from exc
