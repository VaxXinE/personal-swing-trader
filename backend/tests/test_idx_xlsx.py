"""Synthetic XLSX tests with no external downloads or spreadsheet engine dependency."""
from __future__ import annotations

from pathlib import Path
import zipfile

import pytest
from app.universe import DiscoveryError, discover_idx_file, sync_discovery, _atomic_write
from app.xlsx_rows import read_xlsx_tables, WorkbookFormatError

PREFIX = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'


def _make_xlsx(path: Path, *, missing_header: bool = False, bad_shared: bool = False,
               multiple_sheets: bool = True) -> Path:
    # A representative OOXML file with shifted headers, sparse columns, shared strings,
    # inline text, and a second sheet. No Excel or external dependency is needed.
    book = f'''<?xml version="1.0" encoding="UTF-8"?>
    <workbook xmlns="{PREFIX}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
      <sheets><sheet name="Petunjuk" sheetId="1" r:id="rId1"/>
      <sheet name="Daftar Saham" sheetId="2" r:id="rId2"/></sheets></workbook>'''
    rels = '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
      <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="/xl/worksheets/sheet2.xml"/>
    </Relationships>'''
    names = ['Kode', 'Nama Perusahaan', 'Papan Pencatatan', 'Bank Central Asia Tbk',
             'Bank Rakyat Indonesia Tbk', 'Utama', 'Pemantauan Khusus', 'Contoh Perusahaan']
    shared = f'<sst xmlns="{PREFIX}" count="9" uniqueCount="{len(names)}">' + ''.join(
        f'<si><t>{n}</t></si>' for n in names) + '</sst>'
    header = '<c r="B4" t="s"><v>0</v></c><c r="D4" t="s"><v>1</v></c><c r="G4" t="s"><v>2</v></c>'
    if missing_header:
        header = '<c r="B4" t="inlineStr"><is><t>No.</t></is></c>'
    index = '900' if bad_shared else '3'
    rows = f'''
      <row r="2"><c r="B2" t="inlineStr"><is><t>DAFTAR SAHAM IDX</t></is></c></row>
      <row r="4">{header}</row>
      <row r="5"><c r="A5"><v>1</v></c><c r="B5" t="inlineStr"><is><t>BBCA</t></is></c><c r="D5" t="s"><v>{index}</v></c><c r="G5" t="s"><v>5</v></c></row>
      <row r="6"><c r="B6" t="inlineStr"><is><t>TEST</t></is></c><c r="D6" t="s"><v>7</v></c><c r="G6" t="s"><v>6</v></c></row>
      <row r="7"><c r="B7" t="inlineStr"><is><t>BBRI</t></is></c><c r="D7" t="s"><v>4</v></c><c r="G7" t="s"><v>5</v></c></row>
      <row r="8"><c r="B8" t="inlineStr"><is><t>INVALID1</t></is></c><c r="D8" t="s"><v>7</v></c></row>
    '''
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('xl/workbook.xml', book)
        zf.writestr('xl/_rels/workbook.xml.rels', rels)
        zf.writestr('xl/sharedStrings.xml', shared)
        zf.writestr('xl/worksheets/sheet1.xml', f'<worksheet xmlns="{PREFIX}"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Info</t></is></c></row></sheetData></worksheet>')
        zf.writestr('xl/worksheets/sheet2.xml', f'<worksheet xmlns="{PREFIX}"><sheetData>{rows}</sheetData></worksheet>')
    return path


def test_idx_xlsx_multiple_sheets_and_shifted_header(tmp_path):
    book = _make_xlsx(tmp_path / 'Daftar Saham 20261023.xlsx')
    instruments, total = discover_idx_file(book, limit=35)
    assert total == 2
    assert [i.symbol for i in instruments] == ['BBCA', 'BBRI']
    assert [i.provider_symbol for i in instruments] == ['BBCA.JK', 'BBRI.JK']


def test_idx_xlsx_cap_and_sync_status(tmp_path):
    book = _make_xlsx(tmp_path / 'idx.xlsx')
    snap = tmp_path / 'snapshot.json'
    outcome = sync_discovery(['IDX'], idx_file=book, idx_limit=1, path=snap)
    assert outcome['snapshot_updated']
    assert not outcome['errors']
    assert outcome['markets']['IDX']['discovered'] == 2
    assert outcome['markets']['IDX']['selected'] == 1
    assert outcome['markets']['IDX']['source'] == 'IDX_USER_IMPORTED_XLSX'
    assert len(__import__('json').loads(snap.read_text())['instruments']) == 1


def test_idx_xlsx_missing_columns_preserves_snapshot(tmp_path):
    snap = tmp_path / 'snapshot.json'
    initial = {'version': 1, 'generated_at': '2026-01-01', 'markets': {'IDX': {'selected': 1}},
               'instruments': [{'market': 'IDX', 'symbol': 'OLD'}]}
    _atomic_write(snap, initial)
    before = snap.read_bytes()
    book = _make_xlsx(tmp_path / 'bad.xlsx', missing_header=True)
    result = sync_discovery(['IDX'], idx_file=book, path=snap)
    assert len(result['errors']) == 1
    assert result['snapshot_updated'] is False
    assert snap.read_bytes() == before


def test_idx_xlsx_bad_shared_strings_rejected(tmp_path):
    book = _make_xlsx(tmp_path / 'invalid.xlsx', bad_shared=True)
    with pytest.raises(DiscoveryError, match='shared string'):
        discover_idx_file(book, 35)


def test_idx_xlsx_rejects_unreadable_and_invalid_extensions(tmp_path):
    bad = tmp_path / 'corrupted.xlsx'
    bad.write_bytes(b'not an Excel file')
    with pytest.raises(DiscoveryError, match='could not be read'):
        discover_idx_file(bad, 35)
    extension = tmp_path / 'danger.xlsm'
    extension.write_text('dummy')
    with pytest.raises(DiscoveryError, match='Unsupported'):
        discover_idx_file(extension, 35)


def test_idx_xlsx_zip_bomb_metadata_limit(tmp_path):
    path = tmp_path / 'huge.xlsx'
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('xl/worksheets/sheet1.xml', ' ' * 37_000_000)
    with pytest.raises(WorkbookFormatError, match='safety limits'):
        read_xlsx_tables(path)
