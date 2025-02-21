
import ipywidgets as widgets
from IPython.display import display
import pandas as pd
import streamlit as st
import numpy as np
from datetime import datetime
import seaborn as sns
import matplotlib.pyplot as plt


# In[2]:


data = pd.read_excel("correct_payments.xlsx", engine="openpyxl")
#data = pd.read_excel("https://raw.githubusercontent.com/rozhkov1922/work_experience/main/simple_things/correct_payments.xlsx", engine="openpyxl")


# In[4]:


#data.info()


# In[5]:


data.isna().sum()


# In[6]:


data[data['action_date'].isna()]['status'].value_counts()


# In[7]:


data[data['order_id'].isna()]['status'].value_counts()


# In[8]:


data[data['final_sum'].isna()]['status'].value_counts()


# In[9]:


data[data['aim'].isna()]['status'].value_counts()


# In[10]:


data['action_date'].value_counts()


# In[11]:


data['status'].value_counts()


# In[12]:


data['type'].value_counts()


# In[13]:


data['customer'].str.contains('nan').value_counts()


# In[14]:


data.loc[data['customer'].str.contains('nan', na=False), 'customer'] = None


# In[15]:


data['operation_currency'].value_counts()


# In[16]:


data['comission_sum'] = data['comission_sum'].astype(float)


# In[17]:


data['final_sum'] = data['final_sum'].astype(float)


# In[18]:


data['comission_perc'] = data['comission_perc'].astype(float)


# In[19]:


data['status'] = data['status'].replace({
    'Завершена': 'Completed',
    'Отклонена': 'Declined'
})


# In[20]:


data['status'].value_counts()


# In[21]:


#print(data['status'].unique())


# In[22]:


data[data['status'] == 'Declined']['final_sum'].value_counts()


# In[23]:


data['status'].value_counts()


# In[24]:


data['action_date'] = pd.to_datetime(data['action_date'], errors='coerce')


# In[25]:


data['action_date_month'] = data['action_date'].dt.month


# In[26]:


data['action_date_year'] = data['action_date'].dt.year


# In[27]:


data['action_date_month'].nunique()


# In[28]:


# Курсы валют на 11 февраля 2025 года
exchange_rates = {
    'USD': 96.7821,   # 1 доллар США = 96.7821 рубля
    'EUR': 100.4991,  # 1 евро = 100.4991 рубля
    'BYN': 28.6227    # 1 белорусский рубль = 28.6227 рубля
}

# Функция для конвертации суммы в рубли
def convert_to_rub(row):
    currency = row['operation_currency']
    amount = row['final_sum']
    if currency == 'RUB':
        return amount
    elif currency in exchange_rates:
        return amount * exchange_rates[currency]
    else:
        # Если валюта не распознана, можно вернуть NaN или оставить сумму без изменений
        return amount

# Применяем функцию к DataFrame
data['amount_in_rub'] = data.apply(convert_to_rub, axis=1)

# Обновляем колонку 'operation_currency' на 'RUB'
data['operation_currency'] = 'RUB'


# In[29]:


def prepare_rfm_data(data, analysis_date=None):
    """
    Подготовка данных для RFM-анализа
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Датафрейм с колонками customer_id, transaction_date, amount
    analysis_date : datetime, optional
        Дата, относительно которой проводится анализ
        
    Returns:
    --------
    pandas.DataFrame
        Датафрейм с RFM-метриками для каждого клиента
    """
    if analysis_date is None:
        analysis_date = data['action_date'].max()
    
    # Группировка по клиентам и расчет RFM-метрик
    rfm = data.groupby('customer').agg({
        'action_date': lambda x: (analysis_date - x.max()).days,  # Recency
        'amount_in_rub': ['count', 'sum']  # Frequency & Monetary
    }).reset_index()
    
    # Переименование колонок
    rfm.columns = ['customer', 'recency', 'frequency', 'monetary']
    
    # Обработка выбросов
    for column in ['recency', 'frequency', 'monetary']:
        q1 = rfm[column].quantile(0.25)
        q3 = rfm[column].quantile(0.75)
        iqr = q3 - q1
        upper_bound = q3 + 1.5 * iqr
        rfm[column] = np.where(rfm[column] > upper_bound, upper_bound, rfm[column])
    
    return rfm

