"""Cloud project workspace: RLS-secured project, snapshot, review and QR workflow."""
from __future__ import annotations
import streamlit as st
import pandas as pd
from concretelab.cloud_ui import signed_user,cloud_notice
from concretelab.cloud import (
    create_project,list_projects,list_snapshots,load_snapshot,save_snapshot,
    list_reports,new_report,submit_report,review_report,
    print_verification_label,verify_url,get_profile,member_list,add_member,delete_member
)

st.title('Proyek Saya')
st.caption('Workspace berbasis akun untuk menyimpan CSV dan hasil analisis secara permanen pada database Supabase.')
st.divider()

try: client,user=signed_user()
except Exception:
    st.error('Supabase tidak dapat dihubungi. Periksa konfigurasi dan koneksi.')
    st.stop()
if client is None:
    cloud_notice(); st.stop()
if user is None:
    st.info('Silakan login di menu **Akun** untuk membuka proyek cloud. Analisis tanpa akun tetap tersedia di Service.')
    st.stop()
uid=str(user.id)
try: profile=get_profile(client,uid) or {}
except Exception: profile={}
is_admin=profile.get('global_role')=='admin'
if profile.get('account_status') != 'active':
    st.warning('Akses workspace menunggu persetujuan admin atau sedang ditangguhkan.')
    st.stop()

with st.expander('Buat proyek baru',expanded=False):
    with st.form('create_project'):
        new_name=st.text_input('Nama proyek',max_chars=120)
        new_code=st.text_input('Kode proyek (opsional)',max_chars=45)
        new_desc=st.text_area('Deskripsi (opsional)',max_chars=1500)
        clicked=st.form_submit_button('Simpan proyek',type='primary')
    if clicked:
        try:
            create_project(client,uid,new_name,new_code,new_desc)
            st.success('Proyek tersimpan.'); st.rerun()
        except ValueError as exc:
            st.error(str(exc))
        except Exception:
            st.error('Gagal membuat proyek. Periksa koneksi, login, dan kebijakan RLS.')
try: projects=list_projects(client)
except Exception:
    st.error('Proyek tidak dapat dimuat. Pastikan schema_v55.sql telah dijalankan dan RLS aktif.')
    st.stop()
if not projects:
    st.info('Belum ada proyek. Buat proyek pertama menggunakan formulir di atas.')
    st.stop()

project_map={p['id']:p for p in projects}
current=st.selectbox('Pilih proyek',options=list(project_map),
    format_func=lambda k: f"{project_map[k]['name']} — {project_map[k].get('code') or 'tanpa kode'}")
p=project_map[current]
st.caption('Pemilik proyek: '+('akun kamu' if p['owner_id']==uid else 'pengguna lain / proyek dibagikan'))

cloud,membertab,reporttab,audittab=st.tabs(['Data & Snapshot','Anggota Proyek','Laporan & Persetujuan','Audit Log'])

