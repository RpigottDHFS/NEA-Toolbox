import csv
from pathlib import Path
import pandas as pd
import pytest
from PIL import Image
import qrcode
from modules.models import Student
from modules.excel_loader import load_students
from modules import photo_sorter as ps

@pytest.fixture
def roster():
    return [Student('23162','0042','Alex Example','10/Fp1'),Student('23162','0043','Sam Example','10/Fp2')]

def fixture_files(tmp_path, mapping):
    src=tmp_path/'input';src.mkdir()
    for i,name in enumerate(mapping):
        (src/name).write_bytes(f'photo {i}'.encode())
    return src

def test_multi_student_originals_repeat_and_unknown(tmp_path,monkeypatch,roster):
    mapping={'a.jpg':[], 'b.jpg':[roster[0].qr_payload,roster[1].qr_payload], 'c.jpg':[roster[0].qr_payload,'NEA|23162|9999']}
    src=fixture_files(tmp_path,mapping);out=tmp_path/'output'
    calls=[]
    def decode(path):calls.append(path.name);return mapping[path.name]
    monkeypatch.setattr(ps,'_decode_qr',decode)
    result=ps.sort_photos([src],out,roster)
    assert result.sorted==2 and result.student_copies==3 and result.review==2 and result.errors==0
    assert result.originals_copied==3
    assert Path(result.matched_example).name=='b.jpg'
    assert calls==['a.jpg','b.jpg','c.jpg'] # cached preflight decoding
    for name in mapping:assert (out/'All_Original_Images'/name).read_bytes()==(src/name).read_bytes()
    for student in roster:assert (ps._student_folder(out,student)/'b.jpg').read_bytes()==(src/'b.jpg').read_bytes()
    rows=list(csv.DictReader(open(result.report_csv,encoding='utf-8-sig')))
    assert rows[1]['candidate_number']=='0042;0043'
    again=ps.sort_photos([src],out,roster)
    assert again.already_copied==3 and again.student_copies==again.originals_copied==0
    assert again.originals_already_copied==3

def test_no_match_stops_without_copy(tmp_path,monkeypatch,roster):
    src=fixture_files(tmp_path,{'a.jpg':[],'b.jpg':[]});out=tmp_path/'out'
    monkeypatch.setattr(ps,'_decode_qr',lambda p:['NEA|99999|0042'])
    with pytest.raises(ValueError,match='No readable student QR'):ps.sort_photos([src],out,roster)
    assert not out.exists()

def test_unknown_first_is_skipped(tmp_path,monkeypatch,roster):
    data={'a.jpg':['9999'],'b.jpg':[],'c.jpg':[roster[1].qr_payload]}
    src=fixture_files(tmp_path,data)
    monkeypatch.setattr(ps,'_decode_qr',lambda p:data[p.name])
    result=ps.sort_photos([src],tmp_path/'out',roster)
    assert Path(result.matched_example).name=='c.jpg' and result.review==2

def test_changed_excel_column_order_and_blank_duplicate_headings(tmp_path):
    path=tmp_path/'roster.xlsx'
    original=[['School'],['Name','Candidate number','Group Code'],['Alex Example','0042','10/Fp1']]
    pd.DataFrame(original).to_excel(path,index=False,header=False)
    before=load_students(path)
    changed=[['School'],['Notes',None,None,'Group Code','New field','Name','Candidate number'],['note',None,None,'10/Fp1','extra','Alex Example','0042']]
    pd.DataFrame(changed).to_excel(path,index=False,header=False)
    after=load_students(path)
    assert after.students==before.students
    assert after.column_mappings and after.students[0].candidate_number=='0042'

def test_identity_centre_and_legacy(roster):
    m={s.candidate_number:s for s in roster}
    assert ps._candidate_from_payload('NEA|99999|0042',m) is None
    assert ps._candidate_from_payload('NEA1|23162|0042',m)=='0042'
    assert ps._candidate_from_payload('0042',m)=='0042'

