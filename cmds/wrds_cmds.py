import pandas as pd
import numpy as np
import datetime
import holidays




def process_wrds_treasury_data(rawdata,keys_extra=[]):

    DAYS_YEAR = 365.25
    FREQ = 2
    # could pull this directly from TNIPPY

    data = rawdata.copy()
    
    data.columns = data.columns.str.upper()

    data.sort_values('TMATDT',inplace=True)
    data.set_index('KYTREASNO',inplace=True)

    data = data[['CALDT','TDBID','TDASK','TDNOMPRC','TDACCINT','TDYLD','TDATDT','TMATDT','TCOUPRT','ITYPE','TDDURATN','TDPUBOUT','TDTOTOUT']]


    ### List issue type
    dict_type = {
        1: 'bond',
        2: 'note',
        4: 'bill',
        11: 'TIPS note',
        12: 'TIPS bond'
    }
    
    data['ITYPE'] = data['ITYPE'].replace(dict_type)
    

    ### Rename columns
    data.rename(columns={'CALDT':'quote date',
                         'TDATDT':'issue date',
                         'TMATDT':'maturity date',
                         'TCOUPRT':'cpn rate',
                         'TDTOTOUT':'total size',
                         'TDPUBOUT':'public size',
                         'TDDURATN':'duration',
                         'ITYPE':'type',
                         'TDBID':'bid',
                         'TDASK':'ask',
                         'TDNOMPRC':'price',
                         'TDACCINT':'accrued int',
                         'TDYLD':'ytm'
                        },inplace=True)


    ### Calculate time-to-maturity (TTM)
    data['maturity date'] = pd.to_datetime(data['maturity date'])
    data['issue date'] = pd.to_datetime(data['issue date'])
    data['quote date'] = pd.to_datetime(data['quote date'])
    data['ttm'] = (data['maturity date'] - data['quote date']).dt.days.astype(float)/DAYS_YEAR

    
    ### Dirty price
    data['dirty price'] = data['price'] + data['accrued int']    


    ### duration
    data['duration'] *= 365
    data['total size'] *= 1e6
    data['public size'] *= 1e6
    
    
    ### Annualize YTM for semi-compounding
    def tempfunc(x):
        return (np.exp(x*DAYS_YEAR/FREQ)-1)*FREQ

    data['ytm'] = data['ytm'].apply(tempfunc)

    
    ### accrual fraction
    data['accrual fraction'] = data['accrued int'] / (data['cpn rate'] / FREQ)

    idx = data['accrual fraction'].isna()
    data.loc[idx,'accrual fraction'] = 1 - (data.loc[idx,'ttm']-round(data.loc[idx,'ttm']))*FREQ

    
    ### Reorganize columns
    keys = ['type',
            'quote date',
            'issue date',
            'total size',
            'public size',
            'maturity date',
            'ttm',
            'accrual fraction',
            'cpn rate',
            'bid',
            'ask',
            'price',
            'accrued int',
            'dirty price',
            'ytm']
    
    data = data[keys+keys_extra]

    
    return data            







from pandas.tseries.offsets import DateOffset




def select_maturities(rawdata,periods=20,freq='6ME'):

    data = rawdata.copy()[['quote date','issue date','maturity date']]
    
    # Convert DATE and columns in 'data' to datetime
    DATE = data['quote date'].iloc[0]
    DAYS_YEAR = 365

    FREQ = freq

    # Generate 6-month intervals from DATE
    six_month_intervals = pd.date_range(start=DATE, periods=periods+1, freq=FREQ)[1:]
    
    
    def find_closest_date(interval, data):
    
        # Calculate the absolute difference between each MATURITY date and the interval
        data['difference'] = abs(data['maturity date'] - interval)
        
        # Ensure we only consider future dates relative to DATE
        DATE = data['quote date'].iloc[0]
        future_dates = data[data['maturity date'] > DATE]
        if not future_dates.empty:
            # Find the row with the minimum difference
            min_diff = future_dates['difference'].min()
            closest_dates = future_dates[future_dates['difference'] == min_diff]
            # Resolve ties by 'tdatdt' date
            return closest_dates.sort_values('issue date', ascending=False).iloc[0]
            
        return None
    
    # Apply the function to each interval
    selected_rows = [find_closest_date(interval, data) for interval in six_month_intervals]
    
    # Remove None values and ensure uniqueness
    selected_rows = [row for row in selected_rows if row is not None]
    select_ids = [row.name for row in selected_rows]

    # algorithm includes
    #select_ids = select_ids[1:]
    return select_ids



