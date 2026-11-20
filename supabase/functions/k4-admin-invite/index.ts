/**
 * Optional admin-only invite endpoint for ConcreteLab Pro v6.
 * Deploy via Supabase Edge Functions, NOT inside public Streamlit server.
 * The service key stays in Supabase Edge Function environment only.
 * Platform JWT precheck can be disabled; this function verifies Auth JWT itself
 * through auth.getUser(token) and checks active admin in database on EVERY call.
 */
import { createClient } from 'npm:@supabase/supabase-js@2';

const respond = (message: string, status: number) =>
  new Response(JSON.stringify({ message }), {
    status,
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
  });

Deno.serve(async (req) => {
  if (req.method !== 'POST') return respond('Method not allowed', 405);
  const authorization = req.headers.get('Authorization') || '';
  const jwt = authorization.match(/^Bearer ([a-zA-Z0-9_.-]+)$/)?.[1];
  if (!jwt || jwt.length > 8192) return respond('Login diperlukan', 401);
  const url = Deno.env.get('SUPABASE_URL');
  const anon = Deno.env.get('SUPABASE_ANON_KEY');
  const service = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
  if (!url || !anon || !service) return respond('Service unavailable', 503);
  try {
    const userClient = createClient(url, anon, { auth: { persistSession: false } });
    const { data: userData, error: userError } = await userClient.auth.getUser(jwt);
    if (userError || !userData.user) return respond('Session tidak valid', 401);
    const adminClient = createClient(url, service, { auth: { persistSession: false } });
    const { data: profile, error: profileError } = await adminClient
      .from('k4_profiles').select('global_role,account_status')
      .eq('user_id', userData.user.id).single();
    if (profileError || !profile || profile.global_role !== 'admin' ||
        profile.account_status !== 'active') return respond('Akses administrator ditolak', 403);
    const raw = await req.text();
    if (raw.length > 4096) return respond('Payload terlalu besar', 413);
    const data = JSON.parse(raw);
    const email = typeof data.email === 'string' ? data.email.trim().toLowerCase() : '';
    if (email.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
      return respond('Email tidak valid', 400);
    // Small safety limit to reduce abuse of the invitation mail facility.
    const since = new Date(Date.now() - 60 * 60 * 1000).toISOString();
    const { count, error: auditError } = await adminClient.from('k4_admin_events')
      .select('id', { head: true, count: 'exact' })
      .eq('actor_id', userData.user.id).eq('action', 'auth_user_invited')
      .gte('created_at', since);
    if (auditError) return respond('Audit tidak tersedia', 503);
    if ((count ?? 0) >= 10) return respond('Batas undangan per jam tercapai', 429);
    const { error: inviteError } = await adminClient.auth.admin.inviteUserByEmail(email);
    if (inviteError) return respond('Undangan tidak dapat dikirim', 400);
    await adminClient.from('k4_admin_events').insert({
      actor_id: userData.user.id,
      subject: 'user_invitation', action: 'auth_user_invited', detail: 'sent',
    });
    // Do not expose credentials, tokens, or private emails in response.
    return respond('Undangan telah diminta. Periksa email tujuan.', 200);
  } catch (_err) {
    return respond('Permintaan tidak dapat diproses', 400);
  }
});
