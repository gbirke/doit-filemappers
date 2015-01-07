import pathlib
import re
import abc
from collections import defaultdict

class BaseFileMapper(object):
    __metaclass__  = abc.ABCMeta

    def __init__(self, src="*", callback=None, **kwargs):
        self._initialize_defaults(kwargs)

        self.map_initialized = False
        self.map = []
        self.src = src
        self.callback = callback
        
    def _initialize_defaults(self, config):
        self.in_path = config.get("in_path", pathlib.Path("."))
        self.file_dep = config.get("file_dep", True)
        self.allow_empty_map = config.get("allow_empty_map", False)

    def get_map(self):
        """
        Return a list of (source, target) tuples.

        Each source and target is an instance of Path.
        """
        if not self.map_initialized:
            self.map = self._create_map(self.src)
            self.map_initialized = True
        return self.map

    @abc.abstractmethod
    def _create_map(self, src):
        """ Create the mapping that specific for this mapping class. """

    def get_action(self, callback):
        """
        Return a function that iterates over the map, calling the callback.

        The `targets` parameter of the generated function is ignored.
        """
        file_map = self.get_map()
        def task_action(targets):
            ok = True
            for source, target in file_map:
                if callback(source, target) == False:
                    ok = False
            return ok
        return task_action

    def get_cmd_action(self, cmd):
        """
        Return a list of commands that can be used as action for a task.

        Placeholders `%%(target)s` and `%%(source)s` in the `cmd` parameter will be replaced.
        """
        file_map = self.get_map()
        return [cmd % {'source':m[0], "target":m[1]} for m in file_map]

    def get_task(self, task={}):
        """ Get a task dictionary for DoIt. """
        file_map = self.get_map()
        if not file_map:
            if self.allow_empty_map:
                return self._get_task_for_empty_map(task)
            else:
                raise RuntimeError("The generated map is empty. Please check your mapper parameters.")
        sources, targets = zip(*file_map)
        task["targets"] = list(set([str(t) for t in targets]))

        callback = self.callback
        if callback == None:
            if "action" in task:
                callback = task["action"]
        if hasattr(callback, "__call__"):
            task["actions"] = [self.get_action(callback)]
        elif callback:
            task["actions"] = self.get_cmd_action(callback)

        if self.file_dep:
            task["file_dep"] = [str(s) for s in sources]
        return task

    def _get_task_for_empty_map(self, task):
        """ Provide a NOP action if the task does not contain an action """
        if "actions" not in task:
            task["actions"] = [lambda targets: True]
        return task

    @property
    def src(self):
        return self._src

    @src.setter
    def src(self, src):
        if isinstance(src, basestring):
            self._src = list(pathlib.Path(self.in_path).glob(src))
            self.map_initialized = False
            return
        # Check if src is a list of paths
        try:
            self._src = [self.in_path / p for p in src]
        except TypeError:
            if isinstance(src, pathlib.Path):
                self._src = [self.in_path / src]
            else:
                raise RuntimeError("src must be a path list, a glob expression or a Path instance!")
        self.map_initialized = False

    @property
    def in_path(self):
        return self._in_path

    @in_path.setter
    def in_path(self, path):
        if isinstance(path, pathlib.Path):
            self._in_path = path
        else:
            self._in_path = pathlib.Path(path)

class IdentityMapper(BaseFileMapper):
    def __init__(self, src="*", callback=None, **kwargs):
        super(IdentityMapper, self).__init__(src, callback, **kwargs)
        self.file_dep = kwargs.get("file_dep", False)

    def _create_map(self, src):
        return [(f, f) for f in src]

class RegexMapper(BaseFileMapper):
    def __init__(self, src="*", callback=None, search=r".*", replace=r"\0",flags=0, ignore_nonmatching=True, **kwargs):
        super(RegexMapper, self).__init__(src, callback, **kwargs)
        self.pattern = re.compile(search, flags)
        self.replace = replace
        self.ignore_nonmatching = ignore_nonmatching

    def _create_map(self, src):
        return [(f, self._get_target_from_source(f)) for f in src if self._source_matches(f)]

    def _get_target_from_source(self, source):
        """ Return a Path object for the regular expression substition of source. """
        return pathlib.Path(re.sub(self.pattern, self.replace, str(source)))

    def _source_matches(self, source):
        """
        Check if source matches the search pattern.
        Always returns True if ignore_nonmatching is set to False.
        """
        return not self.ignore_nonmatching or self.pattern.search(str(source))

