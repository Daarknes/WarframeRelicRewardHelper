import os
import re
from builtins import isinstance


section_str = """#===============================================================================
# {}
#===============================================================================
"""
_block_sym = r'"""'
block_pattern = re.compile(r'(.*?) *= *' + _block_sym + r'((?:.*?\n?)*)' + _block_sym)
pattern = re.compile(r"(\w+) *= *([^=\n]+)")

class FunctionBlock():
    def __init__(self, body, *params):
        self._body = body
        self._params = params
        
        code = "def func(" + ", ".join(params) + "):\n"
        for line in body.split("\n"):
            code += "  " + line + "\n"
        exec(code)
        self._func = eval("func")

    def __call__(self, *params):
        return self._func(*params)

    def __str__(self):
        return _block_sym + self._body + _block_sym
        
# def create_func(body, func_name, *param_names):
#     code = "def " + func_name + "(" + ", ".join(param_names) + "):"
#     for line in body.split("\n"):
#         code += "  " + line + "\n"
# 
#     exec(code)
#     return eval(func_name)

class Config():
    def __init__(self):
        self._sections = []
        self._defaults = {}
        self._entries = {}
        self._func_locals = {}
    
    def addSection(self, name):
        section = _ConfigSection(name)
        self._sections.append(section)
        return section
    
    def __getitem__(self, key):
        return self._entries[key]
    
    def build(self):
        self._defaults.clear()
        for section in self._sections:
            for entry in section.entries:
                self._defaults[entry.key] = entry.value
 
    def loadAndUpdate(self, path):
        self._entries.clear()
        
        # when the config does not exist, fill self._entries with the default values and save it
        if not os.path.exists(path):
            for key, value in self._defaults.items():
                self._entries[key] = value
                # add FunctionBlocks to the globals dict to make all "functions" accessible
                if isinstance(value, FunctionBlock):
                    globals()[key] = value

            self._save(path)
            return

        with open(path, "r") as f:
            raw_data = f.read()
        needsSave = False

        while True:
            res = re.search(block_pattern, raw_data)
            if res is None:
                break
            
            key = res.group(1)
            raw_data = raw_data[:res.span()[0]] + raw_data[res.span()[1]+1:]
            
            # not an allowed key
            if key not in self._defaults:
                needsSave = True
                continue

            value = res.group(2)
            self._entries[key] = FunctionBlock(value, *self._defaults[key]._params)
            # add FunctionBlocks to the globals dict to make all "functions" accessible
            globals()[key] = self._entries[key]
        
        for key, value in re.findall(pattern, raw_data):
            # not an allowed key
            if key not in self._defaults:
                needsSave = True
                continue
            
            vType = type(self._defaults[key])
            if vType == bool:
                value = value == "True"
            else:
                value = vType(value)
            self._entries[key] = value
        
        # check if all default keys exist in the loaded config
        for key, value in self._defaults.items():
            if key not in self._entries:
                self._entries[key] = value
                needsSave = True
        
        if needsSave:
            self._save(path)
    
    def _save(self, path):
        raw_data = ""
        for section in self._sections:
            raw_data += section_str.format(section.name)

            for entry in sorted(section.entries, key=lambda entry: entry.key):
                raw_data += "# " + entry.comment + "\n"
                raw_data += entry.key + " = " + str(self._entries[entry.key]) + "\n\n"
                
        with open(path, "w") as f:
            f.write(raw_data)
    
    def __repr__(self):
        return repr(self._entries)

class _ConfigSection():
    def __init__(self, name):
        self.name = name
        self.entries = []

    def addEntry(self, key, value, comment):
        if isinstance(value, FunctionBlock):
            comment += " (PARAMS: " + ", ".join(value._params) + ")"
        else:
            comment += " (DEFAULT: " + str(value) + ")"
        self.entries.append(_ConfigEntry(key, value, comment))

class _ConfigEntry():
    def __init__(self, key, value, comment):
        self.key = key
        self.value = value
        self.comment = comment
    
    def __str__(self):
        return (self.key, self.value, self.comment)
