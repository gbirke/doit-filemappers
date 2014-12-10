import glob
import re

# At the moment, file set and file mapper functionality is built into one, this will change

class Fileset(object):
    """ Basic abstract fileset class to define common methods and interfaces
    """
    def get_targets(self):
        return []

    def get_file_dep(self):
        return []

    def get_action(self, callback):
        return lambda targets: None

    def get_filelist(self, files):
        file_list = []
        if type(files) == str or type(files) == unicode:
            file_list += glob.glob(files)
        else:
            for f in files:
                file_list += self.get_filelist(f)
        return file_list


class SourceFileset(Fileset):
    """ Fileset class that is the starting point for processing files.
        It just reads exists files.
    """
    def __init__(self, src):
        self.sources = self.get_filelist(src)
        
    def get_targets(self):
        return self.sources

    def get_action(self, callback):
        def action(targets):
            for t in targets:
                callback(t)
        return action

class TransformFileset(Fileset):
    def __init__(self, src, search, replace):
        self.map = {s : re.sub(search, replace, s) for s in self.get_filelist(src)}
        
    def get_targets(self):
        return self.map.values()

    def get_file_dep(self):
        return self.map.keys()        

    def get_action(self, callback):
        filemap = {target: source for source,target in self.map.items()}
        def action(targets):
            for t in targets:
                callback(filemap[t], t)
        return action    