import doitfilemappers.filemappers as fm
import shutil

def rename_file(_in, _out):
    shutil.move(str(_in), str(_out))

def copy_file(_in, _out):
    shutil.copy(str(_in), str(_out))

def task_create_build_dir():
    return {
        "actions": ["mkdir build"],
        "targets": ["build"],
        "clean": ["rm -rf build"]
    }

def task_convert_files():
    sub_mappers = [
        # Copy files
        fm.GlobMapper("*", copy_file, "build/*.txt", "src/*.txt"),
        # Rename lingering file
        fm.RegexMapper("*", rename_file, search="foo.txt", replace="foo3.txt", dir="build", file_dep=False),
    ]
    mapper = fm.ChainedMapper("src/*.txt", sub_mappers)
    return mapper.get_task()