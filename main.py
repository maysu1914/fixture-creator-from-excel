import json
import os
import pathlib
import time
import urllib.parse

import pandas as pd
from lxml import html
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as chrome_options


class BrowserChrome:
    path = "\driver\chromedriver.exe"
    extensions = ()

    def __init__(self, path=path, extensions=extensions, headless=None):
        driver_path = os.getcwd() + path
        print(driver_path)
        options = self.get_options(extensions, headless)
        self.driver = webdriver.Chrome(executable_path=driver_path, options=options)

    def open(self, url):
        if urllib.parse.unquote(self.driver.current_url) != url:
            self.driver.get(url)

    def get_driver(self):
        return self.driver

    def get_options(self, extensions, headless):
        options = chrome_options()
        options.add_argument("--start-maximized")
        if headless:
            options.headless = True  # disabled because some different behaviours detected from web site
        for extension in extensions:
            options.add_extension(os.getcwd() + extension)
        return options

    def google_translate(self, text, _from, _to):
        self.open(
            f'https://translate.google.com.tr/?hl={_to}&tab=wT&sl={_from}&tl={_to}&text={urllib.parse.quote_plus(text)}&op=translate')
        result_xpath = """//*[@id="yDmH0d"]/c-wiz/div/div[2]/c-wiz/div[2]/c-wiz/div[1]/div[2]/div[2]/c-wiz[2]/div[5]/div/div[1]/span[1]/span/span/text()"""
        while not html.fromstring(self.driver.page_source).xpath(result_xpath):
            try_again_button_xpath = """//*[@id="yDmH0d"]/c-wiz/div/div[2]/c-wiz/div[2]/c-wiz/div[1]/div[2]/div[2]/c-wiz[2]/div[4]/div[2]/button/span"""
            if self.driver.find_element_by_xpath(try_again_button_xpath).is_displayed():
                print('try again exist')
                self.driver.find_element_by_xpath(try_again_button_xpath).click()
        return html.fromstring(self.driver.page_source).xpath(result_xpath)[0]

    def google_search_translate(self, text):
        """
        better than individual translate page
        but not well programmed
        :param text:
        :return:
        """
        self.open("https://www.google.com/search?q=çeviri")

        source = """//*[@id="tw-source-text-ta"]"""
        result = """//*[@id="tw-target-text"]/span/text()"""

        self.driver.find_element_by_xpath(source).clear()
        self.driver.find_element_by_xpath(source).send_keys(text)

        time.sleep(1.5)
        print(' -> '.join([text, html.fromstring(self.driver.page_source).xpath(result)[0]]))
        return html.fromstring(self.driver.page_source).xpath(result)[0]


def read_excel(filepath, columns=None):
    df = pd.read_excel(filepath, header=0, usecols=','.join(columns))
    headers = [header for header in df]
    data = {header: '' for header in headers}
    results = []

    for index, row in df.iterrows():
        _data = data.copy()
        for header in headers:
            _data[header] = row[header]
        results.append(_data)

    return results


def get_json_countries(data):
    bc = BrowserChrome(headless=True)
    countries = {}
    # set country names only as keys
    counter = 1
    for row in sorted(data, key=lambda k: k['country']):
        if row['country'] not in countries:
            countries[row['country']] = {
                'pk': counter,  # we use this id when creating city fixture
                'fields': {
                    'formal_name': bc.google_search_translate(row['country']),
                    'international_formal_name': row['country'],
                }
            }
            counter += 1
    return countries


def get_json_cities(data, countries_json):
    cities = {}
    # set city names only as keys
    for row in sorted(data, key=lambda k: str(k['admin_name'])):
        if row['admin_name'] not in cities:
            cities[row['admin_name']] = {
                'fields': {
                    'country': countries_json[row['country']]['pk'],
                    'city': row['city'],
                    'city_ascii': row['city_ascii'],
                    'admin_name': row['admin_name'],
                    'capital': True if row['capital'] == "primary" else False,
                    'iso2': row['iso2'],
                    'iso3': row['iso3'],
                }
            }
    return cities


def create_django_fixture(app, model, fields_list):
    fixture_list = []
    for index, fields in enumerate(fields_list, start=1):
        record = {
            "model": f"{app}.{model}",
            "pk": index,
            "fields": fields
        }
        fixture_list.append(record)
    return fixture_list


def create_file(output_name, data):
    # create folders
    pathlib.Path('/'.join(output_name.split('/')[:-1])).mkdir(parents=True, exist_ok=True)
    with open(output_name, "w", encoding='UTF-8') as file:
        file.write(data)


def main():
    cities_data = read_excel('worldcities.xlsx', columns=['A', 'B', 'E', 'F', 'G', 'H', 'I'])

    countries_json = get_json_countries(cities_data)
    cities_json = get_json_cities(cities_data, countries_json)

    country_fields_only = [value['fields'] for key, value in countries_json.items()]
    country_fixture = create_django_fixture('information', 'country', country_fields_only)

    create_file('fixtures/country.json', json.dumps(country_fixture, ensure_ascii=False))

    city_fields_only = [value['fields'] for key, value in cities_json.items()]
    city_fixture = create_django_fixture('information', 'city', city_fields_only)

    create_file('fixtures/city.json', json.dumps(city_fixture, ensure_ascii=False))


if __name__ == '__main__':
    main()
