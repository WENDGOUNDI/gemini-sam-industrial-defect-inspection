"""VisionAI inspection UI. Start with: python app.py"""
import asyncio
import base64
import io
import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from nicegui import ui, run, app
from config import PORT, MAX_IMAGE_MB
from utils.image_utils import decode_image, to_data_url
from services.inspection_service import inspect, notify_mes
from services.sam_service import sam_engine
from services.history_service import recent, get_inspection
from utils.report_utils import csv_bytes, pdf_bytes


@dataclass
class PageState:
    reference: bytes | None = None
    test: bytes | None = None
    batch: list[tuple[str,bytes]] = field(default_factory=list)
    result: dict | None = None

async def read_upload(e):
    """NiceGUI >=2.0 e.file.read() (async); older versions e.content.read()."""
    if hasattr(e,'file'):
        data = e.file.read()
        if asyncio.iscoroutine(data): data = await data
    elif hasattr(e,'content'):
        data = e.content.read()
        if asyncio.iscoroutine(data): data = await data
    else:
        raise ValueError('Unsupported NiceGUI upload event API')
    return bytes(data)

def data_url_to_bytes(data_url):
    if not isinstance(data_url,str) or not data_url.startswith('data:image/'):
        raise ValueError('Camera did not return an image')
    return base64.b64decode(data_url.split(',',1)[1],validate=True)

