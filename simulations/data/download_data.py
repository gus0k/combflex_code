from zipfile import ZipFile
import io
import datetime
import time
import requests
import pandas as pd

URL = ('https://www.ausgrid.com.au/-/media/Documents/Data-to-share/'
'Solar-home-electricity-data/Solar-home-half-hour-data---1-July-2012-to-30-June-2013.zip')

start = time.time()

r = requests.get(URL, stream=True)
file = ZipFile(io.BytesIO(r.content)) # unzip
filename = file.filelist[0].filename
raw = pd.read_csv(file.open(filename), skiprows=1) # first row is comment

raw = raw.drop(['Generator Capacity', 'Postcode', 'Row Quality'], axis=1)

tmp = pd.melt(raw, id_vars=['Customer', 'Consumption Category', 'date'])

tmp =  pd.pivot_table(tmp, index=['Customer', 'date', 'variable'],
                      columns='Consumption Category', values='value')

tmp['net'] = tmp['GC'] - tmp['GG'] + tmp['CL']
datetimes = [datetime.datetime.strptime(x[1] + x[2], '%d/%m/%Y%H:%M') for x in
             tmp.index]

tmp['datetime'] = datetimes

final = tmp.reset_index()[['Customer', 'datetime', 'net']].copy()
final.columns = ['customer', 'date', 'power']

final = final.dropna(axis=0)
final = final.sort_values(['customer', 'date'])

final.to_csv('customers_data.csv', index=None)


end =  time.time() - start
print(f'Elapsed time: {end:0.2f}')