with cloud:
    st.subheader('Data yang tersimpan')
    st.caption('Setiap penyimpanan menjadi snapshot baru (append-only). Data sebelumnya tidak ditimpa.')
    try: snapshots=list_snapshots(client,current)
    except Exception:
        st.error('Snapshot tidak dapat dibaca.'); snapshots=[]
    if snapshots:
        st.dataframe([{'ID':s['id'][:8],'Dibuat':s['created_at'],
            'Target MPa':s['target_mpa'],'SHA-256':s['csv_sha256'][:16]} for s in snapshots],
            use_container_width=True,hide_index=True)
        choice=st.selectbox('Pilih snapshot',options=[s['id'] for s in snapshots],
            format_func=lambda x: f'{x[:8]} · {next(s for s in snapshots if s["id"]==x)["created_at"]}')
        if st.button('Muat data snapshot ke Service',key='load_cloud_snapshot'):
            try:
                snap=load_snapshot(client,choice)
                if not snap: raise ValueError('Snapshot tidak ditemukan')
                # Revalidate before making the CSV active.
                from concretelab.cloud import read_cloud_snapshot
                read_cloud_snapshot(snap['csv_text'],snap['target_mpa'])
                st.session_state['k4_uploaded_bytes']=snap['csv_text'].encode('utf-8')
                st.session_state['k4_uploaded_name']=f"snapshot_{choice[:8]}.csv"
                st.session_state['k4_restored_target']=float(snap['target_mpa'])
                st.session_state['k4_restored_name']=p['name']
                st.session_state['k4_restored_owner']=getattr(user,'email','') or 'Pengguna'
                st.session_state.pop('k4_saved_edit_csv',None)
                st.session_state.pop('k4_active_fingerprint',None)
                st.switch_page('app_pages/service.py')
            except Exception:
                st.error('Gagal memuat snapshot. Periksa data atau izin baca.')
    else: st.caption('Proyek belum mempunyai snapshot data.')
    st.divider()
    active=st.session_state.get('k4_saved_edit_csv') or st.session_state.get('k4_uploaded_bytes')
    if active is None:
        st.info('Belum ada CSV aktif pada sesi. Unggah CSV di halaman Service terlebih dahulu.')
    else:
        st.success('Ada CSV aktif dalam sesi. Tekan simpan hanya jika yakin data boleh disimpan ke cloud.')
        with st.form('save_snapshot'):
            target=st.number_input('Target mutu (MPa) untuk snapshot',min_value=1.0,max_value=150.0,value=float(st.session_state.get('k4_restored_target',30.0)))
            note=st.text_input('Catatan versi',max_chars=500)
            confirm=st.checkbox('Saya memiliki izin menyimpan data ini ke cloud.')
            save=st.form_submit_button('Simpan Snapshot CSV',type='primary')
        if save:
            if not confirm: st.error('Konfirmasi penggunaan data cloud terlebih dahulu.')
            else:
                try:
                    _,count=save_snapshot(client,current,uid,active,target,note)
                    st.success(f'{count} benda uji tersimpan sebagai versi baru.'); st.rerun()
                except ValueError as exc: st.error(str(exc))
                except Exception: st.error('Gagal menyimpan: periksa validitas CSV, akses proyek, dan RLS.')

with membertab:
    st.subheader('Anggota Proyek')
    st.caption('Peran berlaku pada proyek ini saja, bukan hak Admin global.')
    try: members=member_list(client,current)
    except Exception: members=[]; st.warning('Daftar anggota belum dapat dimuat.')
    if members: st.dataframe(members,use_container_width=True,hide_index=True)
    can_manage=(is_admin or p['owner_id']==uid or any(m['user_id']==uid and m['project_role']=='supervisor' for m in members))
    if can_manage:
        with st.form('project_member'):
            member_uuid=st.text_input('UUID pengguna yang sudah terdaftar')
            role=st.selectbox('Peran',('viewer','technician','supervisor'))
            do_add=st.form_submit_button('Tambahkan / Ubah anggota')
        if do_add:
            try:
                if member_uuid.strip()==p['owner_id']: raise ValueError('Pemilik tidak perlu dimasukkan ulang.')
                add_member(client,current,member_uuid.strip(),role)
                st.success('Izin anggota diperbarui.');st.rerun()
            except Exception: st.error('Tidak dapat mengubah anggota. Periksa UUID dan hak akses proyek.')
        if members:
            with st.expander('Cabut akses anggota'):
                del_uuid=st.selectbox('Anggota',options=[m['user_id'] for m in members],key='k4_delete_member')
                if st.button('Cabut akses pengguna'):
                    try:delete_member(client,current,del_uuid);st.success('Akses dicabut.');st.rerun()
                    except Exception:st.error('Tidak dapat mencabut akses.')
    else: st.caption('Hanya pemilik, supervisor proyek, atau Admin dapat mengatur anggota.')

