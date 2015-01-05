# File-based workflows for the DoIt automation tool
The goal of this project is to create a library of file collection and mapping classes that provide `action`, `file_dep` and `target` parameters to [DoIt][1] tasks. The mappers allow specifying tasks that rely on globs and file name mapping rather than having to explicity name every file dependency and every target. This is for text and data processing tasks that happen in several stages where data is converted, enriched, filtered and merged.

The classes are inspired by concepts in the popular [Ant][2] and [Ruffus][3] build tools.

## FileMapper usage
A typical DoIt Python task calls a function with a list of target files:

```python
def task_convert_to_json():
    def process_files(targets):
        for t in target:
            # read target, map to json, write to individual json file
    return {
        "actions": [process_files],
        "targets": ["file1.csv", "file2.csv"]
    }
```

A file mapper produces a "source" file for every target file and vice versa. Consider the easiest case where you want to create a new, processed file for every source file:

```python
from doitfilemappers import GlobMapper

def task_convert_to_json():
    def process_file(in_file, out_file):
        with in_file.open("r") as _in, out_file.open("w") as _out:
            # read from _in, process data, write to _out
    mapper = GlobMapper("src/*.csv", process_file, pattern="dst/*.json")
    return mapper.get_task()
```

You must always provide a callback to the mapper that receives one source file and one target file as [`pathlib.Path`][5] instances. This callback will be called for every source/target pair of the mapper.

The `get_task` method of the mapper will return the task dictionary with the ` actions`, `targets` and `file_dep` keys generated by the mapper. `actions` is a callable generated by the mapper using the `callback` parameter. The `actions` callable will __ignore__ the `targets` parameter provided by DoIt and use the internal mapping instead.

If you want to have additional keys in the task dictionary, e.g. `uptodate`, `basename`, `title`, etc., you can provide them as a parameter to `get_task`. All dictionary values except for `actions`, `targets` and `file_dep` will just be returned.

```python
mapper.get_task({"basename":"foo"})
```

### Mapper constructor parameters
The following parameters are common for all mappers
- `src`: Designate which source files should be selected. This can either be a glob string that can be used by [`pathlib.Path.glob`][4] or a list of Path instances. Defaults to all files (`*`).
- `callback`: A callable with `input_file`, `output_file` parameters.
- `in_path`: Operating directory. The glob expression / Path items  in `src` will be evaluated in the context of this path. If `in_path` is absolute, the generated targets will be absolute too. Otherwise they will be relative. Defaults to `.` (current directory).
- `file_dep`: If true, `get_task` creates a `file_dep` key with the source files from the mapper. For most mappers it is true.
- `allow_empty_map`: See "Dealing with empty maps". Defaults to false.

### Multiple dependent mappers
If you are building a chain of mappers where the output files (targets) of one processing step become the input (sources) of the next step, you can't use a glob expression for the `src` parameter after the first because the files don't exist yet. Instead, you must set the `src` of each task after the first to the `target` output of the preceding task. The ChainedMapper (see below) does that for you.

### Using mappers with commandline tasks

TODO

### Decorators for your callback function

#### `@open_files`
If you'd rather work with open files instead of opening and closing them yourself, you can use the `@open_files` decorator:

```python
@open_files
def process_file(in_file, out_file):
    data = in_file.read()
    # process data
    out_file.write(data)
```

Normally the input file is opened in read mode, the output file is opened in write mode. You can change the modes with the `in_mode` and `out_mode` parameters for `@open_file`.

#### `@open_files_with_merge`
This decorator works like `@open_files` except it tracks which target files have already been opened. Files that were opened before, are opened in append mode (`a`). You can customize the modes with the  `in_mode`, `out_mode` and `out_append_mode` parameters.

#### `@track_file_count`
If you want to keep track of the number of files that were processed, use the `@track_file_count` decorator and a `file_count` parameter in your callback:

```python
@track_file_count
def process_file(in_file, out_file, file_count=0):
    if file_count > 99:
        raise RuntimeError("Too many files, I quit!")
```

