import doitfilemappers.filemappers as fm

import mock

def get_path_mock(name=""):
    p = mock.MagicMock()
    p.is_file.return_value = True
    p.is_symlink.return_value = False 
    p.__str__.return_value = name
    return p

@mock.patch('doitfilemappers.filemappers.pathlib.Path.glob')
def test_identitymapper_expands_glob(mock_glob):
    mapper = fm.IdentityMapper("*.foo")
    m = mapper.get_map()
    mock_glob.assert_called_with("*.foo")

@mock.patch('doitfilemappers.filemappers.pathlib.Path.glob')
def test_identitymapper_input_equals_output(mock_glob):
    p1 = get_path_mock()
    p2 = get_path_mock()
    mock_glob.return_value = [p1, p2]
    mapper = fm.IdentityMapper("*.foo")
    m = mapper.get_map()
    assert m == [(p1, p1), (p2, p2)]

@mock.patch('doitfilemappers.filemappers.pathlib.Path.glob')
def test_identitymapper_get_task_returns_targets_and_callable(mock_glob):
    p1 = get_path_mock("one.foo")
    p2 = get_path_mock("two.foo")
    mock_glob.return_value = [p1, p2]
    mapper = fm.IdentityMapper("*.foo")
    t = mapper.get_task()
    assert t["targets"] == ["one.foo", "two.foo"]
    assert hasattr(t["action"], "__call__")

@mock.patch('doitfilemappers.filemappers.pathlib.Path.glob')
def test_identitymapper_action_is_called_for_each_target(mock_glob):
    p1 = get_path_mock("one.foo")
    p2 = get_path_mock("two.foo")
    mock_glob.return_value = [p1, p2]
    custom_callback = mock.Mock(return_value=True)
    mapper = fm.IdentityMapper("*.foo", custom_callback)
    a = mapper.get_action()
    assert a(["one.bar"]) # targets are ignored
    expected = [mock.call(p1, p1), mock.call(p2, p2)]
    assert custom_callback.call_args_list == expected

@mock.patch('doitfilemappers.filemappers.pathlib.Path.glob')
def test_regexmapper_replaces_placeholders(mock_glob):
    p1 = get_path_mock("one.foo")
    p2 = get_path_mock("two.foo")
    mock_glob.return_value = [p1, p2]
    mapper = fm.RegexMapper("*.foo", None, search=r"(.*)\.foo$", replace=r"\1.bar")
    t = mapper.get_task()
    assert t["targets"] == ["one.bar", "two.bar"]
    assert t["file_dep"] == ["one.foo", "two.foo"]

@mock.patch('doitfilemappers.filemappers.pathlib.Path.glob')
def test_regexmapper_ignores_nonmatching(mock_glob):
    p1 = get_path_mock("one.foo")
    p2 = get_path_mock("two.baz")
    mock_glob.return_value = [p1, p2]
    mapper = fm.RegexMapper(search=r"(.*)\.foo$", replace=r"\1.bar", ignore_nonmatching=True)
    t = mapper.get_task()
    assert t["targets"] == ["one.bar"]
    assert t["file_dep"] == ["one.foo"]



# TODO test dir param