# Применяем функцию к нашим данным
rfm_data = prepare_rfm_data(data)


# In[30]:


#rfm_data


# In[31]:


def plot_rfm_distributions(rfm_data):
    """
    Визуализация распределения RFM-метрик
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle('Распределение RFM-метрик', fontsize=14)
    
    # Recency
    sns.histplot(data=rfm_data, x='recency', bins=30, ax=axes[0])
    axes[0].set_title('Распределение Recency')
    axes[0].set_xlabel('Дни с последней покупки')
    
    # Frequency
    sns.histplot(data=rfm_data, x='frequency', bins=30, ax=axes[1])
    axes[1].set_title('Распределение Frequency')
    axes[1].set_xlabel('Количество покупок')
    
    # Monetary
    sns.histplot(data=rfm_data, x='monetary', bins=30, ax=axes[2])
    axes[2].set_title('Распределение Monetary')
    axes[2].set_xlabel('Общая сумма покупок')
    
    plt.tight_layout()
    return fig

# Создаем визуализацию
rfm_dist_plot = plot_rfm_distributions(rfm_data)


# In[32]:


def quantile_segmentation(rfm_data, n_segments=3):
    """
    Квантильная сегментация клиентов
    
    Parameters:
    -----------
    rfm_data : pandas.DataFrame
        Датафрейм с RFM-метриками
    n_segments : int
        Количество сегментов для каждой метрики
        
    Returns:
    --------
    pandas.DataFrame
        Датафрейм с добавленными сегментами
    """
    rfm = rfm_data.copy()
    
    # Создаем лейблы для сегментов
    labels = range(n_segments, 0, -1)
    
    # Квантильная сегментация
    r_labels = pd.qcut(rfm['recency'], q=n_segments, labels=labels)
    f_labels = pd.qcut(rfm['frequency'], q=n_segments, labels=labels)
    m_labels = pd.qcut(rfm['monetary'], q=n_segments, labels=labels)
    
    # Добавляем сегменты в датафрейм
    rfm['R'] = r_labels
    rfm['F'] = f_labels
    rfm['M'] = m_labels
    
    # Создаем RFM Score
    rfm['RFM_Score'] = rfm['R'].astype(str) + rfm['F'].astype(str) + rfm['M'].astype(str)
    
    return rfm

# Применяем сегментацию
rfm_segmented = quantile_segmentation(rfm_data)
rfm_segmented = rfm_segmented[~rfm_segmented['RFM_Score'].str.contains('nan', na=False)]


# In[33]:


data = data[data['status'] == 'Completed']
data = data[data['action_date'].notna()]
data = data[data['final_sum'].notna()]


# In[34]:


dau_total = (
    data.groupby('action_date').agg({'customer': 'nunique'}).mean()
)

wau_total = (
    data.groupby(['action_date_month', 'action_date_year'])
    .agg({'customer': 'nunique'})
    .mean()
)

print(int(dau_total))
print(int(wau_total)) 

dau_total = int(dau_total)
wau_total = int(wau_total)
sticky  = round((dau_total / wau_total * 100),2)
# In[35]:


#print(dau_total / wau_total * 100) 


# In[36]:


#data['month_cohort'] = data.groupby('customer')['action_date_month'].transform('min')
data['session_start'] = data.groupby(['customer'])['action_date'].transform('min')
data['max_action_date'] = data.groupby(['customer'])['action_date'].transform('max')


# In[37]:


def get_profiles(sessions):

    # сортируем сессии по ID пользователя и дате посещения
    # группируем по ID и находим первые значения session_start и channel
    # столбец с временем первого посещения назовём first_ts
    # от англ. first timestamp — первая временная отметка
    profiles = (
        data.sort_values(by=['customer', 'session_start'])
        .groupby('customer')
        .agg({'session_start': 'min'})
        .rename(columns={'session_start': 'first_ts'})
        .reset_index()  # возвращаем user_id из индекса
    )

    # определяем дату первого посещения
    # и первый день месяца, в который это посещение произошло
    # эти данные понадобятся для когортного анализа
    profiles['dt'] = profiles['first_ts'].dt.date
    profiles['month'] = profiles['first_ts'].dt.to_period('M')


    return profiles


# In[38]:


profiles = get_profiles(data)
#profiles


# In[39]:


result_raw = profiles.merge(
    data[['customer', 'max_action_date', 'session_start', 'final_sum']], on='customer', how='left'
)

#result_raw


# In[40]:


result_raw['lifetime'] = (
    ((result_raw['max_action_date'] - result_raw['first_ts']).dt.days / 30)
    .fillna(0)
    .astype(int)
)

result_raw['final_sum'] = result_raw['final_sum'].astype(int)


# In[42]:


# строим таблицу удержания

result_grouped = result_raw.pivot_table(
    index=['month'], columns='lifetime', values='customer', aggfunc='nunique'
)

#result_grouped


# In[43]:


# вычисляем размеры когорт

cohort_sizes = (
    result_raw.groupby('month')
    .agg({'customer': 'nunique'})
    .rename(columns={'customer': 'cohort_size'})
)

#cohort_sizes


# In[44]:


result_grouped = cohort_sizes.merge(
    result_grouped, on='month', how='left'
).fillna(0)

#result_grouped.info()


# In[45]:


import pandas as pd

# 1. Скопируем
dist = result_grouped.copy()

# 2. Отберём столбцы, где название - это int/float (то есть сами lifetime, без 'cohort_size'):
lifetime_cols = sorted(
    c for c in dist.columns 
    if isinstance(c, (int, float))
)

# 3. Кумулятивная сумма «точного распределения» по строкам
cumulative = dist[lifetime_cols].cumsum(axis=1)

# 4. Собираем новый DataFrame, куда запишем «количество, доживших до i-го месяца»
retention = pd.DataFrame(index=dist.index) 
retention['cohort_size'] = dist['cohort_size']

for i, col in enumerate(lifetime_cols):
    if col == 0:
        # "До 0-го месяца" доживают все (обычно это старт когорты = 100%)
        retention[str(col)] = dist['cohort_size']
    else:
        # lifetime >= col
        # = cohort_size - кумулятивная сумма всех lifetime < col
        # а "кумулятивная сумма всех lifetime < col" — это cumulative[col предыдущий].
        prev_col = lifetime_cols[i-1]  # например, если col=2, предыдущий col=1
        retention[str(col)] = dist['cohort_size'] - cumulative[prev_col]

# retention — это ваша финальная таблица удержания
#retention


# In[46]:


retention = retention.div(
    retention['cohort_size'], axis=0
).drop(columns='cohort_size')

retention = round(retention, 2)


# In[47]:


retention = retention.reset_index()


# In[66]:



plt.figure(figsize=(10, 6))
sns.heatmap(retention.set_index("month"), 
            annot=True, fmt=".2f", cmap="coolwarm", linewidths=0.5, linecolor='gray')

plt.title("Retention Heatmap")
plt.xlabel("Lifetime")
plt.ylabel("Cohort Month")

# Делаем подписи оси Y горизонтальными
plt.yticks(rotation=0)  

plt.show()


# In[48]:


retention.to_csv('retention.csv', index=False)


# In[49]:


import pandas as pd

# Сохраняем 'month', если он есть в индексе
if isinstance(retention.index, pd.DatetimeIndex):
    retention = retention.reset_index()

# Определяем список колонок с данными о ретеншене (без 'cohort_size' и 'month')
lifetime_cols = sorted(
    c for c in retention.columns if c not in ['cohort_size', 'month']
)

# Создадим DataFrame под churn
churn = pd.DataFrame()

# Переносим 'month' в churn
churn['month'] = retention['month']

# Вычисляем churn для каждого месяца
for i, col in enumerate(lifetime_cols):
    if i == 0:
        churn[col] = 0  # Для нулевого месяца ставим 0
    else:
        prev_col = lifetime_cols[i - 1]
        churn[col] = 1 - (retention[col].astype(float) / retention[prev_col].astype(float))

# Округляем и заполняем NaN
churn = round(churn.fillna(0), 2)

# Убираем ненужное имя колонок
churn.columns.name = None


# In[50]:



# In[51]:


churn.to_csv('churn.csv', index=False)


# In[52]:


def diff_months(d1, d2):
    """
    Возвращает целую разницу в месяцах между двумя датами.
    Например, между 2024-05-15 и 2024-07-01 будет 2 месяца.
    """
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)

def ltv(result_raw, cohort_sizes):
    # 1. Сводная таблица: для каждой пары (cohort_month, lifetime) -> сумма выручки
    result = result_raw.pivot_table(
        index='month',      # когорты (месяц начала)
        columns='lifetime', # лайфтаймы
        values='final_sum',
        aggfunc='sum'
    ).fillna(0)
    
    # 2. Превращаем суммы в накопленные по лайфтаймам (cumsum слева направо).
    result = result.cumsum(axis=1)
    
    # 3. Приклеиваем cohort_size к результату и заполняем пропуски
    result = cohort_sizes.merge(result, on='month', how='left').fillna(0)
    
    # 4. Считаем LTV: делим накопленную выручку на размер когорты
    #    (первый столбец — cohort_size, остальные — лайфтаймы)
    ltv = round(result.iloc[:, 1:].div(result['cohort_size'], axis=0), 2)
    ltv.insert(0, 'cohort_size', result['cohort_size'])
    
    max_date = pd.to_datetime(result_raw['dt']).max()

    # Все столбцы, кроме 'cohort_size', считаем лайфтаймом
    lifetime_cols = ltv.columns[1:]  # пропускаем 'cohort_size'

    for cohort_start in ltv.index:
        # Считаем, сколько месяцев «прожила» когорта
        lived_months = diff_months(cohort_start.to_timestamp(), max_date)
        
        # Если когорта "моложе" max_date (lived_months < 0), обнуляем все столбцы
        if lived_months < 0:
            ltv.loc[cohort_start, lifetime_cols] = 0
        else:
            # Иначе обнуляем только те столбцы, чей лайфтайм больше lived_months
            invalid_cols = [col for col in lifetime_cols if int(col) > lived_months]
            ltv.loc[cohort_start, invalid_cols] = 0

    return ltv

ltv_result = ltv(result_raw, cohort_sizes)


# In[53]:


ltv_result = ltv_result.reset_index()


# In[54]:


#ltv_result


# In[55]:


ltv_result.to_csv('ltv_result.csv', index=False)


# In[56]:


result_mean_per_cohort = result_raw.pivot_table(
    index='month',      # когорты (месяц начала)
    columns='lifetime', # лайфтаймы
    values='final_sum',
    aggfunc='mean'
).fillna(0)

result_mean_per_cohort = round(result_mean_per_cohort, 2)  # округляем значения

# Сброс индекса, чтобы "month" стал обычным столбцом
result_mean_per_cohort = result_mean_per_cohort.reset_index()

# Переименовываем колонки, чтобы убрать multiindex (если остался)
result_mean_per_cohort.columns.name = None

#result_mean_per_cohort


# In[57]:


result_mean_per_cohort.to_csv('result_mean_per_cohort.csv', index=False)


# In[58]:


mean_revenue = data.groupby('action_date_month').agg({
    'final_sum': ['mean']
}).reset_index().round(2)

#mean_revenue


# In[59]:


# 1. Сгруппируем по месяцу и возьмем среднюю final_sum
monthly_mean = (
    data
    .groupby('action_date_month', as_index=False)['final_sum']
    .mean()
)

# 2. Отсортируем по датам на случай, если месяц идет не по порядку
monthly_mean = monthly_mean.sort_values('action_date_month')

# 3. Вычислим скользящее среднее по окну в 2 месяца
monthly_mean['rolling_mean_3m'] = monthly_mean['final_sum'].rolling(window=2).mean()

# Посмотрим результат
#monthly_mean.head(10)


import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

st.title('Дашборд для компании "Простые вещи"')

st.markdown("""
📊 Этот дашборд предоставляет ключевые метрики пользовательской активности и финансовых показателей. 
Вы можете выбрать интересующий график из списка, чтобы проанализировать удержание пользователей, 
динамику доходов и другие важные показатели. 🔍
""")

# Выбор графика
option = st.selectbox("Выберите график", 
                      ["RFM Analysis", "Retention Rate", "Churn Rate", "LTV", 
                       "Mean by month heatmap", "Mean Revenue", 
                       "Mean Revenue with Rolling Average"])

# 🔹 RFM Analysis
def plot_rfm_distributions(rfm_data):
    """
    Визуализация распределения RFM-метрик
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle('Распределение RFM-метрик', fontsize=14)
    
    # Recency
    sns.histplot(data=rfm_data, x='recency', bins=30, ax=axes[0])
    axes[0].set_title('Распределение Recency')
    axes[0].set_xlabel('Дни с последней покупки')
    
    # Frequency
    sns.histplot(data=rfm_data, x='frequency', bins=30, ax=axes[1])
    axes[1].set_title('Распределение Frequency')
    axes[1].set_xlabel('Количество покупок')
    
    # Monetary
    sns.histplot(data=rfm_data, x='monetary', bins=30, ax=axes[2])
    axes[2].set_title('Распределение Monetary')
    axes[2].set_xlabel('Общая сумма покупок')
    
    plt.tight_layout()
    return fig