class GlobMapper(RegexMapper):
    def __init__(self, src="*", callback=None, replace="*", pattern=None, **kwargs):
        if pattern:
            search = self._get_search_regex(pattern)
        elif isinstance(src, basestring):
            search = self._get_search_regex(src)
        else:
            raise RuntimeError("No valid glob search pattern found! You must either provide a glob string in src or via pattern.")
        replace_pattern = replace.replace("*", r"\1", 1)
        super(GlobMapper, self).__init__(src, callback, search, replace_pattern, **kwargs)

    def _get_search_regex(self, pattern):
        """ Convert the glob pattern expression into a regular expression and return it. """
        cnt = pattern.count("*")
        if cnt == 0:
            raise RuntimeError("Glob pattern must contain one asterisk.")
        elif cnt > 1:
            raise RuntimeError("Glob pattern can only contain one asterisk.")
        parts = pattern.split("*", 2)
        return "^" + re.escape(parts[0]) + "(.+)" + re.escape(parts[1]) + "$"

class MergeMapper(BaseFileMapper):
    def __init__(self, src="*", callback=None, target=None, **kwargs):
        super(MergeMapper, self).__init__(src, callback, **kwargs)
        self.target = target

    def _create_map(self, src):
        target = self.target
        return [(f, target) for f in src]
    
    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, new_target):
        if isinstance(new_target, pathlib.Path):
            self._target = new_target
        elif new_target == None:
            raise RuntimeError("Target must be set!")
        else:
            self._target = pathlib.Path(new_target)

class CompositeMapper(BaseFileMapper):
    def __init__(self, sub_mappers=[], callback=None, **kwargs):
        super(CompositeMapper, self).__init__(callback=callback, **kwargs)
        self.sub_mappers = sub_mappers

    def _create_map(self, src):
        """ 
        Create and return map from sub_mappers.

        src is ignored.
        """
        combined_map = []
        for sub_mapper in self.sub_mappers:
            combined_map += sub_mapper.get_map()
        return combined_map

class ChainedMapper(BaseFileMapper):
    def __init__(self, src="*", sub_mappers=[], callback=None, **kwargs):
        super(ChainedMapper, self).__init__(src, callback, **kwargs)
        self.sub_mappers = sub_mappers

    def _create_map(self, src):
        start_source = None
        for m in self.sub_mappers:
            m.src = src
            file_map = m.get_map()
            if not file_map:
                if self.allow_empty_map:
                    return self._get_task_for_empty_map(task)
                else:
                    raise RuntimeError("The generated map is empty. Please check your mapper parameters.")
            sources, targets = zip(*file_map)
            src = list(set([str(t) for t in targets]))
            if not start_source:
                start_source = sources
        sources, targets = zip(*file_map)
        return zip(start_source, targets)

    def get_task(self, task={}):
        if self.callback == None:
            src = self.src
            self.map_counters = defaultdict(lambda: 0)
            for mapper in self.sub_mappers:
                mapper.src = src
                sub_task = mapper.get_task(task)
                src = sub_task["targets"]
                sub_task["name"] = self._get_taskname(mapper, task)
                yield sub_task
        else:
            task = super(ChainedMapper, self).get_task(task)
            task["name"] = "chained_map"
            yield

    def _get_taskname(self, mapper, task):
        classname = type(mapper).__name__
        self.map_counters[classname] += 1
        suffix = self.map_counters[classname]
        return "{}{}".format(classname, suffix)


def open_files(func, in_mode="r", out_mode="w"):
    """ Open files for callback """
    def file_opener(_in, _out, *args, **kwargs):
        with _in.open(in_mode) as in_handle, _out.open(out_mode) as out_handle:
            ok = func(in_handle, out_handle, *args, **kwargs)
        return ok
    return file_opener

def track_file_count(func):
    # See http://stackoverflow.com/questions/3190706/nonlocal-keyword-in-python-2-x
    # to learn why this must be a dictionary
    call_count = {"count":0}
    def file_tracker(_in, _out, *args, **kwargs):
        ok = func(_in, _out, file_count=call_count["count"], *args, **kwargs)
        call_count["count"] += 1
        return ok
    return file_tracker

def open_files_with_merge(func, in_mode="r", out_mode="w", out_append_mode="a"):
    opened = {}
    def file_opener(_in, _out, *args, **kwargs):
        out_name = str(_out)
        if out_name in opened:
            o_mode = out_append_mode
            opened[out_name] += 1
        else:
            o_mode = out_mode
            opened[out_name] = 1
        with _in.open(in_mode) as in_handle, _out.open(o_mode) as out_handle:
            ok = func(in_handle, out_handle, *args, **kwargs)
        return ok
    return file_opener

# TODO  and open_files_for_merge decorators