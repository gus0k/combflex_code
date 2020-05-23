import datetime

INTERVAL = 2
CANT = 100
FIRSTDAY = datetime.date(2012, 8, 1)
TIMEDELTA = datetime.timedelta(days=INTERVAL)


DATES = [str(FIRSTDAY + (TIMEDELTA * x)) for x in range(1, CANT)]

for dt in DATES:
    print(dt)
