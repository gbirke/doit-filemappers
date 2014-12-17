import pathlib
import re
import abc

class BaseFileMapper(object):
    __metaclass__  = abc.ABCMeta

    def __init__(self, src="*", callback=None, **kwargs):
        self.map_initialized = False
        self.map = []
        self.src = src
        self.callback = callback
        self.follow_symlinks = kwargs.get("follow_symlinks", True)
        self.dir = kwargs.get("dir", ".")
        self.file_dep = kwargs.get("file_dep", True)

    def get_map(self, src=None):
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

    def get_action(self):
        """
        Return a function that iterates over the map, calling the callback.

        The `targets` parameter of the generated function is ignored.
        """
        file_map = self.get_map()
        callback = self.callback
        def task_action(targets):
            ok = True
            for source, target in file_map:
                ok &= callback(source, target)
            return ok
        return task_action

    def get_task(self, task={}):
        """ Get a task dictionary for DoIt. """
        file_map = self.get_map()
        sources, targets = zip(*file_map)
        task["targets"] = [str(t) for t in targets]
        task["action"]  = self.get_action()
        if self.file_dep:
            task["file_dep"] = [str(s) for s in sources]
        return task

    def _get_files_from_glob(self, src):
        """ 
        Get a list of files from the glob expression in src.

        If self.follow_symlinks is false, symlinks will be ignored, 
        otherwise smylinks to files will be returned.
        """
        return [p for p in pathlib.Path(self.dir).glob(src) if self._is_file_or_symlink(p)]

    def _is_file_or_symlink(self, f):
        if not self.follow_symlinks and f.is_symlink():
            return False
        else:
            return f.is_file()


class IdentityMapper(BaseFileMapper):
    def __init__(self, src="*", callback=None, **kwargs):
        super(IdentityMapper, self).__init__(src, callback, **kwargs)
        self.file_dep = kwargs.get("file_dep", False)

    def _create_map(self, src):
        return [(f, f) for f in self._get_files_from_glob(src)]

class RegexMapper(BaseFileMapper):
    def __init__(self, src="*", callback=None, search=r".*", replace=r"\0", ignore_nonmatching=True, **kwargs):
        super(RegexMapper, self).__init__(src, callback, **kwargs)
        self.pattern = re.compile(search)
        self.replace = replace
        self.ignore_nonmatching = ignore_nonmatching

    def _create_map(self, src):
        return [(f, self._get_target_from_source(f)) for f in self._get_files_from_glob(src) if self._source_matches(f)]

    def _get_target_from_source(self, source):
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
        else:
            search = self._get_search_regex(src)
        replace_pattern = replace.replace("*", r"\1", 1)
        super(GlobMapper, self).__init__(src, callback, search, replace_pattern)

    def _get_search_regex(self, pattern):
        cnt = pattern.count("*")
        if cnt == 0:
            raise RuntimeError("Glob pattern must contain one asterisk.")
        elif cnt > 1:
            raise RuntimeError("Glob pattern can only contain one asterisk.")
        parts = pattern.split("*", 2)
        return "^" + re.escape(parts[0]) + "(.*)" + re.escape(parts[1]) + "$"