rfm_dist_plot = plot_rfm_distributions(rfm_data)

description_rfm = """
**RFM-анализ (Recency, Frequency, Monetary)** позволяет сегментировать клиентов по трем основным параметрам:
- **Recency** (Давность) — сколько дней прошло с последней покупки.
- **Frequency** (Частота) — сколько раз клиент совершал покупки.
- **Monetary** (Доходность) — сколько денег клиент потратил за весь период.

Этот анализ помогает находить лояльных клиентов и определять аудиторию с высоким потенциалом.
"""

# 🔹 Retention Rate
fig, ax = plt.subplots(figsize=(10, 6))
sns.heatmap(retention.set_index("month"), annot=True, fmt=".2f", cmap="coolwarm", linewidths=0.5, linecolor="gray", ax=ax)
ax.set_title("Retention Heatmap")
ax.set_xlabel("Lifetime")
ax.set_ylabel("Cohort Month")
ax.set_yticklabels(ax.get_yticklabels(), rotation=0)

description_retention = """
**Retention Rate (Коэффициент удержания)** показывает, сколько пользователей возвращается в последующие месяцы после первой активности.

На графике видно:
- Большинство когорт теряют более **50% пользователей** уже через 2 месяца.
- В когорте **2024-06** к 2-му месяцу остается **23% пользователей**.
- В когорте **2024-07** пользователи полностью теряются к 2-му месяцу.

График помогает анализировать снижение активности пользователей и выявлять проблемные моменты в удержании клиентов.
"""

