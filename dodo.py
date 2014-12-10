import shutil
from filesets import *

def task_step1():

    def process_file(out_file):
        print "processing {} ...".format(out_file)

    fs = SourceFileset("work/*.txt")
    return {
        "actions": [fs.get_action(process_file)],
        "targets": fs.get_targets()
    }

def task_step2():

    def copy_file(in_file, out_file):
        shutil.copyfile(in_file, out_file)

    fs = TransformFileset("work/*.txt", r"(.*)\.txt$", r"\1.bak")
    return {
        "actions": [fs.get_action(copy_file)],
        "file_dep": fs.get_file_dep(),
        "targets":  fs.get_targets()
    }    
    
