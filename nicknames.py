###
##
#
# carltonnorthern/nickname-and-diminutive-names-lookup is licensed under the
#
# https://github.com/carltonnorthern/nickname-and-diminutive-names-lookup
#
# Apache License 2.0
# http://www.apache.org/licenses/
#
##
###

import logging
import collections
import csv

class NameDenormalizer(object):
    def __init__(self, filename=None):
        filename = filename or 'static_data/names.csv'
        lookup = collections.defaultdict(list)
        with open(filename) as f:
            reader = csv.reader(f)
            for line in reader:
                matches = set(line)
                for match in matches:
                    lookup[match].append(matches)
        self.lookup = lookup

    def __getitem__(self, name):
        name = name.lower()
        if name not in self.lookup:
            raise KeyError(name)
        names = set().union(*self.lookup[name])
        logging.debug(f'getitem({name}): {names}')
        if name in names:
            names.remove(name)
        return names

    def get(self, name):
        try:
            logging.debug(f'getnick: self[{name}] = self[name]')
            return self[name]
        except KeyError:
            return []
