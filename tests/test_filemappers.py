import doitfilemappers.filemappers as fm

import mock
import pytest
import pathlib

def get_path_open_mock(name=""):
    p = mock.MagicMock(spec=pathlib.Path)
    p.__str__.return_value = name
    p_file = mock.MagicMock(spec=file)
    p.open.return_value = p_file
    return p

# The IdentityMapper is used for many tests of BaseMapper functionality

@mock.patch('doitfilemappers.filemappers.pathlib.Path.glob')
def test_identitymapper_expands_glob_in_src(mock_glob):
    mapper = fm.IdentityMapper("*.foo")
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

def test_identitymapper_input_equals_output():
    p1 = pathlib.Path()
    p2 = pathlib.Path()
    mapper = fm.IdentityMapper([p1, p2])
    m = mapper.get_map()
    assert m == [(p1, p1), (p2, p2)]

def test_identitymapper_get_task_returns_targets_and_callable():
    p1 = pathlib.Path("one.foo")
    p2 = pathlib.Path("two.foo")
    mapper = fm.IdentityMapper([p1, p2])
    t = mapper.get_task()
    assert set(t["targets"]) == set(["one.foo", "two.foo"])
    assert hasattr(t["actions"][0], "__call__")

def test_identitymapper_action_is_called_for_each_target():
    p1 = pathlib.Path("one.foo")
    p2 = pathlib.Path("two.foo")
    custom_callback = mock.Mock(return_value=True)
    mapper = fm.IdentityMapper([p1, p2], custom_callback)
    a = mapper.get_action(mapper.callback)
    assert a(["dummy"]) # we provide one dummy target, which will be ignored
    expected = [mock.call(p1, p1), mock.call(p2, p2)]
    assert custom_callback.call_args_list == expected

def test_regexmapper_replaces_placeholders():
    p1 = pathlib.Path("one.foo")
    p2 = pathlib.Path("two.foo")
    mapper = fm.RegexMapper([p1, p2], search=r"(.*)\.foo$", replace=r"\1.bar")
    t = mapper.get_task()
    assert t["targets"] == ["one.bar", "two.bar"]
    assert t["file_dep"] == ["one.foo", "two.foo"]

def test_regexmapper_ignores_nonmatching():
    p1 = pathlib.Path("one.foo")
    p2 = pathlib.Path("two.baz")
    mapper = fm.RegexMapper([p1, p2], search=r"(.*)\.foo$", replace=r"\1.bar", ignore_nonmatching=True)
    t = mapper.get_task()
    assert t["targets"] == ["one.bar"]
    assert t["file_dep"] == ["one.foo"]

def test_regexmapper_generates_cmd_actions_from_string_callback():
    p1 = pathlib.Path("one.foo")
    p2 = pathlib.Path("two.foo")
    mapper = fm.RegexMapper([p1, p2], callback="mv %(source)s %(target)s", search=r"(.*)\.foo$", replace=r"\1.bar")
    t = mapper.get_task()
    assert t["actions"] == ["mv one.foo one.bar", "mv two.foo two.bar"]

@mock.patch('doitfilemappers.filemappers.pathlib.Path.glob')
def test_globmapper_replaces_asterisk(mock_glob):
    p1 = pathlib.Path("one.foo")
    p2 = pathlib.Path("two.foo")
    mock_glob.return_value = [p1, p2]
    mapper = fm.GlobMapper("*.foo", None, "*.bar")
    t = mapper.get_task()
    assert t["targets"] == ["one.bar", "two.bar"]
    assert t["file_dep"] == ["one.foo", "two.foo"]

def test_globmapper_uses_search_pattern_if_provided():
    p1 = pathlib.Path("one.foo")
    p2 = pathlib.Path("two.foo")
    mapper = fm.GlobMapper([p1, p2], pattern="*.foo", replace="*.bar")
    t = mapper.get_task()
    assert t["targets"] == ["one.bar", "two.bar"]
    assert t["file_dep"] == ["one.foo", "two.foo"]

def test_globmapper_uses_in_path_param():
    p1 = pathlib.Path("one.foo")
    p2 = pathlib.Path("two.foo")
    mapper = fm.GlobMapper([p1, p2], pattern="*.foo", replace="*.bar", in_path="subdir")
    t = mapper.get_task()
    assert t["targets"] == ["subdir/one.bar", "subdir/two.bar"]
    assert t["file_dep"] == ["subdir/one.foo", "subdir/two.foo"]

