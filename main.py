import json
import pathlib
from functools import lru_cache

import pandas as pd
import unidecode as unidecode


class CountryCityFixture:

    def __init__(self, excel_name, country_model_name, city_model_name, **kwargs):
        self.data = pd.read_excel(excel_name, keep_default_na=False, **kwargs)
        self.country_model_name = country_model_name
        self.city_model_name = city_model_name

    @property
    @lru_cache
    def countries(self):
        countries = list()
        seen = set()
        for key, row in self.data.sort_values(by=['country']).iterrows():
            if not row['country'] or row['country'] in seen:
                continue
            entry = dict(model=None, pk=None, fields=dict)
            entry['fields'] = {
                'name': row['country'],
                'iso2': row['iso2'],
                'iso3': row['iso3'],
            }
            countries.append(entry)
            seen.add(row['country'])
        self.add_fixture_attributes(self.country_model_name, countries)
        return countries

    @property
    @lru_cache
    def cities(self):
        cities = list()
        seen = set()
        for key, row in self.data.sort_values(by=['country', 'admin_name', 'city_ascii']).iterrows():
            name = unidecode.unidecode(row['admin_name'] or row['city_ascii']).replace('/', '')
            country_id = self.get_country_id(row['country'])
            if not name or (name, country_id) in seen:
                continue
            entry = dict(model=None, pk=None, fields=dict)
            entry['fields'] = {
                'country': country_id,
                'name': name,
                'is_capital': row['capital'] == "primary",
            }
            cities.append(entry)
            seen.add((name, country_id))
        self.add_fixture_attributes(self.city_model_name, cities)
        return cities

    @staticmethod
    def add_fixture_attributes(model, objects):
        for index, obj in enumerate(objects, start=1):
            record = {
                "model": model,
                "pk": index,
            }
            obj.update(record)
        return objects

    @lru_cache
    def get_country_id(self, name):
        for country in self.countries:
            if country['fields']['name'] == name:
                return country['pk']
        raise ValueError


def create_file(output_name, data):
    # create folders
    pathlib.Path('/'.join(output_name.split('/')[:-1])).mkdir(parents=True, exist_ok=True)
    with open(output_name, "w", encoding='UTF-8') as file:
        file.write(data)


def main():
    fixture = CountryCityFixture('worldcities.xlsx', 'adverts.country', 'adverts.city')
    create_file('fixtures/country.json', json.dumps(fixture.countries, ensure_ascii=False))
    create_file('fixtures/city.json', json.dumps(fixture.cities, ensure_ascii=False))


if __name__ == '__main__':
    main()