### Dealing with empty maps
An empty map means that the source files are missing, your glob expression for `src` is wrong or the mapper filtered the file names (can happen with GlobMapper and RegexMapper). In most cases this means the task and all tasks depending on it should not continue, so the default behavior of mappers is to raise an exception if the map is empty.

You can change the default behavior by setting `allow_empty_map` to `True`. You can then provide custom `actions` and `targets` keys to `get_map` do do something else when the map is empty:

```python
from __future__ import print_function

def task_report_missing_foo():
    def report_missing(targets):
        print("WARNING: We're out of 'foo' files!", file=sys.stderr)
    mapper = GlobMapper("foo*", process_foo, "bar*", allow_empty_map=True)
    return mapper.get_task({
        "actions": [report_missing],
        "targets": ["foo_dummy"]
    })
```

If you don't provide an `actions` key, the task will simply do nothing. A dummy action is created that just returns `True`. 

## Types of Mappers
### IdentityMapper
This simple mapper returns all files found by the `src` glob as targets and has no `file_dep` (because that would create a cyclic dependency). 

The IdentityMapper is useful for processing files in-place or processing files without changing them.

### GlobMapper
The GlobMapper uses a single asterisk to define a simple replacement pattern.

```python
def task_json2html():
    def process_file(in_file, out_file):
        # do stuff here
    mapper = GlobMapper("*.json", process_file, "*.html")
    return mapper.get_task()
```

The asterisk in the search expression (by default the `src` parameter) is a wildcard expression that matches at least one character. The asterisk in the replace string is the placeholder for everything matched by the search expression.

If your `src` parameter contains a single file name, a directory glob like `**/*.json`, multiple asterisks like `*.txt*` or complex globs like `ba[rz].txt` you **must** provide a replacement pattern that contains a single asterisk. 

```python
mapper = GlobMapper("**/*.json", process_file, "*.html", "*.json")
```

If a single asterisk is not sufficient for your replacement needs, use `RegexMapper` instead.

**Warning:** Some patterns will create the same target name for different source names which may lead to overwriting the target. If you want to append instead, use `@open_files_with_merge`.

### RegexMapper

The RegexMapper uses a regular expression to allow for more complex filename transformations.

```python
import shutils

def task_move_files():
    """ Rename files named "Foo_Bar.txt" to "Bar-Foo.txt" """
    mapper = RegexMapper("*.txt", shutils.move, r"^(\w+)_(\w+)", r"\2-\1")
    return mapper.get_task()
```

RegexMapper has the parameter `ignore_nonmatching` which is `True` by default. If set to `False`, the map will contain files that do not match the search expression. You should set `ignore_nonmatching` to `False` in this case to avoid errors.

```python
def task_process_text():
    """ 
    Process only CSV and text files.
    All other files will keep their name and show up unchanged
    in the targets list.
    """
    def process_text(_in, _out):
        if _in.suffix() == ".txt":
            # process text file
        elif _in.suffix() == ".csv":
            # process CSV file

    mapper = RegexMapper("*", process_text, 
        search=r"^(.*)\.(txt|csv)$",
        replace=r"\1-processed.\3",
        ignore_nonmatching=False,
        file_dep=False
    )
    return mapper.get_task()
```

You can set all the usual regex flags by using the `flags` parameter:

```python
import re
# match TXT and txt files
mapper = RegexMapper("*", shutils.move,
    search=r"^(.*)\.txt",
    replace=r"\1-processed.txt",
    flags=re.IGNORECASE
)
```

**Warning:** Some patterns will create the same target name for different source names which may lead to overwriting the target. If you want to append instead, use `@open_files_with_merge`.

### MergeMapper
The MergeMapper returns the same target file name for all source names.

When using MergeMapper you have to open the output file for appending (mode `a`) instead of opening it while truncating it (mode `w`). This can be a problem because if the target file exists from a previous task run, the content from the source files will be appended to it - not a desired behavior in most cases. To avoid a separate task where you delete the target file before first opening it, use the `@open_files_with_merge` decorator which keeps track of the files, opens the first one with mode `w` and all following files with mode `a`.

