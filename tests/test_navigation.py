from components import navigation


class FakeStreamlit:
    def __init__(self):
        # mimic streamlit.session_state as a dict
        self.session_state = {}
        self.rerun_called = False
        self.markdown_calls = []

    def tabs(self, labels, key=None):
        # When called with a key, ensure a session key exists and return placeholders
        if key:
            # If not present, initialize to current active_tab index if available
            if key not in self.session_state:
                self.session_state[key] = self.session_state.get("visual_tabs", 0)
        return [None] * len(labels)

    def markdown(self, *args, **kwargs):
        self.markdown_calls.append((args, kwargs))

    def rerun(self):
        self.rerun_called = True


def test_initial_navigation_sets_defaults(monkeypatch):
    fake = FakeStreamlit()
    # inject fake streamlit into the module
    monkeypatch.setattr(navigation, "st", fake)

    # Ensure clean state
    if "active_page" in fake.session_state:
        del fake.session_state["active_page"]
    if "visual_tabs" in fake.session_state:
        del fake.session_state["visual_tabs"]

    active = navigation.render_main_navigation()

    # active page should be in nav options and stored in session state
    assert active in [p for p, _ in navigation.NAV_OPTIONS]
    assert fake.session_state.get("active_page") == active
    # visual_tabs should be initialized
    assert "visual_tabs" in fake.session_state


def test_visual_tab_selection_updates_active_page(monkeypatch):
    fake = FakeStreamlit()
    monkeypatch.setattr(navigation, "st", fake)

    # start with active page = overview (index 0)
    fake.session_state["active_page"] = "overview"
    fake.session_state["active_tab"] = navigation._label_for("overview")
    fake.session_state["visual_tabs"] = 0

    # simulate user clicking the 2nd tab (index 1 -> chat)
    fake.session_state["visual_tabs"] = 1

    active = navigation.render_main_navigation()

    # should have updated active_page to 'chat' and called rerun
    assert fake.session_state.get("active_page") == "chat"
    assert fake.rerun_called is True
    assert active == fake.session_state.get("active_page")


def test_navigation_target_page_overrides(monkeypatch):
    fake = FakeStreamlit()
    monkeypatch.setattr(navigation, "st", fake)

    # programmatically request navigation to 'reports'
    fake.session_state["navigation_target_page"] = "reports"

    active = navigation.render_main_navigation()

    assert fake.session_state.get("active_page") == "reports"
    # visual_tabs index should match reports
    idx = next(i for i, (pid, _) in enumerate(navigation.NAV_OPTIONS) if pid == "reports")
    assert fake.session_state.get("visual_tabs") == idx
    assert active == "reports"
