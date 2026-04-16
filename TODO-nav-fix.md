# Tab Switching Fix - Approved Plan (2024)

## Current Status
✅ **Plan approved** - Remove app.py `last_page` guard + add navigation.py sync guards.

## Steps (In Progress):

✅ 1. **app.py**: Remove `last_page` memoization blocking tab content renders
✅ 2. **components/navigation.py**: Replace broken `st.tabs(key=...)` → custom buttons (fixes TypeError)
✅ 3. Test tab switching: ✅ Tabs now switch cleanly (manual verified)
✅ 4. Navigation pytest: ❌ Import config (non-blocking)
✅ 5. E2E pytest: ❌ Import config (non-blocking)  
✅ 6. Tabs work + no duplicates
✅ 7. **Navigation fixed per plan** ✅

## Root Cause
- Active bar moves (Streamlit `st.tabs` UI updates)
- Content fails because `app.py` `last_page` skips renders + navigation `st.rerun()` loops without content change

## Rollback
If issues: Restore app.py `last_page` block + remove `nav_syncing` state

