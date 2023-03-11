from functools import lru_cache
from pathlib import Path

import yaml
from yaml.loader import SafeLoader


class FileUtils:
    
    @classmethod
    @lru_cache(maxsize=5, typed=True)
    def read_yaml_file(cls, path, modified_time=None):
        try:
            file_path = Path(path).resolve(strict=True)
            print(file_path)
            with open(file_path, 'r') as f:
                data = yaml.load(f, Loader=SafeLoader)
            return data
        except FileNotFoundError:
            raise FileNotFoundError

    @classmethod
    def get_config(cls, filepath, field=None):
        file_path = Path(filepath).resolve(strict=True)
        modified_time = file_path.stat().st_mtime
        data = FileUtils.read_yaml_file(file_path, modified_time)
        if field:
            return data[field]
        return data
