import pandas as pd
import numpy as np
import json

def prepare_data(df):
    """подготовка данных"""
    #нужные колонки
    columns=['brand','name','bodyType','color','fuelType','year','power','price']
    df=df[columns].dropna()
    
    #фильтруем выбросы
    df=df[(df['price']>10000)&(df['price']<10000000)]
    df=df[(df['year']>1990)&(df['year']<=2024)]
    df=df[(df['power']>50)&(df['power']<1000)]
    
    #уникальные значения
    unique_data={
        'brands':sorted(df['brand'].astype(str).unique().tolist()),
        'models':{},
        'bodyTypes':sorted(df['bodyType'].astype(str).unique().tolist()),
        'colors':sorted(df['color'].astype(str).unique().tolist()),
        'fuelTypes':sorted(df['fuelType'].astype(str).unique().tolist()),
        'years':sorted(df['year'].astype(int).unique().tolist()),
        'min_power':int(df['power'].min()),
        'max_power':int(df['power'].max())
    }
    
    #модели по маркам
    for brand in unique_data['brands']:
        brand_models=df[df['brand']==brand]['name'].astype(str).unique()
        unique_data['models'][brand]=sorted(brand_models.tolist())
    
    #сохр для api
    with open('data/unique_values.json','w',encoding='utf-8')as f:
        json.dump(unique_data,f,ensure_ascii=False,indent=2)
    
    return df,unique_data