def test_same_names_different_sources_archive_safely(tmp_path,monkeypatch,roster):
    a=tmp_path/'a';b=tmp_path/'b';a.mkdir();b.mkdir()
    (a/'one.jpg').write_bytes(b'one');(b/'one.jpg').write_bytes(b'two')
    monkeypatch.setattr(ps,'_decode_qr',lambda p:[roster[0].qr_payload])
    out=tmp_path/'out';result=ps.sort_photos([a,b],out,roster)
    assert result.originals_copied==2
    assert {p.read_bytes() for p in (out/'All_Original_Images').iterdir()}=={b'one',b'two'}
    again=ps.sort_photos([a,b],out,roster)
    assert again.already_copied==2 and again.originals_already_copied==2

def test_cancel_in_preflight(tmp_path,roster):
    src=fixture_files(tmp_path,{'a.jpg':[]});out=tmp_path/'out'
    result=ps.sort_photos([src],out,roster,should_cancel=lambda:True)
    assert result.cancelled and not out.exists()

def test_actual_qr_group_photo(tmp_path,roster):
    src=tmp_path/'src';src.mkdir()
    Image.new('RGB',(600,400),'white').save(src/'a_missing.jpg')
    im=Image.new('RGB',(1200,650),'white')
    for x,s in zip((70,700),roster):im.paste(qrcode.make(s.qr_payload).convert('RGB'),(x,100))
    im.save(src/'b_group.png')
    result=ps.sort_photos([src],tmp_path/'out',roster)
    assert result.sorted==1 and result.student_copies==2 and result.review==1 and result.originals_copied==2

def test_partial_destination_error_keeps_archive_and_other_copy(tmp_path,monkeypatch,roster):
    src=fixture_files(tmp_path,{'a.jpg':[]});out=tmp_path/'out';out.mkdir()
    monkeypatch.setattr(ps,'_decode_qr',lambda p:[s.qr_payload for s in roster])
    ps._student_folder(out,roster[0]).parent.mkdir()
    ps._student_folder(out,roster[0]).write_bytes(b'blocking file')
    result=ps.sort_photos([src],out,roster)
    assert result.errors==1 and result.student_copies==1 and result.originals_copied==1
    assert (ps._student_folder(out,roster[1])/'a.jpg').exists()

def test_worker_reloads_current_excel_and_reports_failure(tmp_path,monkeypatch):
    import app
    path=tmp_path/'roster.xlsx'
    pd.DataFrame({'Name':['Alex Example'],'Candidate number':['0042'],'Group Code':['New group']}).to_excel(path,index=False)
    ui=object.__new__(app.NEAToolbox)
    class Root:
        def __init__(self):self.callbacks=[]
        def after(self,_delay,callback):self.callbacks.append(callback)
    ui.root=Root();ui.cancel_requested=False
    captured=[]
    monkeypatch.setattr(app,'sort_photos',lambda sources,out,students,**kw:captured.extend(students) or ps.SortSummary())
    ui._sort_worker([],str(tmp_path/'out'),path,'23162')
    assert captured[0].group_code=='New group'
    ui.root.callbacks.clear()
    ui._sort_failed=lambda exc:captured.append(str(exc))
    ui._sort_worker([],str(tmp_path/'out'),tmp_path/'missing.xlsx','23162')
    ui.root.callbacks[0]()  # Exception survives the worker scope for the GUI callback.
    assert 'missing.xlsx' in captured[-1]

def test_unsupported_original_is_archived(tmp_path,monkeypatch,roster):
    data={'a.heic':[], 'b.jpg':[roster[0].qr_payload]}
    src=fixture_files(tmp_path,data)
    monkeypatch.setattr(ps,'_decode_qr',lambda p:data[p.name])
    result=ps.sort_photos([src],tmp_path/'out',roster)
    assert result.originals_copied==2 and result.review==1
