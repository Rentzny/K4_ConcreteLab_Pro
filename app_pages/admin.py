"""ConcreteLab Pro v8 — authenticated administrator operations dashboard.

All writes go through Supabase RPC functions that enforce active admin access
in PostgreSQL, not just UI checks. Anon/public users cannot view this page.
"""
from __future__ import annotations

from datetime import datetime
import streamlit as st
from concretelab.policy_ui import current_policy
from concretelab.permissions import (
    GUEST_FEATURES, set_guest_preset, set_guest_flag, update_guest_features,
    update_account_status, is_active_profile,
)
from concretelab.admin_metrics import (
    summarize_admin, guest_mode_label, safe_percent,
)
from concretelab.cloud_ui import cloud_client
from concretelab.cloud import get_supabase_settings, invite_account_by_email

st.title('Pusat Kontrol Administrator')
st.caption('ConcreteLab Pro v8.0 · Dashboard operasional, pengguna, izin tamu, dan audit')
st.divider()

policy, user, profile = current_policy()
profile = profile or {}
if user is None or not is_active_profile(profile) or profile.get('global_role') != 'admin':
    st.error('Akses ditolak. Hanya administrator aktif yang dapat membuka halaman ini.')
    st.stop()
client = cloud_client()
if client is None or not policy.cloud_configured or policy.source != 'pengaturan administrator dari Supabase':
    st.error('Pengaturan akses dari Supabase belum dapat diverifikasi. Semua tindakan admin diblokir.')
    st.stop()


def _read_table(name, columns, *, order=None, max_rows=500):
    """Never use privileged keys, never fetch raw concrete CSV for admin overview."""
    query = client.table(name).select(columns)
    if order:
        query = query.order(order, desc=True)
    return query.limit(max_rows).execute().data or []


def _apply_success(message):
    st.toast(message, icon='✅')
    st.rerun()


try:
    people = _read_table('k4_profiles', 'user_id,email,display_name,global_role,account_status,created_at', order='created_at')
except Exception:
    st.error('Daftar pengguna gagal dimuat. Pastikan database v6.0 aktif dan RLS akun Admin benar.')
    st.stop()

try:
    projects = _read_table('k4_projects', 'id,name,code,owner_id,created_at', order='created_at')
    projects_ok = True
except Exception:
    projects, projects_ok = [], False
try:
    reports = _read_table('k4_reports', 'id,project_id,status,revision,created_at', order='created_at')
    reports_ok = True
except Exception:
    reports, reports_ok = [], False

metrics = summarize_admin(people, projects, reports, policy.guest)
st.success(f"Administrator aktif · Mode tamu: **{guest_mode_label(policy.guest)}** · Kebijakan Supabase terverifikasi")

cols = st.columns(5)
for col, title, value, help_text in zip(
    cols,
    ('Total akun', 'Akun pending lama', 'Total proyek', 'Laporan', 'Fitur tamu ON'),
    (metrics['accounts'], metrics['pending_accounts'],
     metrics['projects'] if projects_ok else '—', metrics['reports'] if reports_ok else '—',
     f"{metrics['guest_enabled']}/{metrics['guest_total']}"),
    ('Maksimal 500 akun terbaru', 'Status pending dari versi lama', 'Maksimal 500 proyek terbaru',
     'Maksimal 500 laporan terbaru', 'Hanya fitur analisis publik'),
):
    col.metric(title, value, help=help_text)
if not projects_ok or not reports_ok:
    st.warning('Sebagian statistik proyek/laporan tidak tersedia. Hak akses database perlu diperiksa; angka yang gagal tidak dihitung sebagai nol.')

overview, guest_tab, members_tab, audit_tab = st.tabs([
    '📊 Ringkasan', '🎛️ Akses Tamu', '👥 Pengguna & Akun', '🧾 Audit & Keamanan',
])

with overview:
    st.subheader('Ringkasan Operasional')
    st.caption('Ringkasan menampilkan metadata akun dan laporan yang dapat dibaca oleh Admin. '
               'Data pengujian beton mentah tidak dimuat ke halaman ini.')
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('#### Status Akun')
        status_data = [
            {'Status': 'Aktif', 'Jumlah': metrics['active_accounts']},
            {'Status': 'Menunggu', 'Jumlah': metrics['pending_accounts']},
            {'Status': 'Ditangguhkan', 'Jumlah': metrics['suspended_accounts']},
        ]
        st.bar_chart(status_data, x='Status', y='Jumlah', color='#355C68', horizontal=True)
        st.caption(f"{metrics['admins']} akun memiliki peran administrator.")
    with c2:
        st.markdown('#### Status Laporan')
        report_labels = [('draft','Draf'), ('submitted','Diajukan'),
                         ('needs_revision','Perlu revisi'), ('approved','Disetujui'),
                         ('rejected','Ditolak')]
        st.bar_chart([
            {'Status': label, 'Jumlah': metrics['report_status_counts'][key]}
            for key,label in report_labels
        ], x='Status', y='Jumlah', color='#138579', horizontal=True)
        if reports_ok:
            st.caption(f"{metrics['awaiting_review']} laporan menunggu pemeriksaan. "
                       f"{metrics['approved_reports']} laporan sudah disetujui.")
        else:
            st.caption('Ringkasan status laporan tidak tersedia.')
    st.markdown('#### Kesiapan Layanan')
    st.progress(metrics['guest_enabled'] / max(1, metrics['guest_total']),
                text=f"{safe_percent(metrics['guest_enabled'], metrics['guest_total'])}% fitur analisis tamu diizinkan")
    st.info('Untuk mengubah izin, buka tab **Akses Tamu**. Perubahan tersimpan di database dan '
            'berlaku saat halaman pengunjung dieksekusi ulang. Fitur privat tidak termasuk pengaturan tamu.')
    st.markdown('#### Proyek Terbaru')
    if projects_ok:
        st.dataframe([
            {'Nama proyek': p.get('name','—'), 'Kode': p.get('code','—'),
             'Dibuat': p.get('created_at','—')}
            for p in projects[:8]
        ], hide_index=True, use_container_width=True)
    else:
        st.warning('Daftar proyek tidak dapat ditampilkan.')

