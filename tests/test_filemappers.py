import doitfilemappers.filemappers as fm

import mock

def get_path_mock():
    p = mock.MagicMock()
    p.is_file.return_value = True
    p.is_symlink.return_value = False 
    return p

@mock.patch('doitfilemappers.filemappers.pathlib.Path.glob')
def test_identitymapper_expands_glob(mock_glob):
    #mock_glob.return_value = ["one.foo"]
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
def test_identitymapper_input_equals_output(mock_glob):
    p1 = get_path_mock()
    p2 = get_path_mock()
    mock_glob.return_value = [p1, p2]
    mapper = fm.IdentityMapper("*.foo")
    m = mapper.get_map()
    assert m == [(p1, p1), (p2, p2)]