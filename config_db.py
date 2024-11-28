#!/usr/bin/python
from configparser import ConfigParser

def config(file='database.ini', section='postgresql'):
    parser = ConfigParser()
    parser.read(file)

    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in {1} file'.format(section, file))
    return db

if __name__ == '__main__':
    config = config()
    print(config)
