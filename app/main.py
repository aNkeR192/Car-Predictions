import gradio as gr
import requests
import json
from typing import Dict,List

class CarPriceApp:
    def __init__(self,api_url="http://localhost:8000"):
        self.api_url=api_url
        self.brands=[]
        self.models_data={}
        self.other_data={}
        self.load_initial_data()
        self.init_local_history()

    def init_local_history(self):
        try:
            with open('local_history.json','r',encoding='utf-8')as f:
                pass
        except:
            with open('local_history.json','w',encoding='utf-8')as f:
                json.dump([],f,ensure_ascii=False,indent=2)

    def load_initial_data(self):
        try:
            response=requests.get(f"{self.api_url}/brands",timeout=5)
            if response.status_code==200:
                self.brands=response.json().get('brands',[])
                self.brands=sorted(self.brands,key=lambda x:str(x).lower())

            response=requests.get(f"{self.api_url}/unique_values",timeout=5)
            if response.status_code==200:
                self.other_data=response.json()

            print(f"✓загружено{len(self.brands)}марок")

        except Exception as e:
            print(f"✗ошибка загрузки данных:{e}")
            self.brands=["Toyota","BMW","Lada","Kia","Hyundai","Mercedes","Audi","Volkswagen"]
            self.other_data={
                'bodyTypes':['седан','внедорожник','хэтчбек','универсал','купе','кабриолет'],
                'colors':['белый','черный','серебристый','серый','синий','красный'],
                'fuelTypes':['бензин','дизель','гибрид','электро'],
                'years':list(range(1995,2025)),
                'power_range':{'min':60,'max':600}
            }

    def get_models_for_brand(self,brand):
        if not brand:
            return[]

        try:
            if brand in self.models_data:
                return self.models_data[brand]

            response=requests.get(f"{self.api_url}/models/{brand}",timeout=5)
            if response.status_code==200:
                models=response.json().get('models',[])
                models=sorted(models,key=lambda x:str(x).lower())
                self.models_data[brand]=models
                return models
            return[]

        except:
            return[]

    def predict_price(self,brand,model,body_type,color,fuel_type,year,power):
        if not all([brand,model,body_type,color,fuel_type,year,power]):
            return"❌Заполните все поля",{},{}

        car_data={
            "brand":brand,
            "name":model,
            "bodyType":body_type,
            "color":color,
            "fuelType":fuel_type,
            "year":int(year),
            "power":int(power)
        }

        try:
            response=requests.post(f"{self.api_url}/predict",
                                   json=car_data,
                                   timeout=10)

            if response.status_code==200:
                result=response.json()
                price=result['predicted_price']

                formatted_price=f"₽{price:,.0f}".replace(',',' ')

                details={
                    "Марка":brand,
                    "Модель":model,
                    "Год выпуска":year,
                    "Мощность":f"{power}л.с.",
                    "Тип кузова":body_type,
                    "Цвет":color,
                    "Тип топлива":fuel_type
                }

                recommendation=self.get_recommendation(price,year,power)

                self.save_to_local_history(brand,model,year,power,body_type,color,fuel_type,price)

                return formatted_price,details,recommendation
            else:
                error_detail=response.json().get('detail','Неизвестная ошибка')
                return f"❌Ошибка API:{error_detail}",{},{}

        except Exception as e:
            print(f"API недоступен,используем локальную историю")
            
            base_price=1000000
            year_multiplier=1+(int(year)-2010)*0.05
            power_multiplier=1+(int(power)-100)*0.002
            price=base_price*year_multiplier*power_multiplier
            
            self.save_to_local_history(brand,model,year,power,body_type,color,fuel_type,price)
            
            formatted_price=f"₽{price:,.0f}".replace(',',' ')
            
            details={
                "Марка":brand,
                "Модель":model,
                "Год выпуска":year,
                "Мощность":f"{power}л.с.",
                "Тип кузова":body_type,
                "Цвет":color,
                "Тип топлива":fuel_type,
                "ℹ️":"Цена рассчитана локально(API недоступен)"
            }
            
            recommendation=self.get_recommendation(price,year,power)
            
            return formatted_price,details,recommendation
    
    def save_to_local_history(self,brand,model,year,power,body_type,color,fuel_type,price):
        try:
            import time
            history=self.load_local_history()
            
            record={
                "id":str(int(time.time())),
                "timestamp":time.strftime("%Y-%m-%d %H:%M:%S"),
                "car_data":{
                    "brand":brand,
                    "name":model,
                    "year":int(year),
                    "power":int(power),
                    "bodyType":body_type,
                    "color":color,
                    "fuelType":fuel_type
                },
                "predicted_price":float(price)
            }
            
            history.insert(0,record)
            if len(history)>50:
                history=history[:50]
                
            self.save_local_history(history)
            return True
        except Exception as e:
            print(f"Ошибка сохранения истории:{e}")
            return False

    def get_recommendation(self,price,year,power):
        current_year=2024
        age=current_year-year

        recommendations=[]

        if age>15:
            recommendations.append("🚨Автомобиль старше 15 лет-могут быть проблемы с запчастями")
        elif age>10:
            recommendations.append("⚠️Автомобиль старше 10 лет-проверьте техническое состояние")
        else:
            recommendations.append("✅Автомобиль относительно новый")

        if power>300:
            recommendations.append("⚡Высокая мощность-повышенный расход топлива")
        elif power<100:
            recommendations.append("🐌Низкая мощность-может не хватать для динамичной езды")
        else:
            recommendations.append("⚖️Оптимальная мощность для города")

        return"\n".join(recommendations)
    
    def calculate_credit(self,car_price,down_payment,loan_term,interest_rate):
        try:
            car_price=float(car_price)
            down_payment=float(down_payment)
            loan_term=int(loan_term)
            interest_rate=float(interest_rate)
            
            if car_price<=0:
                return None
            if down_payment<0 or down_payment>=car_price:
                return None
            if loan_term<12 or loan_term>84:
                return None
            if interest_rate<5 or interest_rate>20:
                return None
            
            loan_amount=car_price-down_payment
            monthly_rate=interest_rate/100/12
            
            monthly_payment=loan_amount*(
                monthly_rate*(1+monthly_rate)**loan_term
            )/((1+monthly_rate)**loan_term-1)
            
            total_payment=monthly_payment*loan_term
            total_interest=total_payment-loan_amount
            overpayment_percent=(total_interest/loan_amount)*100
            
            return{
                "monthly_payment":round(monthly_payment,2),
                "total_interest":round(total_interest,2),
                "total_payment":round(total_payment,2),
                "overpayment_percent":round(overpayment_percent,2),
                "loan_amount":round(loan_amount,2)
            }
        except:
            return None
    
    def load_history(self):
        try:
            response=requests.get(f"{self.api_url}/history?limit=20",timeout=3)
            if response.status_code==200:
                return response.json()
        except:
            pass
        
        return self.load_local_history()
    
    def load_local_history(self):
        try:
            with open('local_history.json','r',encoding='utf-8')as f:
                history=json.load(f)
                if isinstance(history,list):
                    return history
                else:
                    return[]
        except Exception as e:
            print(f"Ошибка загрузки истории:{e}")
            return[]
    
    def save_local_history(self,history):
        try:
            with open('local_history.json','w',encoding='utf-8')as f:
                json.dump(history,f,ensure_ascii=False,indent=2)
            return True
        except Exception as e:
            print(f"Ошибка сохранения истории:{e}")
            return False
    
    def clear_history(self):
        try:
            response=requests.get(f"{self.api_url}/history",timeout=3)
            if response.status_code==200:
                history=response.json()
                deleted=0
                for record in history:
                    try:
                        requests.delete(f"{self.api_url}/history/{record['id']}",timeout=2)
                        deleted+=1
                    except:
                        continue
                if deleted>0:
                    print(f"Удалено{deleted}записей из API истории")
                    return True
        except:
            pass
        
        success=self.save_local_history([])
        if success:
            print("Локальная история очищена")
        return success

    def create_interface(self):
        with gr.Blocks(
            title="🚗Предсказатель цен на автомобили",
            theme=gr.themes.Soft(
                primary_hue="blue",
                secondary_hue="purple",
                font=[gr.themes.GoogleFont("Inter"),"ui-sans-serif","system-ui"]
            ),
            css="""
            .main-container{padding:20px;}
            .price-card{
                background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
                border-radius:15px;padding:25px;margin:20px 0;
                color:white;text-align:center;
                box-shadow:0 10px 30px rgba(0,0,0,0.2);
            }
            .price-text{font-size:42px;font-weight:800;margin:10px 0;}
            .details-card{
                background:white;border-radius:12px;padding:20px;margin:15px 0;
                border:1px solid #e5e7eb;box-shadow:0 4px 6px rgba(0,0,0,0.05);
            }
            .recommendation-card{
                background:linear-gradient(135deg,#4facfe 0%,#00f2fe 100%);
                border-radius:12px;padding:20px;margin:15px 0;color:white;
            }
            .section-title{font-size:18px;font-weight:600;margin-bottom:15px;color:#374151;}
            .example-btn{margin:5px;transition:all 0.3s ease;}
            .example-btn:hover{transform:translateY(-2px);box-shadow:0 5px 15px rgba(0,0,0,0.1);}
            .credit-summary{
                background:linear-gradient(135deg,#4CAF50 0%,#2E7D32 100%);
                color:white;border-radius:10px;padding:20px;margin:15px 0;
            }
            .history-item{
                background:white;border-radius:10px;padding:15px;margin:10px 0;
                border-left:4px solid #667eea;box-shadow:0 2px 4px rgba(0,0,0,0.1);
            }
            """
        )as app:

            gr.HTML("""
            <div style="text-align:center;padding:20px 0;">
                <h1 style="font-size:36px;margin-bottom:10px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                    🚗Предсказатель цен на автомобили
                </h1>
                <p style="color:#6b7280;font-size:16px;">
                    На основе данных о 1.3 миллиона автомобилей•Точность предсказания 85%
                </p>
            </div>
            """)
            
            with gr.Tabs():
                with gr.TabItem("🎯Предсказание"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("###📋Характеристики автомобиля")
                            with gr.Group():
                                brand_input=gr.Dropdown(
                                    choices=self.brands,
                                    label="Марка",
                                    interactive=True,
                                    filterable=True,
                                    info="Выберите марку автомобиля",
                                    elem_id="brand_select"
                                )
                                model_input=gr.Dropdown(
                                    choices=[],
                                    label="Модель",
                                    interactive=False,
                                    filterable=True,
                                    info="Выберите модель",
                                    elem_id="model_select"
                                )
                            with gr.Row():
                                year_input=gr.Dropdown(
                                    choices=self.other_data.get('years',list(range(1995,2025))),
                                    label="Год выпуска",
                                    value=2020,
                                    interactive=True
                                )
                                power_input=gr.Slider(
                                    minimum=self.other_data.get('power_range',{}).get('min',60),
                                    maximum=self.other_data.get('power_range',{}).get('max',600),
                                    value=150,
                                    step=10,
                                    label="Мощность(л.с.)",
                                    interactive=True
                                )
                            with gr.Row():
                                body_input=gr.Dropdown(
                                    choices=self.other_data.get('bodyTypes',[]),
                                    label="Тип кузова",
                                    value="седан",
                                    interactive=True
                                )
                                color_input=gr.Dropdown(
                                    choices=self.other_data.get('colors',[]),
                                    label="Цвет",
                                    value="белый",
                                    interactive=True
                                )
                            fuel_input=gr.Dropdown(
                                choices=self.other_data.get('fuelTypes',[]),
                                label="Тип топлива",
                                value="бензин",
                                interactive=True
                            )
                            predict_btn=gr.Button(
                                "🎯Предсказать цену",
                                variant="primary",
                                size="lg",
                                elem_id="predict_btn"
                            )
                        with gr.Column(scale=1):
                            gr.Markdown("###💰Результат предсказания")
                            price_output=gr.HTML("""
                            <div class="price-card">
                                <div style="font-size:18px;opacity:0.9;">Предсказанная стоимость</div>
                                <div class="price-text">₽—</div>
                                <div style="font-size:14px;opacity:0.8;">На основе анализа рыночных данных</div>
                            </div>
                            """)
                            gr.Markdown("####📊Детали запроса")
                            details_output=gr.JSON(label="",value={})
                            recommendation_output=gr.HTML("""
                            <div class="recommendation-card">
                                <div style="font-size:16px;font-weight:600;margin-bottom:10px;">💡Рекомендации</div>
                                <div>Заполните данные для получения рекомендаций</div>
                            </div>
                            """)
                    with gr.Row():
                        gr.Markdown("###🚀Быстрые примеры")
                    def load_example_and_predict(brand,model,year,power,body,color,fuel):
                        models=self.get_models_for_brand(brand)
                        updates=[
                            gr.update(value=brand),
                            gr.update(value=model,choices=models if models else[]),
                            gr.update(value=year),
                            gr.update(value=power),
                            gr.update(value=body),
                            gr.update(value=color),
                            gr.update(value=fuel)
                        ]
                        price,details,recommendation=self.predict_price(brand,model,body,color,fuel,year,power)
                        price_html=f"""
                        <div class="price-card">
                            <div style="font-size:18px;opacity:0.9;">Предсказанная стоимость</div>
                            <div class="price-text">{price if'₽'in str(price)else'₽—'}</div>
                            <div style="font-size:14px;opacity:0.8;">На основе анализа рыночных данных</div>
                        </div>
                        """
                        rec_html=f"""
                        <div class="recommendation-card">
                            <div style="font-size:16px;font-weight:600;margin-bottom:10px;">💡Рекомендации</div>
                            <div>{recommendation}</div>
                        </div>
                        """if recommendation else""
                        return updates+[price_html,details,rec_html]
                    with gr.Row():
                        examples=[
                            ("Toyota","Camry",2020,249,"седан","белый","бензин"),
                            ("BMW","X5",2019,340,"внедорожник","черный","бензин"),
                            ("Лада","Веста",2021,106,"седан","серебристый","бензин"),
                            ("Kia","Rio",2018,123,"седан","красный","бензин"),
                            ("Mercedes-Benz","E-Class",2020,299,"седан","черный","дизель"),
                            ("Audi","A4",2019,190,"седан","синий","бензин")
                        ]
                        for brand_ex,model_ex,year_ex,power_ex,body_ex,color_ex,fuel_ex in examples:
                            btn=gr.Button(f"{brand_ex}{model_ex}",size="sm",variant="secondary",min_width=120)
                            btn.click(
                                fn=lambda b=brand_ex,m=model_ex,y=year_ex,p=power_ex,bt=body_ex,c=color_ex,f=fuel_ex:load_example_and_predict(b,m,y,p,bt,c,f),
                                inputs=[],
                                outputs=[brand_input,model_input,year_input,power_input,body_input,color_input,fuel_input,price_output,details_output,recommendation_output]
                            )
                with gr.TabItem("💰Кредит"):
                    with gr.Column():
                        gr.Markdown("###💰Кредитный калькулятор")
                        with gr.Row():
                            car_price_input=gr.Number(label="Стоимость автомобиля(руб)",value=1000000,minimum=10000,step=10000)
                            down_payment_input=gr.Number(label="Первоначальный взнос(руб)",value=200000,minimum=0,step=10000)
                        with gr.Row():
                            loan_term_input=gr.Slider(label="Срок кредита(месяцев)",minimum=12,maximum=84,value=60,step=12)
                            interest_rate_input=gr.Slider(label="Процентная ставка(%)",minimum=5,maximum=20,value=8.5,step=0.1)
                        calculate_credit_btn=gr.Button("📊Рассчитать кредит",variant="primary",size="lg")
                        credit_output=gr.HTML("""
                        <div class="credit-summary">
                            <div style="text-align:center;">
                                <div style="font-size:20px;margin-bottom:10px;">Результаты расчета</div>
                                <div style="font-size:32px;font-weight:bold;">—</div>
                                <div style="font-size:14px;opacity:0.9;">ежемесячный платеж</div>
                            </div>
                        </div>
                        """)
                        credit_details=gr.JSON(label="Детали кредита",value={})
                with gr.TabItem("📋История"):
                    with gr.Column():
                        gr.Markdown("###📋История предсказаний")
                        with gr.Row():
                            refresh_history_btn=gr.Button("🔄Обновить",variant="secondary",size="sm")
                            clear_history_btn=gr.Button("🗑️Очистить",variant="secondary",size="sm")
                        history_output=gr.HTML("""
                        <div style="text-align:center;padding:40px;color:#6b7280;">
                            <div style="font-size:48px;margin-bottom:20px;">📋</div>
                            <div style="font-size:18px;font-weight:500;">Загрузка истории...</div>
                        </div>
                        """)

            with gr.Row():
                with gr.Column():
                    gr.Markdown("###ℹ️О сервисе")
                    gr.Markdown("""
                    **Как это работает:**
                    -Нейросеть анализирует 1.3 миллиона автомобилей
                    -Учитывает 7 ключевых параметров
                    -Обновление данных в реальном времени
                    -Точность предсказания:85%

                    **Факторы влияющие на цену:**
                    🥇Марка и модель(премиум бренды дороже)
                    📅Год выпуска(новые дороже)
                    🐎Мощность двигателя
                    🚙Тип кузова
                    🎨Цвет(металлик дороже)
                    ⛽Тип топлива
                    """)

            def update_model_dropdown(brand):
                models=self.get_models_for_brand(brand)
                if models:
                    return gr.Dropdown(choices=models,value=None,interactive=True)
                return gr.Dropdown(choices=[],value=None,interactive=False)

            brand_input.change(fn=update_model_dropdown,inputs=brand_input,outputs=model_input)

            def process_prediction(brand,model,body_type,color,fuel_type,year,power):
                price,details,recommendation=self.predict_price(brand,model,body_type,color,fuel_type,year,power)
                price_html=f"""
                <div class="price-card">
                    <div style="font-size:18px;opacity:0.9;">Предсказанная стоимость</div>
                    <div class="price-text">{price}</div>
                    <div style="font-size:14px;opacity:0.8;">На основе анализа рыночных данных</div>
                </div>
                """
                rec_html=f"""
                <div class="recommendation-card">
                    <div style="font-size:16px;font-weight:600;margin-bottom:10px;">💡Рекомендации</div>
                    <div>{recommendation}</div>
                </div>
                """if recommendation else""
                return price_html,details,rec_html

            predict_btn.click(fn=process_prediction,inputs=[brand_input,model_input,body_input,color_input,fuel_input,year_input,power_input],outputs=[price_output,details_output,recommendation_output])
            
            def calculate_credit_handler(car_price,down_payment,loan_term,interest_rate):
                result=self.calculate_credit(car_price,down_payment,loan_term,interest_rate)
                if result:
                    credit_html=f"""
                    <div class="credit-summary">
                        <div style="text-align:center;">
                            <div style="font-size:20px;margin-bottom:10px;">Результаты расчета</div>
                            <div style="font-size:32px;font-weight:bold;">₽{result['monthly_payment']:,.0f}</div>
                            <div style="font-size:14px;opacity:0.9;">ежемесячный платеж</div>
                            <div style="margin-top:15px;font-size:14px;">
                                Переплата:₽{result['total_interest']:,.0f}({result['overpayment_percent']:.1f}%)
                            </div>
                        </div>
                    </div>
                    """
                    details={
                        "Сумма кредита":f"₽{result['loan_amount']:,.0f}",
                        "Ежемесячный платеж":f"₽{result['monthly_payment']:,.0f}",
                        "Общая сумма выплат":f"₽{result['total_payment']:,.0f}",
                        "Переплата":f"₽{result['total_interest']:,.0f}({result['overpayment_percent']:.1f}%)",
                        "Процентная ставка":f"{interest_rate}%",
                        "Срок кредита":f"{loan_term}месяцев"
                    }
                    return credit_html,details
                else:
                    error_html="""
                    <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:20px;color:#991b1b;">
                        <div style="font-size:20px;margin-bottom:10px;">❌Ошибка расчета</div>
                        <div>Проверьте введенные данные:</div>
                        <div>•Стоимость должна быть больше 0</div>
                        <div>•Первоначальный взнос должен быть меньше стоимости</div>
                        <div>•Срок кредита от 12 до 84 месяцев</div>
                        <div>•Процентная ставка от 5% до 20%</div>
                    </div>
                    """
                    return error_html,{}
            
            calculate_credit_btn.click(fn=calculate_credit_handler,inputs=[car_price_input,down_payment_input,loan_term_input,interest_rate_input],outputs=[credit_output,credit_details])
            
            def load_history_handler():
                history=self.load_history()
                if not history:
                    return"""
                    <div style="text-align:center;padding:40px;color:#6b7280;">
                        <div style="font-size:48px;margin-bottom:20px;">📭</div>
                        <div style="font-size:18px;font-weight:500;">История пуста</div>
                        <div style="font-size:14px;">Сделайте первое предсказание!</div>
                    </div>
                    """
                history_html="<div style='margin-top:20px;'>"
                for record in history:
                    car=record['car_data']
                    timestamp=record['timestamp']
                    if'T'in timestamp:
                        timestamp=timestamp.split('T')[0]
                    history_html+=f"""
                    <div class="history-item">
                        <div style="display:flex;justify-content:space-between;align-items:start;">
                            <div>
                                <div style="font-size:16px;font-weight:600;color:#374151;">
                                    {car['brand']}{car['name']}
                                </div>
                                <div style="font-size:14px;color:#6b7280;margin-top:5px;">
                                    {car['year']}•{car['power']}л.с.•{car['bodyType']}•{car['color']}
                                </div>
                                <div style="font-size:12px;color:#9CA3AF;margin-top:5px;">
                                    {timestamp}
                                </div>
                            </div>
                            <div style="text-align:right;">
                                <div style="font-size:18px;font-weight:700;color:#667eea;">
                                    ₽{record['predicted_price']:,.0f}
                                </div>
                            </div>
                        </div>
                    </div>
                    """
                history_html+="</div>"
                return history_html
            
            def clear_history_handler():
                success=self.clear_history()
                if success:
                    return"""
                    <div style="text-align:center;padding:40px;color:#6b7280;">
                        <div style="font-size:48px;margin-bottom:20px;">🗑️</div>
                        <div style="font-size:18px;font-weight:500;">История очищена</div>
                    </div>
                    """
                return load_history_handler()
            
            refresh_history_btn.click(fn=load_history_handler,inputs=[],outputs=history_output)
            clear_history_btn.click(fn=clear_history_handler,inputs=[],outputs=history_output)

            @app.load
            def on_load():
                return gr.update(choices=self.brands)

            return app

if __name__=="__main__":
    import sys
    in_colab='google.colab'in sys.modules
    app_instance=CarPriceApp()
    interface=app_instance.create_interface()
    if in_colab:
        interface.launch(share=True,debug=True)
    else:
        interface.launch(server_name="0.0.0.0",server_port=7860,share=False,show_error=True)