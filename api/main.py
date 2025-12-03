from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from typing import List,Dict,Optional
import uvicorn
import numpy as np
import pickle
from tensorflow import keras
import json
import sqlite3
import hashlib
from datetime import datetime

#модели данных
class CarRequest(BaseModel):
    brand:str
    name:str
    bodyType:str
    color:str
    fuelType:str
    year:int
    power:int

class PredictionResponse(BaseModel):
    predicted_price:float
    currency:str="RUB"
    log_price:float

class CreditRequest(BaseModel):
    car_price:float
    down_payment:float
    loan_term_months:int=60
    interest_rate:float=8.5

class CreditResponse(BaseModel):
    monthly_payment:float
    total_interest:float
    total_payment:float
    overpayment_percent:float

class HistoryRecord(BaseModel):
    id:str
    timestamp:str
    car_data:dict
    predicted_price:float

#загружаем модель
MODEL_PATH='car_price_model.keras'
SCALER_PATH='scaler.pkl'
ENCODERS_PATH='encoders.pkl'
FEATURE_INFO_PATH='feature_info.pkl'
UNIQUE_VALUES_PATH='unique_values.json'
CAR_INDEX_PATH='car_index.json'

model=keras.models.load_model(MODEL_PATH)

with open(SCALER_PATH,'rb')as f:
    scaler=pickle.load(f)

with open(ENCODERS_PATH,'rb')as f:
    encoders=pickle.load(f)

with open(FEATURE_INFO_PATH,'rb')as f:
    feature_info=pickle.load(f)

with open(UNIQUE_VALUES_PATH,'r',encoding='utf-8')as f:
    unique_data=json.load(f)

try:
    with open(CAR_INDEX_PATH,'r',encoding='utf-8')as f:
        car_index=json.load(f)
except:
    car_index=[]
    
#БД для истории
def init_history_db():
    conn=sqlite3.connect('history.db')
    cursor=conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions(
            id TEXT PRIMARY KEY,
            timestamp TEXT,
            brand TEXT,
            model TEXT,
            year INTEGER,
            power INTEGER,
            body_type TEXT,
            color TEXT,
            fuel_type TEXT,
            predicted_price REAL
        )
    ''')
    conn.commit()
    conn.close()

init_history_db()

#fastapi приложение
app=FastAPI(title="car price prediction api",version="1.0")

@app.get("/")
def root():
    return{"message":"car price prediction api","version":"1.0"}

@app.get("/health")
def health():
    return{"status":"ok"}

@app.get("/brands")
def get_brands():
    return{"brands":unique_data['brands']}

@app.get("/models/{brand}")
def get_models(brand:str):
    if brand in unique_data['models']:
        return{"brand":brand,"models":unique_data['models'][brand]}
    raise HTTPException(status_code=404,detail=f"марка{brand}не найдена")

@app.get("/unique_values")
def get_unique_values():
    return{
        "bodyTypes":unique_data['bodyTypes'],
        "colors":unique_data['colors'],
        "fuelTypes":unique_data['fuelTypes'],
        "years":unique_data['years'],
        "power_range":{
            "min":unique_data['min_power'],
            "max":unique_data['max_power']
        }
    }

def save_to_history(car_data:dict,predicted_price:float):
    try:
        unique_str=f"{car_data}{datetime.now()}"
        record_id=hashlib.md5(unique_str.encode()).hexdigest()[:10]
        
        conn=sqlite3.connect('history.db')
        cursor=conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO predictions
            (id,timestamp,brand,model,year,power,body_type,color,fuel_type,predicted_price)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        ''',(
            record_id,
            datetime.now().isoformat(),
            car_data.get('brand'),
            car_data.get('name'),
            car_data.get('year'),
            car_data.get('power'),
            car_data.get('bodyType'),
            car_data.get('color'),
            car_data.get('fuelType'),
            float(predicted_price)
        ))
        
        conn.commit()
        conn.close()
        return record_id
    except:
        return None

@app.post("/predict",response_model=PredictionResponse)
def predict(car:CarRequest):
    try:
        car_data={
            'brand':car.brand,
            'name':car.name,
            'bodyType':car.bodyType,
            'color':car.color,
            'fuelType':car.fuelType,
            'year':car.year,
            'power':car.power
        }
        
        categorical_features=[]
        for col in feature_info['categorical_cols']:
            value=car_data[col]
            encoder=encoders[col]
            
            if value in encoder.classes_:
                encoded=encoder.transform([value])[0]
            else:
                encoded=encoder.transform([encoder.classes_[0]])[0]
            categorical_features.append(encoded)
        
        numerical_features=[[car.year,car.power]]
        scaled_numerical=scaler.transform(numerical_features)[0]
        features=np.hstack([scaled_numerical,categorical_features]).reshape(1,-1)
        
        pred_log=model.predict(features,verbose=0)[0][0]
        pred_price=np.expm1(pred_log)
        
        #сохранение в историю
        save_to_history(car_data,float(pred_price))
        
        return PredictionResponse(
            predicted_price=float(pred_price),
            log_price=float(pred_log)
        )
        
    except Exception as e:
        raise HTTPException(status_code=400,detail=str(e))

@app.post("/calculate_credit",response_model=CreditResponse)
def calculate_credit(credit_request:CreditRequest):
    try:
        car_price=credit_request.car_price
        down_payment=credit_request.down_payment
        loan_amount=car_price-down_payment
        
        if loan_amount<=0:
            raise HTTPException(status_code=400,detail="сумма кредита должна быть больше 0")
        
        monthly_rate=credit_request.interest_rate/100/12
        loan_term=credit_request.loan_term_months
        
        monthly_payment=loan_amount*(
            monthly_rate*(1+monthly_rate)**loan_term
        )/((1+monthly_rate)**loan_term-1)
        
        total_payment=monthly_payment*loan_term
        total_interest=total_payment-loan_amount
        overpayment_percent=(total_interest/loan_amount)*100
        
        return CreditResponse(
            monthly_payment=round(monthly_payment,2),
            total_interest=round(total_interest,2),
            total_payment=round(total_payment,2),
            overpayment_percent=round(overpayment_percent,2)
        )
        
    except Exception as e:
        raise HTTPException(status_code=400,detail=str(e))

@app.get("/history",response_model=List[HistoryRecord])
def get_history(limit:int=10,offset:int=0):
    try:
        conn=sqlite3.connect('history.db')
        cursor=conn.cursor()
        
        cursor.execute('''
            SELECT*FROM predictions
            ORDER BY timestamp DESC
            LIMIT?OFFSET?
        ''',(limit,offset))
        
        rows=cursor.fetchall()
        conn.close()
        
        history=[]
        for row in rows:
            record=HistoryRecord(
                id=row[0],
                timestamp=row[1],
                car_data={
                    'brand':row[2],
                    'name':row[3],
                    'year':row[4],
                    'power':row[5],
                    'bodyType':row[6],
                    'color':row[7],
                    'fuelType':row[8]
                },
                predicted_price=row[9]
            )
            history.append(record)
        
        return history
        
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))

@app.delete("/history/{record_id}")
def delete_history_record(record_id:str):
    try:
        conn=sqlite3.connect('history.db')
        cursor=conn.cursor()
        
        cursor.execute('DELETE FROM predictions WHERE id=?',(record_id,))
        deleted=cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return{"deleted":deleted>0}
        
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))

@app.get("/metrics")
def get_metrics():
    return feature_info['metrics']

if __name__=="__main__":
    uvicorn.run(app,host="0.0.0.0",port=8000)