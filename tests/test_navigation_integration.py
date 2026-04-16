from components import navigation


class FakeStreamlit:
    def __init__(self):
        self.session_state = {}
        self.rerun_called = False

    def tabs(self, labels, key=None):
        if key and key not in self.session_state:
            self.session_state[key] = self.session_state.get("visual_tabs", 0)
        return [None] * len(labels)

    def markdown(self, *args, **kwargs):
        pass

    def rerun(self):
        self.rerun_called = True


def test_select_each_tab_updates_active(monkeypatch):
    fake = FakeStreamlit()
    monkeypatch.setattr(navigation, "st", fake)

    # initialize active page to overview
    fake.session_state["active_page"] = "overview"
    fake.session_state["active_tab"] = navigation._label_for("overview")

    for idx, (pid, label) in enumerate(navigation.NAV_OPTIONS):
        fake.session_state["visual_tabs"] = idx
        fake.rerun_called = False
        before_active = fake.session_state.get("active_page")
        active = navigation.render_main_navigation()
        assert fake.session_state["active_page"] == pid
        assert active == pid
        # rerun is called only when visual selection differs from current active page
        assert fake.rerun_called is (before_active != pid)
