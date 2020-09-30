#!/usr/bin/env python

from pprint import pprint
import urllib.request
import re
from html.parser import HTMLParser
from collections import defaultdict

baseurl = 'http://mappings.dbpedia.org/server/ontology/classes'

def camel_to_snake(camel_input):
  words = re.findall(r'[A-Z]?[a-z]+|[A-Z]{2,}(?=[A-Z][a-z]|\d|\W|$)|\d+', camel_input)
  return '_'.join(map(str.lower, words))

def range_to_sqltype(range):
  if 'owl:' in range.lower():
    return 'TEXT'
  if 'integer' in range.lower():
    return 'INTEGER'
  if 'string' in range.lower():
    return 'TEXT'
  if 'year' in range.lower():
    return 'INTEGER'
  return range

class OntologyClassParser(HTMLParser):
  class_name = None
  table_counter = 0
  tr_counter = 0
  td_counter = 0
  property_dict = defaultdict(dict)
  property_name = None
  ignore_data = False
  wait_for_comment = False
  comment = None

  def __init__(self, name):
    super().__init__()
    self.reset()
    self.class_name = name

  def handle_starttag(self, tag, attrs):
    if tag == 'table':
      # print('found table #', self.table_counter)
      self.table_counter += 1
    if tag == 'small':
      self.ignore_data = True
    if self.table_counter == 2:
      if tag == 'tr':
        #print('found tr')
        self.tr_counter += 1
      if self.tr_counter > 1:
        if tag == 'td':
          self.td_counter += 1

  def handle_endtag(self, tag):
    sql_field = '  {:25} {:12} {:20} {}'
    if tag == 'table':
      self.tr_counter = 0
    if tag == 'tr':
      self.td_counter = 0
      self.property_name = None
      self.wait_for_comment = False
    if tag == 'small':
      self.ignore_data = False
    if tag == 'html':
      with open(self.class_name.lower() + '.sql', 'w') as f:
        print ('CREATE TABLE IF NOT EXISTS', self.class_name.lower(), file=f)
        print ('(', file=f)
        print (sql_field.format('created', 'timestamptz', '',                     'DEFAULT current_timestamp').rstrip(), ',', file=f)
        print (sql_field.format('id',      'uuid',        'PRIMARY KEY NOT NULL', '').rstrip(),                          ',', file=f)
        for key, value in self.property_dict.items():
          field_name = camel_to_snake(key)
          field_type =  range_to_sqltype(value['Range'])
          print(sql_field.format(field_name, field_type,  '',                     '').rstrip(),                          ',', file=f)
        print (sql_field.format('updated', 'timestamptz', '',                     'DEFAULT current_timestamp'), file=f)
        print (');', file=f)
        print (file=f);
        if self.comment and self.comment != '':
         print("COMMENT ON TABLE {} IS q'[{}]';".format(self.class_name.lower(), self.comment), file=f);
        for key, value in self.property_dict.items():
          if 'Comment' in value and value['Comment'] != '':
            field_name = camel_to_snake(key)
            print("COMMENT ON COLUMN {}.{} IS q'[{}]';".format(self.class_name.lower(), field_name, value['Comment']), file=f);
        print (file=f);

#equipment  {'Name': 'equipment ', 'Label': 'equipment', 'Domain': 'Activity', 'Range': 'owl:Thing'}
#numberOfClubs  {'Name': 'numberOfClubs ', 'Label': 'number of clubs', 'Domain': 'Activity', 'Range': 'xsd:nonNegativeInteger'}
#numberOfPeopleLicensed  {'Name': 'numberOfPeopleLicensed ', 'Label': 'number of licensed', 'Domain': 'Activity', 'Range': 'xsd:nonNegativeInteger', 'Comment': 'nombre de personnes ayant une license pour pratiquer cette activité'}

  def handle_data(self, data):
    if not self.ignore_data:
      if self.table_counter == 1:
        if data.startswith('owl:'):
          self.reset()
        if data == 'Comment (en)':
          self.wait_for_comment = True
        if data.strip() != '' and data.strip() != ':':
          self.comment = data
          self.wait_for_comment = False
      if self.table_counter == 2 and self.tr_counter > 1:
        if data.strip() != '':
          if self.property_name == None:
            #print('set property_name: ', data)
            self.property_name = data
            self.property_dict[self.property_name]['Name'] = data
          else:
            if self.td_counter == 2:
              #print('prop[', self.property_name, '][Label] = ', data)
              self.property_dict[self.property_name]['Label'] = data
            elif self.td_counter == 3:
              #print('prop[', self.property_name, '][Domain] = ', data)
              self.property_dict[self.property_name]['Domain'] = data
            elif self.td_counter == 4:
              #print('prop[', self.property_name, '][Range] = ', data)
              self.property_dict[self.property_name]['Range'] = data
            elif self.td_counter == 5:
              #print('prop[', self.property_name, '][Comment] = ', data)
              self.property_dict[self.property_name]['Comment'] = data

class OntologyClassListParser(HTMLParser):
  def __init__(self):
    super().__init__()
    self.reset()

  def handle_starttag(self, tag, attrs):
    if tag == 'a':
      for name, value in attrs:
        if name == "name":
          if ':' not in value: 
            parse_class(value)

def parse_class(name):
  parser = OntologyClassParser(name)
  url = baseurl + '/' + name
  print('getting: ' + url)
  response = urllib.request.urlopen(url)
  html = response.read().decode()
  try: 
    parser.feed(html)
  except AssertionError:
    print('skipped: ' + name)

def parse_classlist():
  classes_parser = OntologyClassListParser()
  response = urllib.request.urlopen(baseurl)
  html = response.read().decode()
  classes_parser.feed(html)

if __name__ == "__main__":
  parse_classlist()