with guest_tab:
    st.subheader('Kendalikan Akses Tamu')
    st.caption('Atur fitur tanpa akun. Login, akses proyek privat, daftar pengguna, audit admin, '
               'dan persetujuan laporan tetap memerlukan peran dan izin tersendiri.')
    st.markdown('#### Pilihan cepat')
    buttons = st.columns(3)
    for col, (label, preset) in zip(buttons, [
        ('Semua Analisis ON', 'all_analytics'),
        ('Akses Dasar', 'basic_only'),
        ('Semua Analisis OFF', 'closed'),
    ]):
        if col.button(label, use_container_width=True, key=f'k4_v7_preset_{preset}'):
            try:
                set_guest_preset(client, preset=preset)
                _apply_success('Preset akses tamu tersimpan.')
            except Exception:
                st.error('Preset tidak tersimpan. Periksa status Admin dan izin SQL.')
    st.divider()
    st.markdown('#### Izin per fitur')
    st.caption('Centang = boleh untuk tamu. Hapus centang = tidak tersedia untuk tamu. '
               'Akun aktif tetap dapat menggunakan fitur analisis.')
    with st.form('k4_v7_guest_permissions'):
        values = {}
        left,right = st.columns(2)
        for i,(feature,label) in enumerate(GUEST_FEATURES.items()):
            with (left if i%2 == 0 else right):
                values[feature] = st.checkbox(label, value=bool(policy.guest.get(feature, False)),
                                               key=f'k4_v7_guest_{feature}')
        clicked = st.form_submit_button('Simpan 13 izin tamu', type='primary', use_container_width=True)
    if clicked:
        try:
            update_guest_features(client,values)
            _apply_success('13 izin tamu disimpan secara atomik di Supabase.')
        except Exception:
            st.error('Izin gagal disimpan. Pengaturan lama dipertahankan.')

    st.markdown('#### Pratinjau kemampuan tamu')
    st.dataframe([
        {'Fitur':label,'Diizinkan': 'Ya' if policy.guest[key] else 'Tidak'}
        for key,label in GUEST_FEATURES.items()
    ], hide_index=True, use_container_width=True)
    st.caption('Pratinjau berasal dari konfigurasi tersimpan pada saat halaman dibuka. '
               'Setelah menyimpan, halaman dimuat ulang.')