# 🔹 Churn Rate
fig1, ax = plt.subplots(figsize=(10, 6))
sns.heatmap(churn.set_index("month"), annot=True, fmt=".2f", cmap="coolwarm", linewidths=0.5, linecolor="gray", ax=ax)
ax.set_title("Churn Heatmap")
ax.set_xlabel("Lifetime")
ax.set_ylabel("Cohort Month")
ax.set_yticklabels(ax.get_yticklabels(), rotation=0)

description_churn = """
**Churn Rate (Коэффициент оттока)** показывает долю пользователей, которые перестали пользоваться сервисом.

На графике видно:
- В когортах **2024-06 и 2024-07** отток достигает **100% уже через 2 месяца**.
- В когортах **2024-03 и 2024-04** наблюдается более плавный спад.

Анализ этого графика помогает выявить моменты, когда пользователи начинают уходить, и разрабатывать стратегии по удержанию.
"""

# 🔹 LTV Heatmap
fig2, ax = plt.subplots(figsize=(10, 6))
sns.heatmap(ltv_result.set_index("month"), annot=True, fmt=".2f", cmap="coolwarm", linewidths=0.5, linecolor="gray", ax=ax)
ax.set_title("LTV Heatmap")
ax.set_xlabel("Lifetime")
ax.set_ylabel("Cohort Month")
ax.set_yticklabels(ax.get_yticklabels(), rotation=0)

