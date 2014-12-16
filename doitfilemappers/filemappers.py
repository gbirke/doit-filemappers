import pathlib
import re


class BaseFileMapper(object):

    def __init__(self, src, callback=None, **kwargs):
        self.map_initialized = False
        self.map = []
        self.src = src
        self.callback = callback
        self.follow_symlinks = kwargs["follow_symlinks"] if "follow_symlinks" in kwargs else True
        self.dir = kwargs["dir"] if "dir" in kwargs else "."
        self.file_dep = kwargs["file_dep"] if "file_dep" in kwargs else True

    def get_map(self):
        """ Return a list of (source, target) tuples. """
        if not self.map_initialized:
            self._initialize_map()
            self.map_initialized = True
        return self.map

    def _initialize_map(self):
        raise NotImplementedError

    def get_action(self):
        """ Return a function that iterates over the map, calling the callback.

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
        file_map = self.get_map
        sources, targets = zip(*file_map)
        task["targets"] = targets
        task["action"]  = self.get_action()
        if self.file_dep:
            task["file_dep"] = sources
        return task

    def _get_files_from_glob(self):
        """ Get a list of files from the glob expression in self.src

            If self.follow_symlinks is false, symlinks will be ignored, 
            otherwise smylinks to files will be returned.
        """
        return [p for p in pathlib.Path(self.dir).glob(self.src) if self._is_file_or_symlink(p)]

    def _is_file_or_symlink(self, f):
        if not self.follow_symlinks and p.is_symlink():
            return False
        else:
            return p.is_file()


class IdentityMapper(BaseFileMapper):
    def _initialize_map(self):
        self.map = [(f, f) for f in self._get_files_from_glob()]

