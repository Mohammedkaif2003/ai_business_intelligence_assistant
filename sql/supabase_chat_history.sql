create extension if not exists "pgcrypto";

create table if not exists public.chat_history (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  dataset_key text,
  query text,
  ai_response text,
  insight text,
  summary jsonb not null default '[]'::jsonb,
  intent text,
  confidence double precision,
  source_columns jsonb not null default '[]'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_chat_history_user_created_at
  on public.chat_history(user_id, created_at desc);

alter table public.chat_history enable row level security;

drop policy if exists "users_can_read_own_chat_history" on public.chat_history;
create policy "users_can_read_own_chat_history"
  on public.chat_history
  for select
  using (auth.uid() = user_id);

drop policy if exists "users_can_insert_own_chat_history" on public.chat_history;
create policy "users_can_insert_own_chat_history"
  on public.chat_history
  for insert
  with check (auth.uid() = user_id);