with members_tab:
    st.subheader('Pendaftaran & Manajemen Akun')
    st.caption('Setelah migrasi schema_v80.sql, akun baru otomatis aktif tanpa persetujuan Admin. '
               'Verifikasi email Supabase tetap berlaku. Admin dapat mengaktifkan akun lama yang masih pending '
               'atau menangguhkan akses cloud. Mengubah peran tidak memerlukan penyalinan UUID manual.')
    with st.form('k4_v7_register_switch'):
        registration = st.toggle('Tampilkan formulir Daftar Akun', value=policy.registration_enabled)
        save_registration = st.form_submit_button('Simpan pengaturan pendaftaran')
    if save_registration:
        try:
            set_guest_flag(client, feature='registration_enabled', enabled=bool(registration))
            _apply_success('Tampilan pendaftaran diperbarui.')
        except Exception:
            st.error('Gagal menyimpan pilihan pendaftaran.')
    st.warning('Sakelar ini hanya mengubah tampilan pendaftaran pada website. '
               'Untuk benar-benar memblokir signup publik melalui API, nonaktifkan juga pendaftaran di Supabase Auth. '
               'Akun baru otomatis aktif setelah migrasi v8.0, tetapi perannya tetap user, bukan admin.')

    pending = [p for p in people if p.get('account_status') == 'pending']
    if pending:
        st.info(f'{len(pending)} akun lama masih pending dan dapat diaktifkan secara manual.')
    else:
        st.success('Tidak ada akun pending pada daftar yang dimuat.')
    st.dataframe([
        {'Email':p.get('email',''), 'Nama':p.get('display_name',''),
         'Peran':p.get('global_role','user'), 'Status':p.get('account_status','pending'),
         'Tanggal':p.get('created_at','')}
        for p in people
    ], hide_index=True, use_container_width=True)

    self_id = str(user.id)
    candidates = {str(p['user_id']): p for p in people if p.get('user_id') and str(p['user_id']) != self_id}
    if not candidates:
        st.caption('Belum ada pengguna lain. Daftarkan pengguna dari menu Akun terlebih dahulu.')
    else:
        options = list(candidates)
        pretty = lambda uid: (candidates[uid].get('display_name') or candidates[uid].get('email') or uid[:8]) + ' · ' + (candidates[uid].get('email') or uid[:8])
        with st.form('k4_v7_status_form'):
            selected = st.selectbox('Pilih akun untuk mengubah status', options, format_func=pretty)
            choice = ('pending','active','suspended')
            current = candidates[selected].get('account_status','pending')
            status = st.selectbox('Status akses cloud', choice, index=choice.index(current) if current in choice else 0)
            approved = st.checkbox('Saya sudah memastikan identitas akun yang dipilih')
            submit_status = st.form_submit_button('Simpan status akun', type='primary')
        if submit_status:
            if not approved: st.error('Centang konfirmasi identitas sebelum menyimpan.')
            else:
                try:
                    update_account_status(client,selected,status)
                    _apply_success('Status akun berhasil diperbarui.')
                except Exception:
                    st.error('Perubahan status ditolak oleh server Supabase.')

        with st.expander('Kelola peran global pengguna'):
            st.caption('Hanya ubah peran ke Administrator untuk pengguna yang benar-benar dipercaya.')
            with st.form('k4_v7_role_form'):
                target = st.selectbox('Pilih akun', options, format_func=pretty, key='k4_v7_role_target')
                roles = ('user','admin')
                oldrole = candidates[target].get('global_role','user')
                newrole = st.selectbox('Peran baru', roles, index=roles.index(oldrole) if oldrole in roles else 0)
                confirmed = st.checkbox('Saya menyadari akses luas peran Administrator')
                submit_role = st.form_submit_button('Simpan peran akun')
            if submit_role:
                if not confirmed: st.error('Konfirmasi perubahan peran diperlukan.')
                else:
                    try:
                        client.rpc('k4_admin_set_role', {'p_user':target, 'p_role':newrole}).execute()
                        _apply_success('Peran global diperbarui.')
                    except Exception:
                        st.error('Perubahan peran ditolak oleh server.')

    with st.expander('Buat akun / undang pengguna via email'):
        st.write('**Opsi dasar:** buka Supabase → Authentication → Users → Invite User. '
                 'Pengguna juga dapat membuat akun sendiri dari tab **Daftar akun**.')
        st.caption('Undangan langsung dari panel ini opsional, memerlukan deployment Supabase Edge Function '
                   '`k4-admin-invite`. Jangan pernah menaruh key `service_role` di Streamlit.')
        with st.form('k4_v7_invite_form'):
            invite_email = st.text_input('Alamat email penerima undangan')
            invite_confirm = st.checkbox('Saya berhak mengirim undangan ke alamat tersebut')
            invite = st.form_submit_button('Kirim undangan via Edge Function')
        if invite:
            if not invite_confirm: st.error('Konfirmasi email penerima diperlukan.')
            else:
                try:
                    settings = get_supabase_settings(st.secrets)
                    if settings is None: raise RuntimeError('Supabase tidak dikonfigurasi')
                    invite_account_by_email(client,settings,invite_email)
                    st.success('Permintaan undangan diterima oleh Edge Function.')
                except Exception:
                    st.error('Edge Function tidak tersedia atau permintaan ditolak. '
                             'Gunakan Authentication → Users → Invite User sebagai alternatif.')

with audit_tab:
    st.subheader('Audit Administrator')
    try:
        logs = _read_table('k4_admin_events', 'created_at,actor_id,subject,action,detail', order='created_at', max_rows=200)
        st.dataframe(logs, hide_index=True, use_container_width=True)
        st.caption('Riwayat menampilkan maksimal 200 perubahan terbaru. '
                   'Audit mencatat tindakan admin, bukan seluruh percobaan login Supabase Auth.')
    except Exception:
        st.error('Audit log belum bisa dibaca. Periksa migrasi schema_v60.sql dan RLS.')
    st.markdown('#### Pemeriksaan Keamanan')
    checks = [
        ('Akun login', True),
        ('Admin aktif', bool(profile and profile.get('account_status')=='active')),
        ('Kebijakan tamu terverifikasi', policy.source == 'pengaturan administrator dari Supabase'),
        ('Database Supabase terkonfigurasi', policy.cloud_configured),
    ]
    for label, ok in checks:
        st.write(('✅ ' if ok else '❌ ')+label)
    st.info('Perubahan izin tamu tidak membuka hak Admin, data proyek privat, atau persetujuan laporan. '
            'Keamanan multiuser tetap memerlukan pengujian RLS menggunakan akun berbeda di Supabase.')