```python
def task_all_reports():
    @open_files_with_merge()
    def process_csv(_in, _out):
        data = _in.read()
        # process data
        _out.write(data)
    mapper = MergeMapper("*.csv", process_csv, "finished/combined.csv")
    return mapper.get_task()
```

### CompositeMapper
The CompositeMapper returns the combined map of several mappers. It has no `src` parameter. 

```python
def task_convert_images():
    def convert_img(image_in, image_out):
        # do some processing here
    sub_mappers = [
        GlobMapper("*.jpg", replace="*_thumb.jpg"),
        GlobMapper("*.jpeg", replace="*_thumb.jpg")
    ]
    mapper = CompositeMapper(sub_mappers, convert_img)
    return mapper.get_task()
```

The example shows that you can omit the `callback` parameter for the sub-mappers, because only the callback of the CompositeMapper will be executed.

Note that the generated map may contain the same source and/or target files multiple times. You must then write your callback in way that can avoids processing the same source file multiple times or overwriting the same target file.

### ChainedMapper
The ChainedMapper chains multiple mappers together, using the target files of each mapper as the source files for the next mapper. The `src` of the ChainedMapper is used as the initial `src` for the first sub-mapper in the chain.

If you want each action of the sub-mappers executed, you must leave the `callback` parameters of ChainedMapper empty:

```python
import shutils

def task_convert_images():
    def convert_img(image_in, image_out):
        # do some processing here
    # src param ("*") in the following mappers is just a dummy and will
    # be overwritten by the ChainedMapper
    my_sub_mappers = [
        # Remove non-alphanumeric chars in file name
        RegexMapper("*", shutils.move, r"[^\w_]", r"_",
            ignore_nonmatching=False),
        # Restore the suffix (dot was replaced be previous step)
        RegexMapper("*", shutils.move, r"_jpg$", r".jpg"),
        #  Create Thumbnails
        GlobMapper("*", convert_img, replace="*_thumb.jpg", "*.jpg")
    ]
    mapper = ChainedMapper("*.jpg", sub_mappers=my_sub_mappers)
    return mapper.get_task()
```

If the `callback` parameter of the ChainedMapper is set, the callbacks of the chained sub-mappers will **not** be executed. Instead, only the map will be generated and the callback of the ChainedMapper will be executed. This is useful for complex mapping types that require multiple steps when generating the final mapping. The generated `file_dep` will be the source files of the *first* sub-mapper.

```python
import shutils

def cleanup_file_names():
    # src param is left out since it will be overwritten by ChainedMapper
    # callback param is left out since it won't be called.
    my_sub_mappers = [
        RegexMapper(search=r"[^\w_]", replace=r"_", ignore_nonmatching=False)
        RegexMapper(search=r"^_", replace=r"", ignore_nonmatching=False)
        RegexMapper(search=r"_jpg$", replace=r".jpg")
    ]
    mapper = ChainedMapper("*.jpg", shutils.move, sub_mappers=my_sub_mappers)
    return mapper.get_task()
```


## Creating your own mappers

Creating your own mappers is easy - just subclass `BaseMapper` and implement the `_create_map` method:

```python
class LowercaseMapper(BaseMapper):
    def _create_map(self, src):
        return [(s, str(s).lower()) for s in src]
```

The `src` parameter is always a list of `Path` objects.

If you need additional parameters or different parameter defaults, you have to overwrite the `__init__` method:

```python
class LowercaseMapper(BaseMapper):
    def __init__(self, src, callback, file_dep=False, **kwargs):
        super(LowercaseMapper, self).__init__(
            src, 
            callback, 
            file_dep=file_dep,
            **kwargs
        )

    def _create_map(self, src):
        return [(s, str(s).lower()) for s in src]
```

## TODO
- Create specific exceptions
- Add uptodate function to mappers that returns the result of checking timstamps of each source and target file in the map.
- Use [six][6] library for Python 3 compatibility

[1]: http://pydoit.org/ 
[2]: http://ant.apache.org/
[3]: http://www.ruffus.org.uk/
[4]: https://pathlib.readthedocs.org/
[5]: https://docs.python.org/3/library/pathlib.html#concrete-paths
[6]: http://pythonhosted.org/six/