@ui.page('/')
def main_page():
    ui.colors(primary='#17243c',secondary='#334155',accent='#2563eb',positive='#059669',negative='#dc2626')
    state = PageState()  # each browser page gets its own uploaded bytes
    ui.query('body').classes('bg-slate-100')
    with ui.header().classes('bg-slate-900 text-white px-6 py-3 items-center justify-between'):
        ui.label('◈  VisionAI Industrial Inspection').classes('text-xl font-bold')
        ui.label('Gemini + SAM | AOI').classes('text-slate-300 text-sm')
    with ui.column().classes('w-full max-w-7xl mx-auto p-5 gap-5'):
        ui.label('Inspection Setup').classes('text-2xl font-bold text-slate-800')
        with ui.row().classes('w-full gap-4 items-stretch'):
            with ui.card().classes('flex-1 min-w-72 p-4'):
                ui.label('1. Reference (Defect-Free)').classes('font-semibold')
                ref_preview = ui.image().classes('w-full h-52 object-contain bg-slate-100 rounded').style('object-fit:contain')
                ref_status = ui.label('Waiting for image').classes('text-sm text-slate-500')
                async def ref_upload(e):
                    try:
                        raw = await read_upload(e)
                        img = decode_image(raw)
                        state.reference = raw
                        ref_preview.set_source(to_data_url(img))
                        ref_status.set_text(f'✓ Ready · {img.shape[1]}×{img.shape[0]} · {len(raw)//1024} KB')
                        sync_button()
                        ref_uploader.reset()
                    except Exception as ex:
                        state.reference = None
                        ref_status.set_text('Upload failed')
                        ui.notify(str(ex),type='negative')
                        sync_button()
                ref_uploader = ui.upload(on_upload=ref_upload,auto_upload=True,multiple=False).props('accept=image/*').classes('hidden')
                ui.button('Upload / Replace', icon='upload_file', on_click=lambda: ref_uploader.run_method('pickFiles')).props('outline size=sm')
                with ui.row():
                    ui.button('Capture camera',on_click=lambda: capture_camera('reference'),icon='photo_camera').props('outline size=sm')
                    ui.button('Clear',on_click=lambda: clear_image('reference'),icon='delete_outline').props('flat size=sm')
            with ui.card().classes('flex-1 min-w-72 p-4'):
                ui.label('2. Test Image').classes('font-semibold')
                test_preview = ui.image().classes('w-full h-52 object-contain bg-slate-100 rounded').style('object-fit:contain')
                test_status = ui.label('Waiting for image').classes('text-sm text-slate-500')
                async def test_upload(e):
                    try:
                        raw = await read_upload(e)
                        img = decode_image(raw)
                        state.test = raw
                        test_preview.set_source(to_data_url(img))
                        test_status.set_text(f'✓ Ready · {img.shape[1]}×{img.shape[0]} · {len(raw)//1024} KB')
                        sync_button()
                        test_uploader.reset()
                    except Exception as ex:
                        state.test = None
                        test_status.set_text('Upload failed')
                        ui.notify(str(ex),type='negative')
                        sync_button()
                test_uploader = ui.upload(on_upload=test_upload,auto_upload=True,multiple=False).props('accept=image/*').classes('hidden')
                ui.button('Upload / Replace', icon='upload_file', on_click=lambda: test_uploader.run_method('pickFiles')).props('outline size=sm')
                with ui.row():
                    ui.button('Capture camera',on_click=lambda: capture_camera('test'),icon='photo_camera').props('outline size=sm')
                    ui.button('Clear',on_click=lambda: clear_image('test'),icon='delete_outline').props('flat size=sm')
        with ui.row().classes('items-center gap-4'):
            align_toggle = ui.switch('Auto-align images',value=False)
            inspect_button = ui.button('START INSPECTION',icon='document_scanner').classes('px-8 py-3')
            inspect_button.disable()
        status_note = ui.label('Upload both images to enable inspection.').classes('text-sm text-slate-500')
        with ui.column().classes('w-full gap-4') as results_panel:
            results_panel.set_visibility(False)
            ui.label('Inspection Results').classes('text-xl font-bold')
            with ui.row().classes('w-full gap-4 items-start'):
                with ui.card().classes('flex-1 min-w-72'):
                    ui.label('Reference').classes('font-semibold')
                    result_reference = ui.image().classes('w-full object-contain').style('max-height:420px;object-fit:contain')
                with ui.card().classes('flex-1 min-w-72'):
                    ui.label('AI Analysis').classes('font-semibold')
                    result_image = ui.image().classes('w-full object-contain').style('max-height:420px;object-fit:contain')
                with ui.card().classes('w-64'):
                    result_status = ui.label('PENDING').classes('text-3xl font-bold')
                    result_summary = ui.label('').classes('text-sm')
                    result_count = ui.label('Defects: 0')
                    result_time = ui.label('Time: -')
                    result_alignment = ui.label('').classes('text-xs text-slate-500')
            ui.label('Detected regions').classes('font-semibold')
            defect_container = ui.column().classes('w-full gap-2')
            with ui.row().classes('gap-2'):
                ui.button('Export PDF',icon='picture_as_pdf',on_click=lambda: export_result('pdf'))
                ui.button('Export CSV',icon='table_view',on_click=lambda: export_result('csv')).props('outline')
                ui.button('Download annotated image',icon='image',on_click=lambda: export_result('image')).props('outline')
                ui.button('Send to MES',icon='send',on_click=lambda: send_mes()).props('outline')
        with ui.expansion('Batch inspection (ZIP of test images)',icon='inventory_2').classes('w-full bg-white rounded'):
            ui.label('Upload a reference above, then a ZIP containing PNG/JPG test images (max 30).').classes('text-sm')
            batch_status = ui.label('No batch uploaded')
            async def batch_upload(e):
                try:
                    raw = await read_upload(e)
                    if len(raw) > 100 * 1024 * 1024: raise ValueError('ZIP exceeds 100 MB')
                    images = []
                    with zipfile.ZipFile(io.BytesIO(raw)) as z:
                        entries = [x for x in z.infolist() if not x.is_dir() and Path(x.filename).suffix.lower() in ('.png','.jpg','.jpeg','.webp')]
                        if len(entries) > 30: raise ValueError('Batch limited to 30 images')
                        for entry in entries:
                            if entry.file_size > MAX_IMAGE_MB * 1024 * 1024: raise ValueError(f'File too large: {entry.filename}')
                            data = z.read(entry)
                            decode_image(data)
                            images.append((Path(entry.filename).name,data))
                    state.batch = images
                    batch_status.set_text(f'✓ {len(images)} images ready')
                except Exception as ex:
                    state.batch = []
                    ui.notify(f'Batch upload: {ex}',type='negative')
            ui.upload(on_upload=batch_upload,auto_upload=True).props('accept=.zip')
            batch_progress = ui.label('')
            batch_results = ui.column().classes('gap-1')
            async def run_batch():
                if not state.reference or not state.batch:
                    ui.notify('Upload a reference and batch ZIP first',type='warning');return
                batch_button.disable()
                batch_results.clear()
                summary = io.StringIO()
                import csv
                writer = csv.writer(summary)
                writer.writerow(['filename','status','defects','time_s','inspection_id','error'])
                try:
                    for i,(name,data) in enumerate(state.batch,1):
                        batch_progress.set_text(f'Inspecting {i}/{len(state.batch)}: {name}')
                        try:
                            result = await run.io_bound(inspect,state.reference,data,align_toggle.value)
                            writer.writerow([name,result['status'],len(result['defects']),result['elapsed'],result['id'],''])
                            with batch_results: ui.label(f'{name}: {result["status"]} · {len(result["defects"])} defect(s)')
                        except Exception as ex:
                            writer.writerow([name,'ERROR','','','',str(ex)])
                            with batch_results: ui.label(f'{name}: ERROR — {str(ex)[:100]}').classes('text-red-600')
                    ui.download.content(summary.getvalue().encode('utf-8-sig'),'batch_results.csv','text/csv')
                    batch_progress.set_text('Batch complete — CSV downloaded')
                finally: batch_button.enable()
            batch_button = ui.button('Run batch inspection',on_click=run_batch,icon='play_arrow')
        with ui.expansion('Inspection history',icon='history').classes('w-full bg-white rounded'):
            history_container = ui.column().classes('w-full gap-2')
            async def refresh_history():
                history_container.clear()
                try: records = await run.io_bound(recent,30)
                except Exception as ex:
                    ui.notify(str(ex),type='negative');return
                with history_container:
                    for record in records:
                        with ui.row().classes('items-center justify-between w-full border-b pb-1'):
                            ui.label(f'{record["created_at"][:19]} · {record["status"]} · {record["summary"][:75]}').classes('text-sm')
                            ui.button('View',on_click=lambda uid=record['id']: view_history(uid)).props('flat size=sm')
            ui.button('Refresh history',icon='refresh',on_click=refresh_history).props('outline')

    def sync_button():
        if state.reference is not None and state.test is not None:
            inspect_button.enable()
            status_note.set_text('Both images ready for inspection.')
        else:
            inspect_button.disable()
            status_note.set_text('Upload both images to enable inspection.')

    def clear_image(which):
        setattr(state,which,None)
        if which=='reference':
            ref_preview.set_source('');ref_status.set_text('Waiting for image');ref_uploader.reset()
        else:
            test_preview.set_source('');test_status.set_text('Waiting for image');test_uploader.reset()
        sync_button()

    async def capture_camera(which):
        # getUserMedia requires localhost or HTTPS and browser permission.
        js = '''(async () => {
          const stream = await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'}});
          try { const v=document.createElement('video');v.srcObject=stream;v.muted=true;await v.play();
            await new Promise(r=>setTimeout(r,600));const c=document.createElement('canvas');c.width=v.videoWidth;c.height=v.videoHeight;
            c.getContext('2d').drawImage(v,0,0);return c.toDataURL('image/jpeg',0.92);
          } finally { stream.getTracks().forEach(t=>t.stop()); }
        })()'''
        try:
            data_url = await ui.run_javascript(js,timeout=20)
            raw = data_url_to_bytes(data_url)
            img = decode_image(raw)
            setattr(state,which,raw)
            if which=='reference':
                ref_preview.set_source(to_data_url(img));ref_status.set_text('✓ Camera image ready')
            else:
                test_preview.set_source(to_data_url(img));test_status.set_text('✓ Camera image ready')
            sync_button()
        except Exception as ex:
            ui.notify(f'Camera unavailable: {ex}',type='negative')

    def show_result(result):
        state.result = result
        results_panel.set_visibility(True)
        result_reference.set_source('data:image/jpeg;base64,'+base64.b64encode(result['reference_jpg']).decode())
        result_image.set_source('data:image/jpeg;base64,'+base64.b64encode(result['result_jpg']).decode())
        result_status.set_text(result['status'])
        result_status.classes(remove='text-green-600 text-red-600',add='text-red-600' if result['status']=='FAIL' else 'text-green-600')
        result_summary.set_text(result['summary'])
        result_count.set_text(f'Defects: {len(result["defects"])}')
        result_time.set_text(f'Processing: {result["elapsed"]:.2f}s')
        result_alignment.set_text(result['alignment'])
        defect_container.clear()
        with defect_container:
            if not result['defects']: ui.label('No defects reported.')
            for d in result['defects']:
                with ui.card().classes('w-full p-3'):
                    ui.label(f'#{d["id"]} · {d["type"]}').classes('font-semibold')
                    ui.label(d['description']).classes('text-sm')
                    ui.label(f'Mask area: {d["area_px"]:,} px'+(f' · {d["area_mm2"]} mm²' if d['area_mm2'] is not None else ' · not calibrated')).classes('text-xs text-slate-500')

    async def process_inspection():
        if state.reference is None or state.test is None:
            ui.notify('Please upload both images first.',type='warning');return
        inspect_button.disable()
        status_note.set_text('Analyzing images…')
        try:
            result = await run.io_bound(inspect,state.reference,state.test,align_toggle.value)
            show_result(result)
            status_note.set_text('Inspection complete')
            ui.notify('Inspection complete',type='positive')
        except Exception as ex:
            status_note.set_text('Inspection failed — see error')
            ui.notify(f'Inspection error: {ex}',type='negative',timeout=10000)
        finally: sync_button()

    def export_result(kind):
        if not state.result: return
        r=state.result
        if kind=='pdf': ui.download.content(pdf_bytes(r),f'inspection_{r["id"]}.pdf','application/pdf')
        elif kind=='csv': ui.download.content(csv_bytes(r),f'inspection_{r["id"]}.csv','text/csv')
        else: ui.download.content(r['result_jpg'],f'inspection_{r["id"]}.jpg','image/jpeg')

    async def send_mes():
        if not state.result: return
        try: ui.notify(await run.io_bound(notify_mes,state.result),type='info')
        except Exception as ex: ui.notify(f'MES error: {ex}',type='negative')

    async def view_history(uid):
        record = await run.io_bound(get_inspection,uid)
        if not record: ui.notify('Record not found',type='negative');return
        r={'id':record['id'],'status':record['status'],'summary':record['summary'],'elapsed':record['elapsed'],
           'defects':json.loads(record['defects']),'alignment':record['alignment'],
           'reference_jpg':Path(record['reference_file']).read_bytes(),'result_jpg':Path(record['result_file']).read_bytes()}
        show_result(r)
        ui.notify('Loaded inspection from history')

    inspect_button.on('click',process_inspection)

if __name__ in {'__main__','__mp_main__'}:
    print('Loading SAM into memory at startup...', flush=True)
    sam_engine.load()
    print('SAM ready for inspection.', flush=True)
    ui.run(title='VisionAI Industrial Inspection',port=PORT,reload=False,storage_secret=None)