description_ltv = """
**LTV (Lifetime Value)** — это совокупная прибыль, которую приносит клиент за все время взаимодействия с продуктом.

На графике видно:
- В когорте **2024-03** в 3-й месяц наблюдается **максимальное LTV (4888.47)**.
- В когортах **2024-06 и 2024-07** LTV остается низким, что говорит о слабом вовлечении пользователей.

Этот график помогает оценить ценность пользователей и выявлять периоды максимальной прибыли.
"""

# 🔹 Mean by month heatmap
fig3, ax = plt.subplots(figsize=(10, 6))
sns.heatmap(result_mean_per_cohort.set_index("month"), annot=True, fmt=".2f", cmap="coolwarm", linewidths=0.5, linecolor="gray", ax=ax)
ax.set_title("Mean by month Heatmap")
ax.set_xlabel("Lifetime")
ax.set_ylabel("Cohort Month")
ax.set_yticklabels(ax.get_yticklabels(), rotation=0)

description_mean_heatmap = """
**Среднее значение по месяцам** помогает увидеть динамику ключевых метрик в разрезе временных когорт.

На графике выделяется:
- В **2024-03** в 0-й месяц аномально высокое значение **4513.83**.
- В **2024-04** в 3-й месяц есть всплеск до **2679.77**.

Анализ этих данных помогает выявлять неожиданные изменения и корректировать стратегию бизнеса.
"""

