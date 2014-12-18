import doitfilemappers.filemappers as fm

import mock
import pytest
import pathlib

def get_path_mock(name=""):
    p = mock.MagicMock(spec=pathlib.Path)
    p.is_file.return_value = True
    p.is_symlink.return_value = False 
    p.__str__.return_value = name
    return p

def get_path_open_mock(name=""):
    p = mock.MagicMock(spec=pathlib.Path)
    p.__str__.return_value = name
    p_file = mock.MagicMock(spec=file)
    p.open.return_value = p_file
    return p

# The IdentityMapper is used for many tests of BaseMapper functionality

@mock.patch('doitfilemappers.filemappers.pathlib.Path.glob')
def test_identitymapper_expands_glob(mock_glob):
    mapper = fm.IdentityMapper("*.foo")
    m = mapper.get_map()
    mock_glob.assert_called_with("*.foo")

def test_identitymapper_get_task_fails_if_map_is_empty():
    mapper = fm.IdentityMapper("*.foo")
    with pytest.raises(RuntimeError) as e:
        mapper.get_task()
    assert "empty" in e.value.message

def test_identitymapper_empty_map_default_action_returns_true():
    mapper = fm.IdentityMapper("*.foo", allow_empty_map=True)
    task = mapper.get_task()
    assert task["actions"][0]([])

def test_identitymapper_get_task_returns_additional_parameters():
    mapper = fm.IdentityMapper("*.foo", allow_empty_map=True)
    task = mapper.get_task({"title":"Test dummy"})
    assert "title" in task
    assert task["title"] == "Test dummy"

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
    assert set(t["targets"]) == set(["one.foo", "two.foo"])
    assert hasattr(t["actions"][0], "__call__")

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


@mock.patch('doitfilemappers.filemappers.pathlib.Path.glob')
def test_globmapper_replaces_asterisk(mock_glob):
    p1 = get_path_mock("one.foo")
    p2 = get_path_mock("two.foo")
    mock_glob.return_value = [p1, p2]
    mapper = fm.GlobMapper("*.foo", None, "*.bar")
    t = mapper.get_task()
    assert t["targets"] == ["one.bar", "two.bar"]
    assert t["file_dep"] == ["one.foo", "two.foo"]

@mock.patch('doitfilemappers.filemappers.pathlib.Path.glob')
def test_globmapper_uses_search_pattern_if_provided(mock_glob):
    p1 = get_path_mock("one.foo")
    p2 = get_path_mock("two.foo")
    mock_glob.return_value = [p1, p2]
    mapper = fm.GlobMapper("**/*.foo", None, "*.bar", "*.foo")
    t = mapper.get_task()
    assert t["targets"] == ["one.bar", "two.bar"]
    assert t["file_dep"] == ["one.foo", "two.foo"]

def test_globmapper_raises_exception_when_pattern_contains_more_than_one_asterisk():
    with pytest.raises(RuntimeError) as e:
        fm.GlobMapper("**/*.foo", None, "*.bar")
    assert "asterisk" in e.value.message

def test_globmapper_raises_exception_when_pattern_contains_no_asterisk():
    with pytest.raises(RuntimeError) as e:
        fm.GlobMapper("one.foo", None, "*.bar")
    assert "asterisk" in e.value.message

@mock.patch('doitfilemappers.filemappers.pathlib.Path.glob')
def test_mergemapper_returns_the_same_target_for_all_sources(mock_glob):
    p1 = get_path_mock("one.foo")
    p2 = get_path_mock("two.foo")
    tgt = get_path_mock("target.dummy")
    mock_glob.return_value = [p1, p2]
    mapper = fm.MergeMapper("*.foo", None, tgt)
    t = mapper.get_task()
    assert t["targets"] == ["target.dummy"]
    assert t["file_dep"] == ["one.foo", "two.foo"]


@mock.patch('doitfilemappers.filemappers.pathlib.Path.glob')
def test_mergemapper_accepts_string_as_target_name(mock_glob):
    p1 = get_path_mock("one.foo")
    p2 = get_path_mock("two.foo")
    mock_glob.return_value = [p1, p2]
    mapper = fm.MergeMapper("*.foo", None, "target.dummy")
    t = mapper.get_task()
    assert t["targets"] == ["target.dummy"]
    assert t["file_dep"] == ["one.foo", "two.foo"]

def test_mergemapper_raises_exception_without_target():
    with pytest.raises(RuntimeError) as e:
        mapper = fm.MergeMapper("*.foo")
        mapper.get_map()
    assert "Target" in e.value.message

def test_file_handle_decorator_opens_files():
    @fm.open_files
    def check(_in, _out):
        pass
    p_in = get_path_open_mock()
    p_out = get_path_open_mock()
    check(p_in, p_out)
    p_in.open.assert_called_with("r")
    p_out.open.assert_called_with("w")

def test_track_file_count_tracks_calls():
    @fm.track_file_count
    def check(_in, _out, file_count=0):
        return file_count
    assert check(None, None) == 0
    assert check(None, None) == 1
    assert check(None, None) == 2

def test_merge_file_handle_decorator_opens_files():
    @fm.open_files_with_merge
    def check(_in, _out):
        pass
    p_in = get_path_open_mock("in")
    p_out1 = get_path_open_mock("out")
    p_out2 = get_path_open_mock("out")
    check(p_in, p_out1)
    p_out1.open.assert_called_once_with("w")
    check(p_in, p_out2)
    p_out2.open.assert_called_once_with("a")
