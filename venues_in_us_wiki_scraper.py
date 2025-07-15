import re
import calendar
import requests
import pendulum
import pandas as pd
import lxml.html as lx

"""
Resources
- https://pandas.pydata.org/docs/reference/api/pandas.read_html.html#pandas-read-html
- Brave Search
"""

# extract HTML from the Wikipedia page
url = 'https://en.wikipedia.org/wiki/List_of_music_venues_in_the_United_States'

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
    elif re.match(r'^\w+ \d{1,2}, \d{4}', date_str):
        date_str = re.search(r'(\w+ \d{1,2}, \d{4})', date_str).group(1)
        return pendulum.parse(date_str, strict=False).date().isoformat()

    # if date_opened is in the format 'Month Year', convert it to 'YYYY-MM-DD'
    elif re.match(r'^\w+ \d{4}', date_str):
        date_str = re.search(r'(\w+ \d{4})', date_str).group(1)
        if any(month.lower() in date_str for month in calendar.month_name[1:]):
            # if the month is in the date, convert it to 'YYYY-MM-DD'
            date_str = f'{date_str} 01'
            return pendulum.parse(date_str, strict=False).date().isoformat()
        else:
            # if the month is not in the date, assume January
            date_str = re.search(r'(\d{4})', date_str).group(1)
            return f'{date_str}-01-01'
        # TODO: handle a case when date_str starts with 'c.' or 'circa' or 'c.' and a year
    else:
        return date_str

# use pandas to read the HTML table from the Wikipedia page
venues_df = pd.read_html(io=url, flavor='lxml', header=0, extract_links='all')[0]
venues_df.columns = ['opened', 'venue', 'city', 'capacity']

# extract_links='all' returns tuples for all columns
# extract the first element from the following columns
venues_df['opened'] = venues_df['opened'].str[0]
venues_df['city'] = venues_df['city'].str[0]
venues_df['capacity'] = venues_df['capacity'].str[0]

# extract the wikipedia URL first from the venue column only
wiki_url = venues_df['venue'].str[1]
wiki_url = wiki_url.apply(lambda x: f'https://en.wikipedia.org{x}' if x is not None else x)
# extract the venue name from the venue column
venues_df['venue'] = venues_df['venue'].str[0]

# create a state column since pd.read_html does not recognize <th> elements should be a repeating column
response = requests.get(url)
html = lx.fromstring(response.content)
# skip the first row of the table
wiki_table = html.xpath('//table[contains(@class, "wikitable")]//tr[position() > 1]')
state_list = []
for row in wiki_table:
    if row.xpath('count(*)=1 and count(th)=1'):
        state = row.text_content().strip()
    state_list.append(state)
state_col = pd.DataFrame(state_list, columns=['state'])

# add state to the beginning of the DataFrame
venues_df = pd.concat([state_col, venues_df], axis=1)

# remove rows where all columns are the same (state)
venues_df = venues_df[venues_df.nunique(axis=1) > 1]

# add the wiki_url column to the DataFrame based off index and then reset the index
venues_df = pd.concat([venues_df, wiki_url], axis=1, join='inner').reset_index(drop=True)

venues_df['opened_clean'] = venues_df['opened'].apply(clean_date)

# TODO: change order/name of columns, extract additional venue data from the wiki_url