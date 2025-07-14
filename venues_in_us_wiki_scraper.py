import re
import calendar
import requests
import pendulum
import pandas as pd
import lxml.html as lx


# extract HTML from the Wikipedia page
url = 'https://en.wikipedia.org/wiki/List_of_music_venues_in_the_United_States'
response = requests.get(url)
html = lx.fromstring(response.content)

# skip the first row of the table
wiki_table = html.xpath('//table[contains(@class, "wikitable")]//tr[position() > 1]')


def clean_date(date_str):
    """
    Clean and convert date opened to 'YYYY-MM-DD' format where possible.
    """
    # return None if the date is unknown or empty
    if re.match(r'unknown|un\xadknown', date_str.lower()) or date_str == '':
        return None

    # if there are multiple comments, take the first one
    if ';' in date_str or ':' in date_str:
        date_str = re.split(r'[;:]', date_str)[0].lower()
    else:
        date_str = date_str.lower()

    # if the date starts with just a year, convert it to 'YYYY-01-01'
    if re.match(r'^\d{4}', date_str):
        date_str = re.search(r'(\d{4})', date_str).group(1)
        return f'{date_str}-01-01'

    # if the date is in the format 'Month Day, Year', convert it to 'YYYY-MM-DD'
    elif re.match(r'^\w+ \d{1,2}, \d{4}', date_opened):
        date_str = re.search(r'(\w+ \d{1,2}, \d{4})', date_str).group(1)
        return pendulum.parse(date_str, strict=False).date().isoformat()

    # if date_opened is in the format 'Month Year', convert it to 'YYYY-MM-DD'
    elif re.match(r'^\w+ \d{4}', date_opened):
        date_str = re.search(r'(\w+ \d{4})', date_str).group(1)
        if any(month.lower() in date_str for month in calendar.month_name[1:]):
            # if the month is in the date, convert it to 'YYYY-MM-DD'
            date_str = f'{date_str} 01'
            return pendulum.parse(date_str, strict=False).date().isoformat()
        else:
            # if the month is not in the date, assume January
            date_str = re.search(r'(\d{4})', date_str).group(1)
            return f'{date_str}-01-01'
    else:
        return date_str


# create a list to hold the parsed venue data
venue_list = []
for row in wiki_table:
    if row.xpath('count(*)=1 and count(th)=1'):
        # when the row is just a header, save the state and skip to the next row
        state = row.text_content().strip()
        continue

    # a complete row
    if row.xpath('count(td)=4'):
        date_opened = row.xpath('./td[1]')[0].text_content().strip()
        name = row.xpath('./td[2]')[0].text_content().strip()
        wiki_url = row.xpath('./td[2]/a/@href')[0] if row.xpath('./td[2]/a/@href') else None
        city = row.xpath('./td[3]')[0].text_content().strip()
        capacity = row.xpath('./td[4]')[0].text_content().strip()

    # case when a row is missing a city (carried over from the previous row)
    if row.xpath('count(td)=3'):
        date_opened = row.xpath('./td[1]')[0].text_content().strip()
        name = row.xpath('./td[2]')[0].text_content().strip()
        wiki_url = row.xpath('./td[2]/a/@href')[0] if row.xpath('./td[2]/a/@href') else None
        capacity = row.xpath('./td[3]')[0].text_content().strip()

    # case when a row is missing date opened (carried over from the previous row)
    if row.xpath('count(td)=2'):
        name = row.xpath('./td[1]')[0].text_content().strip()
        wiki_url = row.xpath('./td[1]/a/@href')[0] if row.xpath('./td[1]/a/@href') else None
        capacity = row.xpath('./td[2]')[0].text_content().strip()

    venue_list.append({'state': state,
                       'date_opened_raw': date_opened,
                       'date_opened_clean': clean_date(date_opened),
                       'name': name,
                       'wiki_url': f'https://en.wikipedia.org{wiki_url}' if wiki_url else None,
                       'city': city,
                       'capacity': capacity})

venues_df = pd.DataFrame(venue_list)
