import pickle
import json
import numpy as np
from sklearn.preprocessing import LabelEncoder,StandardScaler
from sklearn.model_selection import train_test_split
from tensorflow import keras
from tensorflow.keras import layers,callbacks

def create_and_train_model(df):
    """обучение модели"""
    #категориальные и числовые признаки
    categorical_cols=['brand','name','bodyType','color','fuelType']
    numerical_cols=['year','power']
    
    #кодирование категориальных признаков
    encoders={}
    encoded_features=[]
    
    for col in categorical_cols:
        le=LabelEncoder()
        encoded=le.fit_transform(df[col])
        encoded_features.append(encoded.reshape(-1,1))
        encoders[col]=le
    
    #масштабирование числовых
    scaler=StandardScaler()
    scaled_numerical=scaler.fit_transform(df[numerical_cols])
    
    #объединяем фичи
    X_categorical=np.hstack(encoded_features)
    X_numerical=scaled_numerical
    X=np.hstack([X_numerical,X_categorical])
    
    #целевая переменная
    y=np.log1p(df['price'].values)
    
    #разделение
    X_train,X_test,y_train,y_test=train_test_split(
        X,y,test_size=0.2,random_state=42
    )
    
    #создание модели
    input_dim=X_train.shape[1]
    model=keras.Sequential([
        layers.Dense(128,activation='relu',input_dim=input_dim),
        layers.Dropout(0.3),
        layers.Dense(64,activation='relu'),
        layers.Dropout(0.2),
        layers.Dense(32,activation='relu'),
        layers.Dense(1)
    ])
    
    model.compile(
        optimizer='adam',
        loss='mse',
        metrics=['mae',keras.metrics.RootMeanSquaredError()]
    )
    
    #обучение
    early_stopping=callbacks.EarlyStopping(
        monitor='val_loss',
        patience=10,
        restore_best_weights=True
    )
    
    history=model.fit(
        X_train,y_train,
        validation_split=0.2,
        epochs=50,
        batch_size=32,
        callbacks=[early_stopping],
        verbose=1
    )
    
    #оценка
    test_loss,test_mae,test_rmse=model.evaluate(X_test,y_test,verbose=0)
    
    #сохранение модели
    model.save('models/car_price_model.keras')
    
    with open('models/scaler.pkl','wb')as f:
        pickle.dump(scaler,f)
    
    with open('models/encoders.pkl','wb')as f:
        pickle.dump(encoders,f)
    
    #информация о фичах
    feature_info={
        'categorical_cols':categorical_cols,
        'numerical_cols':numerical_cols,
        'input_dim':input_dim,
        'metrics':{
            'test_mae':float(test_mae),
            'test_rmse':float(test_rmse),
            'test_loss':float(test_loss)
        }
    }
    
    with open('models/feature_info.pkl','wb')as f:
        pickle.dump(feature_info,f)
    
    print(f"модель обучена,mae:{test_mae:.4f}")
    return model,scaler,encoders,feature_info