def test_globmapper_raises_exception_when_pattern_contains_more_than_one_asterisk():
    with pytest.raises(RuntimeError) as e:
        fm.GlobMapper("**/*.foo", replace="*.bar")
    assert "asterisk" in e.value.message
    with pytest.raises(RuntimeError) as e:
        fm.GlobMapper(replace="*.bar", pattern="**/*.foo")
    assert "asterisk" in e.value.message

def test_globmapper_raises_exception_when_pattern_contains_no_asterisk():
    with pytest.raises(RuntimeError) as e:
        fm.GlobMapper("one.foo", None, "*.bar")
    assert "asterisk" in e.value.message

def test_mergemapper_returns_the_same_target_for_all_sources():
    p1 = pathlib.Path("one.foo")
    p2 = pathlib.Path("two.foo")
    tgt = pathlib.Path("target.dummy")
    mapper = fm.MergeMapper([p1, p2], target=tgt)
    t = mapper.get_task()
    assert t["targets"] == ["target.dummy"]
    assert t["file_dep"] == ["one.foo", "two.foo"]

def test_mergemapper_accepts_string_as_target_name():
    p1 = pathlib.Path("one.foo")
    p2 = pathlib.Path("two.foo")
    p1 = pathlib.Path("one.foo")
    p2 = pathlib.Path("two.foo")
    mapper = fm.MergeMapper([p1, p2], target="target.dummy")
    t = mapper.get_task()
    assert t["targets"] == ["target.dummy"]
    assert t["file_dep"] == ["one.foo", "two.foo"]

def test_mergemapper_raises_exception_without_target():
    with pytest.raises(RuntimeError) as e:
        mapper = fm.MergeMapper("*.foo")
        mapper.get_map()
    assert "Target" in e.value.message

@mock.patch('doitfilemappers.filemappers.pathlib.Path.glob')
def test_compositemapper_collects_from_all_sub_mappers(mock_glob):
    s1 = pathlib.Path("one.foo")
    s2 = pathlib.Path("two.foo")
    t1 = pathlib.Path("one.bar")
    t2 = pathlib.Path("two.bar")
    # Mock GlobMappers
    glob_mapper1 = mock.MagicMock()
    glob_mapper1.get_map.return_value = [(s1, t1)]
    glob_mapper2 = mock.MagicMock()
    glob_mapper2.get_map.return_value = [(s2, t2)]
    mapper = fm.CompositeMapper([glob_mapper1, glob_mapper2], None)
    t = mapper.get_task()
    assert set(t["targets"]) == set(["one.bar","two.bar"])
    assert set(t["file_dep"]) == set(["one.foo","two.foo"])

def test_chainmapper_yields_for_all_subtasks():
    m1 = mock.Mock()
    m1.get_task.return_value = {"actions":["touch foo"], "targets":["foo"]}
    m2 = mock.Mock()
    m2.get_task.return_value = {"actions":["touch bar"], "targets":["bar"]}
    mapper = fm.ChainedMapper(sub_mappers=[m1, m2])
    tasks = list(mapper.get_task())
    assert tasks == [
        {"actions":["touch foo"], "targets":["foo"], "name":"Mock1"},
        {"actions":["touch bar"], "targets":["bar"], "name":"Mock2"}
    ]
    # check if chainmapper sets src from targets of previous tasks
    assert m2.src == ["foo"]

def test_chainmapper_calls_first_subtask_with_src_from_chainmapper():
    p1 = pathlib.Path("one.foo")
    m1 = mock.Mock()
    m1.get_task.return_value = {"actions":["touch foo"], "targets":["foo"]}
    src = [p1]
    mapper = fm.ChainedMapper(src, sub_mappers=[m1])
    list(mapper.get_task())
    assert m1.src == src

def test_chainmapper_returns_combined_map_if_callback_is_given():
    m1 = mock.Mock()
    m1.get_map.return_value = [("start", "foo")]
    m2 = mock.Mock()
    m2.get_map.return_value = [("foo", "bar")]
    callback_func = mock.Mock()
    mapper = fm.ChainedMapper(src="start", sub_mappers=[m1, m2], callback=callback_func)
    tasks = list(mapper.get_task())
    assert len(tasks) == 1
    task = tasks[0]
    assert task["targets"] == ["bar"]
    assert task["file_dep"] == ["start"]

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