# 🔹 Mean Revenue
fig4, ax = plt.subplots(figsize=(10, 5))
ax.plot(mean_revenue[("action_date_month", "")], mean_revenue[("final_sum", "mean")], 
        label="Mean Revenue", marker="o", linestyle="-")
ax.set_title("Mean Revenue")
ax.set_xlabel("Month")
ax.set_ylabel("Revenue")
ax.legend()
ax.grid(True)

description_mean_revenue = """
**Mean Revenue (Средний доход)** показывает, какой средний доход компания получает за определенные периоды.

На графике видно:
- Резкий рост дохода в **3-й месяц**, а затем стабилизация.
- Последующие колебания дохода говорят о сезонных факторах.

Этот показатель помогает оценить стабильность выручки.
"""

# 🔹 Mean Revenue with Rolling Average
fig5, ax = plt.subplots(figsize=(10, 5))
ax.plot(monthly_mean["action_date_month"], monthly_mean["final_sum"], 
        label="Mean Revenue", marker="o", linestyle="-")
ax.plot(monthly_mean["action_date_month"], monthly_mean["rolling_mean_3m"], 
        label="Rolling Mean (2-months)", marker="o", linestyle="--", color="red")
ax.set_title("Mean Revenue with Rolling Average")
ax.set_xlabel("Month")
ax.set_ylabel("Revenue")
ax.legend()
ax.grid(True)

description_mean_revenue_rolling = """
**Средний доход с учетом скользящего среднего** позволяет устранить краткосрочные колебания и выявить долгосрочные тренды.

Скользящее среднее показывает:
- Общий рост дохода, несмотря на отдельные колебания.
- Сглаживание позволяет избежать резких скачков и лучше прогнозировать тренды.

Этот график полезен для выявления устойчивых изменений в доходах компании.
"""

# **Отображение выбранного графика**
if option == "RFM Analysis":
    st.pyplot(rfm_dist_plot)
    st.markdown(description_rfm)
elif option == "Retention Rate":
    st.pyplot(fig)
    st.markdown(description_retention)
elif option == "Churn Rate":
    st.pyplot(fig1)
    st.markdown(description_churn)
elif option == "LTV":
    st.pyplot(fig2)
    st.markdown(description_ltv)
elif option == "Mean by month heatmap":
    st.pyplot(fig3)
    st.markdown(description_mean_heatmap)
elif option == "Mean Revenue":
    st.pyplot(fig4)
    st.markdown(description_mean_revenue)
elif option == "Mean Revenue with Rolling Average":
    st.pyplot(fig5)
    st.markdown(description_mean_revenue_rolling)

