import requests
import random
import re
from enum import Enum
from datetime import datetime, timedelta
from urllib.parse import quote
from bs4 import BeautifulSoup
from static_data import USER_LIST


class MovementType(Enum):
    departure = 'departure'
    arrival = 'arrival'


def get_headers():
    headers = {
        'User-Agent': random.choice(USER_LIST)
    }
    return headers


def get_target_url(airport_city: str, airport_id: str, movement_type: MovementType, target_time: datetime):
    movement_type_str = movement_type.value
    target_date_str = target_time.strftime("%Y-%m-%d")
    target_time_str = target_time.strftime("%H_%M")

    target_url = 'https://www.flightera.net/en/airport/' + \
                 quote(f'{airport_city}/{airport_id}/{movement_type_str}/{target_date_str} {target_time_str}')

    return target_url


def get_airline_table_html_one_page(airport_city: str, airport_id: str, movement_type: MovementType,
                                    target_time: datetime, trial_seconds=15):
    entrance_time = datetime.now()
    target_url = get_target_url(airport_city, airport_id, movement_type, target_time)
    headers = get_headers()
    wb_data = requests.get(target_url, headers=headers)
    soup = BeautifulSoup(wb_data.text, features="lxml")
    flight_table_html = soup.find('table')
    while flight_table_html is None:
        delta_seconds = (entrance_time.now() - entrance_time).total_seconds()
        if delta_seconds < trial_seconds:
            print(f'Failed to get the table in html page. {delta_seconds} seconds wasted. Retrying')
            wb_data = requests.get(target_url, headers=headers)
            soup = BeautifulSoup(wb_data.text, features="lxml")
            flight_table_html = soup.find('table')
        else:
            raise Exception("Time expires!")
    return flight_table_html


def analyze_time_data(column: BeautifulSoup):
    time_info = column.find_all('span')[0].get_text().split('\n')
    actual_time = time_info[1]
    time_zone = time_info[2]
    time_descriptor = column.find('div').get_text() if column.find('div') else ''
    time_matcher = re.match(r'((\d+) h )?(\d+) min (early|late)', time_descriptor)
    time_delta_minute = int(time_matcher.group(3)) if time_matcher else 0
    depart_time_delta_hour = int(time_matcher.group(2) or 0) if time_matcher else 0
    time_delta_total_minute = depart_time_delta_hour * 60 + time_delta_minute
    time_type = 'scheduled' if not time_descriptor else time_matcher.group(3)
    return actual_time, time_zone, time_delta_total_minute, time_type


def transform_airline_table(airport_city: str, airport_id: str, movement_type: MovementType,
                            flight_table_html: BeautifulSoup):
    data_rows = flight_table_html.find_all('tr', class_=re.compile(r'^bg.*'))[1:]
    for data_row in data_rows:
        columns = data_row.find_all('td')
        flight_status = columns[0].find('span', class_=re.compile(r'^badge.*')).get_text().strip()
        if flight_status == 'Landed':
            flight_date = columns[0].find('a', href=re.compile(r'.+')).get_text().strip()
            flight_code = columns[1].find('a', title='').get_text().strip()
            flight_code_alias = columns[1].find('span', class_='code-displ-left').get_text().strip() if columns[1].find(
                'span', class_='code-displ-left') else ''
            flight_details = columns[1].find('a', title=re.compile(r'.+')).get_text().strip()

            airport_info = columns[2].find_all('span', class_=re.compile('.*text-nowrap.*'))
            table_airport_city = airport_info[0].get_text().strip()
            table_airport_id = re.match(r'\((.*?)\)', airport_info[1].get_text().strip()).group(1).strip()

            flight_from_airport_city = airport_city if movement_type == MovementType.departure \
                else table_airport_city
            flight_from_airport_id = airport_id if movement_type == MovementType.departure else table_airport_id

            flight_to_airport_city = airport_city if movement_type == MovementType.arrival else table_airport_city
            flight_to_airport_id = airport_id if movement_type == MovementType.arrival else table_airport_id

            actual_depart_time, depart_time_zone, depart_time_delta_total_minute, depart_time_type = analyze_time_data(
                columns[4])

            actual_arrive_time, arrive_time_zone, arrive_time_delta_total_minute, arrive_time_type = analyze_time_data(
                columns[5])

            print(flight_date, flight_code, flight_code_alias, flight_details, flight_from_airport_city,
                  flight_from_airport_id, flight_to_airport_city, flight_to_airport_id, actual_depart_time,
                  depart_time_zone, depart_time_delta_total_minute, depart_time_type, actual_arrive_time,
                  arrive_time_zone, arrive_time_delta_total_minute, arrive_time_type)


def online_transform_one_step(airport_city: str, airport_id: str, movement_type: MovementType, target_time: datetime):
    # flight_table_html = get_airline_table_html_one_page(airport_city, airport_id, movement_type, target_time)
    # cache_file = open('cache.html', 'w', encoding='utf-8')
    # cache_file.write(str(flight_table_html))
    flight_table_html = BeautifulSoup(open('cache.html', 'r', encoding='utf-8').read(), features='lxml')
    transform_airline_table(airport_city, airport_id, movement_type, flight_table_html)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    online_transform_one_step('Shenzhen', 'ZGSZ', MovementType.arrival, datetime(2020, 8, 18, 18))

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
