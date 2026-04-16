import pandas as pd

import modules.dataset_activation as dataset_activation


class _DummyStreamlit:
    def __init__(self):
        self.session_state = {}


def test_activate_dataset_sets_state_and_returns_true(monkeypatch):
    dummy = _DummyStreamlit()
    monkeypatch.setattr(dataset_activation, "st", dummy)

    df = pd.DataFrame({"Revenue": [100, 120]})
    activated = dataset_activation.activate_dataset("sales.csv", df)

    assert activated is True
    assert dummy.session_state["active_dataset_key"] == "sales.csv"
    assert dummy.session_state["dataset_name"] == "sales.csv"
    assert "schema" in dummy.session_state


def test_activate_dataset_returns_false_for_same_active_dataset(monkeypatch):
    dummy = _DummyStreamlit()
    existing_df = pd.DataFrame({"Revenue": [10]})
    dummy.session_state = {
        "active_dataset_key": "sales.csv",
        "df": existing_df,
    }
    monkeypatch.setattr(dataset_activation, "st", dummy)

    activated = dataset_activation.activate_dataset("sales.csv", existing_df)

    assert activated is False


def test_activate_dataset_updates_when_dataset_changes(monkeypatch):
    dummy = _DummyStreamlit()
    dummy.session_state = {
        "active_dataset_key": "sales.csv",
        "df": pd.DataFrame({"Revenue": [10]}),
    }
    monkeypatch.setattr(dataset_activation, "st", dummy)

    df_new = pd.DataFrame({"Profit": [5, 7]})
    activated = dataset_activation.activate_dataset("finance.csv", df_new)

    assert activated is True
    assert dummy.session_state["active_dataset_key"] == "finance.csv"
    assert dummy.session_state["dataset_name"] == "finance.csv"


def test_activate_dataset_returns_false_when_dataframe_none(monkeypatch):
    dummy = _DummyStreamlit()
    monkeypatch.setattr(dataset_activation, "st", dummy)

    activated = dataset_activation.activate_dataset("sales.csv", None)

    assert activated is False


def test_activate_dataset_returns_false_when_dataframe_empty(monkeypatch):
    dummy = _DummyStreamlit()
    monkeypatch.setattr(dataset_activation, "st", dummy)

    empty_df = pd.DataFrame(columns=["Revenue"])
    activated = dataset_activation.activate_dataset("sales.csv", empty_df)

    assert activated is False