with reporttab:
    st.subheader('Alur laporan')
    st.caption('Laporan disimpan sebagai METADATA revisi dan snapshot; PDF dapat dibuat ulang dari data. '
               'Persetujuan di sini adalah review internal proyek, bukan tanda tangan profesi.')
    try:
        snapshots=list_snapshots(client,current)
        reports=list_reports(client,current)
    except Exception:
        st.error('Data laporan tidak tersedia.'); snapshots=[];reports=[]
    if snapshots:
        with st.form('new_cloud_report'):
            snapshot_id=st.selectbox('Snapshot sumber laporan',options=[s['id'] for s in snapshots],
                format_func=lambda sid: sid[:8])
            new_click=st.form_submit_button('Buat draft laporan baru')
        if new_click:
            try:
                new_report(client,current,snapshot_id);st.success('Draft laporan dibuat.');st.rerun()
            except Exception: st.error('Tidak bisa membuat draft. Pastikan kamu memiliki akses pengeditan.')
    if reports:
        st.dataframe([{'Revisi':r['revision'],'ID':r['id'][:8], 'Status':r['status'],
            'Dibuat':r['created_at'],'Komentar':r['review_note']} for r in reports],
            use_container_width=True,hide_index=True)
        rmap={r['id']:r for r in reports}
        report_id=st.selectbox('Pilih laporan',list(rmap),format_func=lambda k:
            f"Rev {rmap[k]['revision']} / {rmap[k]['status']} / {k[:8]}")
        r=rmap[report_id]
        if r['status'] in ('draft','needs_revision') and r['author_id']==uid:
            if st.button('Ajukan untuk pemeriksaan'):
                try: submit_report(client,report_id);st.success('Laporan diajukan.');st.rerun()
                except Exception: st.error('Tidak dapat mengajukan laporan.')
        can_review = (is_admin or p['owner_id']==uid or any(m['user_id']==uid and m['project_role']=='supervisor' for m in members))
        if r['status']=='submitted' and can_review and r['author_id']!=uid:
            with st.form('review_cloud_report'):
                decision=st.selectbox('Keputusan',('approved','needs_revision','rejected'))
                comments=st.text_area('Catatan review (wajib jika perlu revisi atau ditolak)',max_chars=1500)
                do_review=st.form_submit_button('Simpan keputusan')
            if do_review:
                try:review_report(client,report_id,decision,comments);st.success('Keputusan disimpan.');st.rerun()
                except Exception:st.error('Gagal menyimpan review: periksa izin dan kelengkapan catatan.')
        if r['status']=='approved' and r.get('public_token'):
            st.success('Laporan telah disetujui pada alur internal proyek.')
            # Warning: only non-sensitive public metadata is exposed by QR.
            try:
                base_url=st.secrets.get('public_base_url','')
                if base_url:
                    url=verify_url(base_url,r['public_token'])
                    st.code(url,language=None)
                    snap=next((s for s in snapshots if s['id']==r['snapshot_id']),None)
                    if snap:
                        label=print_verification_label(url,report_id,snap['csv_sha256'])
                        st.download_button('Unduh lembar QR verifikasi',label,
                            file_name=f"verifikasi_{report_id[:8]}.pdf",mime='application/pdf')
                else:
                    st.info('Atur public_base_url di Streamlit Secrets untuk mengaktifkan tautan QR publik.')
            except Exception:
                st.warning('URL verifikasi belum dapat dibuat. Periksa public_base_url.')
    else: st.caption('Belum ada laporan yang dibuat.')

with audittab:
    st.subheader('Audit Log')
    st.caption('Perubahan snapshot dan status laporan dicatat melalui trigger database.')
    try:
        logs=(client.table('k4_audit_events').select('created_at,actor_id,event,entity_id')
            .eq('project_id',current).order('created_at',desc=True).limit(100).execute().data or [])
        if logs:st.dataframe(logs,use_container_width=True,hide_index=True)
        else:st.info('Belum ada peristiwa atau kamu tidak mempunyai izin melihat audit.')
    except Exception:
        st.warning('Audit hanya tersedia untuk pemilik/supervisor proyek atau Admin.')