word_d = dau_total  # Daily Active Users
word_w = wau_total  # Weekly Active Users
word_s = sticky  # Sticky Factor

# Заголовок
st.title('Метрики активности пользователей')

# Выбор метрики
metric_option = st.selectbox(
    "Выберите метрику для просмотра",
    ["DAU (Daily Active Users)", "WAU (Weekly Active Users)", "Sticky Factor (DAU/WAU)"]
)

# Отображение выбранной метрики
if metric_option == "DAU (Daily Active Users)":
    st.subheader('Показатель DAU')
    st.markdown(f'Количество активных пользователей в день: **{word_d}**')
    st.markdown("""
        **DAU (Daily Active Users)** — количество уникальных пользователей, 
        зашедших в приложение или сервис за последние 24 часа.
    """)

elif metric_option == "WAU (Weekly Active Users)":
    st.subheader('Показатель WAU')
    st.markdown(f'Количество активных пользователей в неделю: **{word_w}**')
    st.markdown("""
        **WAU (Weekly Active Users)** — количество уникальных пользователей,
        зашедших в приложение в течение последней недели.
    """)

elif metric_option == "Sticky Factor (DAU/WAU)":
    st.subheader('Показатель Sticky')
    st.markdown(f'Коэффициент удержания пользователей (DAU/WAU): **{word_s}**')
    st.markdown("""
        **Sticky Factor** показывает, насколько часто пользователи возвращаются в приложение.
        Рассчитывается как отношение DAU к WAU. Чем выше значение, тем лучше удержание.
    """)

import streamlit as st
import pandas as pd

# Функция чтения файла с автоматическим определением кодировки
def read_csv_with_encoding(upload_file):
    encodings = ["utf-8", "windows-1251", "ISO-8859-1"]
    for enc in encodings:
        try:
            upload_file.seek(0)  # Возвращаемся в начало файла
            return pd.read_csv(upload_file, sep=";", encoding=enc, low_memory=False), enc
        except UnicodeDecodeError:
            continue
    return None, None

# Интерфейс Streamlit
st.title("📊 Анализ загруженных данных")

# Боковая панель
upload_file = st.sidebar.file_uploader("📂 Загрузите CSV", type=["csv"])

if upload_file is not None:
    df, detected_encoding = read_csv_with_encoding(upload_file)

    if df is not None:
        st.write(f"🔎 **Определённая кодировка файла**: **{detected_encoding}**")
        st.write("📋 **Список колонок датасета:**")
        st.write(df.columns.tolist())  # Выводим список колонок

        # Опции обработки данных
        show = st.sidebar.button("📊 Показать датасет")
        process = st.sidebar.button("⚙️ Обработать данные")
        slider_value = st.sidebar.slider("📉 Выберите значение", min_value=0, max_value=100)
        select_option = st.sidebar.selectbox("📌 Выберите опцию", options=["Вариант 1", "Вариант 2"])

        st.write(f"Выбранное значение: **{slider_value}**")
        st.write(f"Выбранная опция: **{select_option}**")

        if show:
            st.write("📊 **Первые 5 строк загруженного датасета:**")
            st.dataframe(df.head())

            # Создание файла для скачивания
            csv_data = df.to_csv(index=False).encode("utf-8")
            st.download_button(label="📥 Скачать данные", file_name="processed_data.csv", data=csv_data)

        if process:
            st.write("⚙️ **Обработка данных**")
            st.text("📋 Колонки датасета:")
            st.write(df.columns.tolist())

            # Удаление пустых значений
            df_cleaned = df.dropna()
            st.write(f"📊 Количество строк до очистки: **{len(df)}**")
            st.write(f"✅ Количество строк после очистки: **{len(df_cleaned)}**")

            # Сохранение обработанных данных
            cleaned_csv = df_cleaned.to_csv(index=False).encode("utf-8")
            st.download_button(label="📥 Скачать очищенные данные", file_name="cleaned_data.csv", data=cleaned_csv)

    else:
        st.error("❌ Ошибка при чтении файла. Попробуйте загрузить CSV с другой кодировкой.")

