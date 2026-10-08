import csv
from pathlib import Path
import qrcode
from PIL import Image
from modules.models import Student
from modules.photo_sorter import sort_photos, _decode_qr, _iter_images, _student_folder
from modules.pdf_reader import preview_pdf

STUDENTS = [Student('23162','0042','Alex Example','10/Fp1'), Student('23162','0043','Sam Example','10/Fp2')]

def page(payload=None):
    im=Image.new('RGB',(850,1100),'white')
    if payload:
        im.paste(qrcode.make(payload).convert('RGB'),(200,300))
    return im

def pdf(path,payloads):
    pages=[page(p) for p in payloads]
    pages[0].save(path,'PDF',save_all=True,append_images=pages[1:],resolution=100)

def test_multipage_pdf_blank_first_page_and_nested_mixed_files(tmp_path):
    source=tmp_path/'source';nested=source/'Camera1'/'Week2';nested.mkdir(parents=True)
    document=nested/'evidence.PDF'
    pdf(document,[None,STUDENTS[0].qr_payload,STUDENTS[1].qr_payload])
    photo=source/'food.jpg';page(STUDENTS[0].qr_payload).save(photo)
    before=document.read_bytes()
    out=tmp_path/'out'
    result=sort_photos([source,nested],out,STUDENTS)
    assert result.sorted==2 and result.student_copies==3 and result.originals_copied==2
    assert result.errors==result.review==0
    for student in STUDENTS:assert (_student_folder(out,student)/document.name).read_bytes()==before
    assert (out/'All_Original_Images'/document.name).read_bytes()==before
    assert document.read_bytes()==before
    repeated=sort_photos([source],out,STUDENTS)
    assert repeated.already_copied==2 and repeated.originals_already_copied==2 and repeated.student_copies==0

def test_unknown_on_later_pdf_page_requires_review(tmp_path):
    src=tmp_path/'src';src.mkdir()
    pdf(src/'both.pdf',[STUDENTS[0].qr_payload,'NEA|23162|9999'])
    out=tmp_path/'out';result=sort_photos([src],out,STUDENTS)
    assert result.sorted==result.review==1
    assert (out/'Manual_Check_Required'/'both.pdf').exists()

def test_damaged_pdf_before_valid_photo_preserved_for_review(tmp_path):
    src=tmp_path/'src';src.mkdir()
    (src/'a_bad.pdf').write_bytes(b'not a PDF')
    page(STUDENTS[0].qr_payload).save(src/'b_valid.png')
    out=tmp_path/'out';result=sort_photos([src],out,STUDENTS)
    assert result.sorted==result.review==1 and result.errors==0
    assert (out/'Manual_Check_Required'/'a_bad.pdf').read_bytes()==b'not a PDF'
    with open(result.report_csv,encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
    assert 'PDF could not be opened' in rows[0]['detail']

def test_recursive_enumeration_deduplicates_overlapping_sources(tmp_path):
    src=tmp_path/'src';deep=src/'a'/'b'/'c';deep.mkdir(parents=True)
    (deep/'one.PDF').write_bytes(b'pdf');(deep/'two.JPG').write_bytes(b'image')
    (deep/'notes.txt').write_text('ignore')
    out=tmp_path/'out';out.mkdir()
    found=list(_iter_images([src,src/'a',deep],out))
    assert {p.name for p in found}=={'one.PDF','two.JPG'} and len(found)==2

def test_pdf_preview_returns_page_count(tmp_path):
    path=tmp_path/'preview.pdf';pdf(path,[None,STUDENTS[0].qr_payload])
    preview,count=preview_pdf(path)
    assert count==2 and max(preview.size)<=901 and preview.mode=='RGB'
