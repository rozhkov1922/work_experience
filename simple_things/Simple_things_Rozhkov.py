#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python
# coding: utf-8

# Проект анализа для компании "Простые вещи"
# 
# В данном проекте я сделал следующее:
# 
# 1. Выгрузил библиотеки  
# 2. Проверил данные 
# 3. Предообработал данные, удалив часть строчек 
# 4. Провел анализ данных
# 5. Провел когортный анализ 
# 6. Провел RFM анализ
# 7. Вычислил DAU, WAU, sticky 

# 1. Загрузка библиотек. 

# In[1]:


import ipywidgets as widgets
from IPython.display import display
import pandas as pd
import streamlit as st
import numpy as np
from datetime import datetime
import seaborn as sns
import matplotlib.pyplot as plt


# 2. Загрузка и проверка данных

# In[2]:


data = pd.read_excel('correct_payments.xlsx')


# In[3]:


data.isna().sum()


# Как видно, в данных много пропусков. Нужно посмотреть, с чем это связано 

# In[4]:


data[data['action_date'].isna()]['status'].value_counts()


# In[5]:


data[data['order_id'].isna()]['status'].value_counts()


# In[6]:


data[data['final_sum'].isna()]['status'].value_counts()


# In[7]:


data[data['aim'].isna()]['status'].value_counts()


# Как видно большая часть пропусков свзана с отклонением платежей

# In[8]:


data['action_date'].value_counts()


# In[9]:


data['status'].value_counts()


# В датасете пропуски связаны с отклоненными транзакциями - их мы далее удалил

# In[10]:


data['type'].value_counts()


# Видно, что с регулярной оплатой пользователей гораздо больше

# In[11]:


data.query('status == "Завершена" or status == "Completed"')['customer'].nunique()


# In[12]:


data['customer'].str.contains('nan').value_counts()


# 2. Предообратка данных

# In[13]:


#data[data['customer'].isna()]


# Среди пользователей мы видим одного неизвестного. Чтобы он не потерялся, можно его переименовать 

# In[14]:


# Найдём маску, где customer == NaN
mask = data['customer'].isna()

# Допустим, хотим всем таким строкам (если одна или несколько) присвоить одно имя:
data.loc[mask, 'customer'] = "Unknown_1"

# Теперь во всех строках, где раньше было NaN, в 'customer' появится "Unknown_1"


# Как видим, в данных есть разные валюты. Их нужно свести к рублям 

# In[15]:


data['operation_currency'].value_counts()


# Переводим все данные в числа с десятиными дробями 

# In[16]:


data['comission_sum'] = data['comission_sum'].astype(float)


# In[17]:


data['final_sum'] = data['final_sum'].astype(float)


# In[18]:


data['comission_perc'] = data['comission_perc'].astype(float)


# Приводим все статусы к единому формату 

# In[19]:


data['status'] = data['status'].replace({
    'Завершена': 'Completed',
    'Отклонена': 'Declined'
})


# In[20]:


df_completed = data.query("status == 'Completed'")
df_completed['customer'].nunique()


# Удаляем лишние данные, т.е. отклоненные платежи 

# In[21]:


data = data[data['status'] == 'Completed']
data = data[data['action_date'].notna()]
data = data[data['final_sum'].notna()]


# In[22]:


data['status'].value_counts()


# Осталось 3327 строчек. Количество соотвествует числу транзакций 

# Переводим данные в нормальный вид. Считаем день, неделя, месяц, год транзакции

# In[23]:


data['action_date'] = pd.to_datetime(data['action_date'], errors='coerce')


# In[24]:


data['action_date_month'] = data['action_date'].dt.to_period('M')


# In[25]:


data['action_date_year'] = data['action_date'].dt.year


# In[26]:


data['action_date_week'] = data['action_date'].dt.to_period('W')


# In[27]:


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


# Данные по валюте переводим в рубли 

# 4. Анализ данных

# In[28]:


data['action_date_month'].nunique()


# В данных представлено семь месяцев 

# Далее готовим данные для построения дашборда

# Количество пользователей

# In[29]:


user_count = data['customer'].nunique()


# Результирующая оплата

# In[30]:


final_revenue = data['final_sum'].sum().astype(int)


# Число транзакций 

# In[31]:


final_transaction = data['operation_sum'].sum()


# Финальная комиссия 

# In[32]:


final_comission = data['comission_sum'].sum()


# Средняя величина транзакции 

# In[33]:


mean_transaction = data['operation_sum'].mean()


# Медиана транзакции 

# In[34]:


median_transaction = data['operation_sum'].median()


# Количество заплативших пользователей

# In[35]:


user_pay_count = data.query('type == "Оплата"')['customer'].nunique()


# Считаем первый месяц активности для всех пользователей

# In[36]:


data['first_month'] = data['customer'].map(
    data.groupby('customer')['action_date'].min().dt.to_period('M')
)


# Кумулитивный рост пользователей по месяцам

# In[37]:


users_count_per_month = (
    data
    .groupby('first_month')['customer']
    .nunique()
    .cumsum()
    .reset_index()
)


# Кумулитивный рост выручки по месяцам

# In[38]:


money_per_month = (
    data.groupby('first_month')['final_sum']
    .sum()
    .round()
    .astype(int)
    .cumsum()
    .reset_index()
)


# Рост средней выручки по месяцам

# In[39]:


mean_revenue_per_month = data.groupby('action_date_month').agg({
    'final_sum': ['mean']
}).reset_index().round(2)


# Скользаящее среднее для двум месяцам

# In[40]:


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


# 5. Когортный анализ 

# Определим первую дату для всех клиентов

# In[42]:


user_first_tx = (
    data
    .groupby('customer', as_index=False)
    .agg(first_txn_date=('action_date', 'min'))
)


# Округлим до месяцов 

# In[43]:


user_first_tx['cohort_month'] = user_first_tx['first_txn_date'].dt.month
user_first_tx['cohort_year'] = user_first_tx['first_txn_date'].dt.year


# Смерджим с основной таблицей, установив первую дату активности, месяц и год для всех клиентов 

# In[44]:


df_merged = data.merge(user_first_tx, on='customer', how='left', validate='many_to_one')


# In[45]:


df_merged['txn_year'] = df_merged['action_date'].dt.year
df_merged['txn_month'] = df_merged['action_date'].dt.month


# Удалим строчки, где информации о первых датах нет

# In[46]:


df_merged = df_merged.dropna(subset=['first_txn_date'])


# Определеям лайфтайм по месяцам

# In[47]:


df_merged['month_of_life'] =  df_merged['txn_month'].astype(int) - df_merged['cohort_month'].astype(int)


# Группируем все данные по месяцу когорты и лайфтайму для дальнейшей обработки 

# In[48]:


grouped = df_merged.groupby(['cohort_month', 'month_of_life'])


# Считаем метрики 

# In[49]:


cohort_metrics = grouped[['month_of_life','id','customer','final_sum']].agg(
    transactions_count=('id','count'),
    active_users=('customer','nunique'),
    total_sum=('final_sum','sum'),
    avg_check=('final_sum', 'mean')
).reset_index()

# Удаляем столбец cohort_month, если не нужен


# Считаем метрики для LTV

# In[50]:


cohort_metrics['cumulative_sum'] = cohort_metrics.sort_values('month_of_life')     .groupby('cohort_month')['total_sum'].cumsum()


# Далее идут сводные таблицы для анализа данных

# In[51]:


cohort_pivot_active_users = cohort_metrics.pivot(
    index='month_of_life',       # строка – это месяц жизни когорты
    columns='cohort_month',         # столбец – это сама когорта (год-месяц начала)
    values='active_users'      # какое значение хотим видеть
).fillna(0)


# In[52]:


cohort_pivot_ltv = cohort_metrics.pivot(
    index='month_of_life',       # строка – это месяц жизни когорты
    columns='cohort_month',         # столбец – это сама когорта (год-месяц начала)
    values='cumulative_sum'      # какое значение хотим видеть
).fillna(0)


# In[53]:


cohort_pivot_transactions = cohort_metrics.pivot(
    index='month_of_life',       # строка – это месяц жизни когорты
    columns='cohort_month',         # столбец – это сама когорта (год-месяц начала)
    values='transactions_count'      # какое значение хотим видеть
).fillna(0)


# In[54]:


cohort_pivot_total_sum = cohort_metrics.pivot(
    index='month_of_life',       # строка – это месяц жизни когорты
    columns='cohort_month',         # столбец – это сама когорта (год-месяц начала)
    values='total_sum'      # какое значение хотим видеть
).fillna(0)


# In[55]:


cohort_pivot_avg_check = round(cohort_metrics).pivot(
    index='month_of_life',       # строка – это месяц жизни когорты
    columns='cohort_month',         # столбец – это сама когорта (год-месяц начала)
    values='avg_check'      # какое значение хотим видеть
).fillna(0)


# Готовим данные для проведения анализа retantion_rate и churn_rate

# In[56]:


cohort_sizes = (
    user_first_tx
    .groupby('cohort_month', as_index=False)
    .agg(cohort_size=('customer', 'nunique'))  # или count, если customer уже уникален
)


# In[57]:


cohort_metrics = cohort_metrics.merge(
    cohort_sizes,
    on='cohort_month', 
    how='left'
)


# In[58]:


cohort_metrics['retention_rate'] = (
    cohort_metrics['active_users'] / cohort_metrics['cohort_size']
)
cohort_metrics['retention_rate'] = round(cohort_metrics['retention_rate'], 2)


# In[59]:


cohort_metrics['churn_rate'] = (
    1 - cohort_metrics['retention_rate']
)

cohort_metrics['churn_rate'] = round(cohort_metrics['churn_rate'], 2)


# In[60]:


pivot_retention = cohort_metrics.pivot(
    index='month_of_life',
    columns='cohort_month',
    values='retention_rate'
).fillna(0)


# In[61]:


pivot_churn = cohort_metrics.pivot(
    index='month_of_life',
    columns='cohort_month',
    values='churn_rate'
).fillna(0)


# 4. Проведение RFM анализа

# In[62]:


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


# In[63]:


import pandas as pd

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

    # Функция для безопасного разбиения с учетом количества уникальных значений
    def safe_qcut(series, q):
        unique_values = series.nunique()
        if unique_values < q:
            q = unique_values  # Корректируем число квантилей
        bins = pd.qcut(series, q=q, duplicates='drop', retbins=True)[1]  # Получаем границы
        labels = range(len(bins) - 1, 0, -1)  # Генерируем метки динамически
        return pd.qcut(series, q=q, labels=labels, duplicates='drop')

    # Применяем квантильную сегментацию с учетом особенностей данных
    rfm['R'] = safe_qcut(rfm['recency'], n_segments)
    rfm['F'] = safe_qcut(rfm['frequency'], n_segments)
    rfm['M'] = safe_qcut(rfm['monetary'], n_segments)

    # Создаем RFM Score
    rfm['RFM_Score'] = rfm['R'].astype(str) + rfm['F'].astype(str) + rfm['M'].astype(str)

    return rfm

# Применяем сегментацию
rfm_segmented = quantile_segmentation(rfm_data)
rfm_segmented = rfm_segmented[~rfm_segmented['RFM_Score'].str.contains('nan', na=False)]


# In[64]:


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


# 5. Вычисление DAU, WAU, sticky 
# 

# In[65]:


dau_total = (
    data.groupby('action_date').agg({'customer': 'nunique'}).mean()
)

mau_total = (
    data.groupby(['action_date_month', 'action_date_year'])
    .agg({'customer': 'nunique'})
    .mean()
)


wau_total = (
    data.groupby(['action_date_week'])
    .agg({'customer': 'nunique'})
    .mean()
)


# In[66]:


dau_total = int(dau_total)


# In[67]:


wau_total = int(wau_total)


# In[68]:


mau_total = int(mau_total)


# In[69]:


wau_total = int(wau_total)


# In[73]:


sticky  = (dau_total / wau_total * 100)


# Ссылка на дашборд

# https://rozhkov1922-work-experience-simple-thingssimple-things1-fvrbsq.streamlit.app/

# ============================================================================
# 6. Построение дашборда
# ============================================================================
st.title("Аналитическая панель для проекта \"Простые вещи\"")

tab1, tab2, tab3 = st.tabs(["Основные показатели", "RFM анализ", "Когортный анализ"])

# -----------------------------------------------------------------------------
# Вкладка 1: Основные показатели
# -----------------------------------------------------------------------------
with tab1:
    st.subheader("Основные показатели")
    
    st.markdown(
        """
        На этой вкладке представлены ключевые метрики:  
        1) Количество пользователей и общая сумма транзакций  
        2) Количество платящих пользователей и итоговая выручка  
        3) Переключатель между DAU, WAU, MAU и sticky  
        4) Динамика показателей по месяцам (4 варианта графиков)
        """
    )

    # --- Первый ряд ---
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Количество пользователей",
            value=user_count
        )
    with col2:
        st.metric(
            "Общая сумма транзакций",
            value=round(final_transaction, 2)
        )

    # --- Второй ряд ---
    col3, col4 = st.columns(2)
    with col3:
        st.metric(
            "Количество заплативших пользователей",
            value=user_pay_count
        )
    with col4:
        st.metric(
            "Итоговая выручка",
            value=round(final_revenue, 2)
        )

    # --- Третий ряд: DAU, WAU, sticky
    st.markdown("### DAU, WAU, MAU, sticky")
    choice_metric = st.selectbox("Выберите метрику:", ["DAU", "WAU", "MAU", "sticky"])
    if choice_metric == "DAU":
        st.metric("DAU", dau_total)
    elif choice_metric == "WAU":
        st.metric("WAU", wau_total)
    elif choice_metric == "MAU":
        st.metric("MAU", mau_total)
    else:
        st.metric("sticky", round(sticky, 2))

    # --- Графики по месяцам ---
    st.markdown("### Динамика по месяцам")
    choice_chart = st.radio(
        "Выберите график:",
        [
            "Линейный график: кумулятивное число пользователей",
            "Линейный график: кумулятивная выручка",
            "Среднее по месяцам",
            "Таблица со скользящим средним"
        ]
    )
    fig, ax = plt.subplots(figsize=(8, 4))

    if choice_chart == "Линейный график: кумулятивное число пользователей":
        ax.plot(
            users_count_per_month["first_month"].astype(str),
            users_count_per_month["customer"],
            marker="o"
        )
        ax.set_title("Кумулятивное число пользователей по месяцам")
        ax.set_xlabel("Месяц (first_month)")
        ax.set_ylabel("Пользователи")
        plt.xticks(rotation=45)

    elif choice_chart == "Линейный график: кумулятивная выручка":
        ax.plot(
            money_per_month["first_month"].astype(str),
            money_per_month["final_sum"],
            marker="o",
            color="green"
        )
        ax.set_title("Кумулятивная выручка по месяцам")
        ax.set_xlabel("Месяц (first_month)")
        ax.set_ylabel("Выручка, руб.")
        plt.xticks(rotation=45)

    elif choice_chart == "Среднее по месяцам":
        tmp = mean_revenue_per_month.copy()
        tmp.columns = ["action_date_month","mean_final_sum"]  # убираем мультииндекс
        ax.plot(
            tmp["action_date_month"].astype(str),
            tmp["mean_final_sum"],
            marker="o",
            color="purple"
        )
        ax.set_title("Средняя сумма по месяцам")
        ax.set_xlabel("Месяц")
        ax.set_ylabel("Средняя сумма, руб.")
        plt.xticks(rotation=45)

    else:  # "Таблица со скользящим средним"
        # Здесь используем rolling_mean_3m
        ax.plot(
            monthly_mean["action_date_month"].astype(str),
            monthly_mean["final_sum"],
            marker="o",
            label="Средняя сумма"
        )
        ax.plot(
            monthly_mean["action_date_month"].astype(str),
            monthly_mean["rolling_mean_3m"],
            marker="o",
            label="Скользящее среднее (2 месяца)"
        )
        ax.set_title("Средняя сумма и скользящее среднее (2 месяца)")
        ax.set_xlabel("Месяц")
        ax.set_ylabel("Сумма, руб.")
        ax.legend()
        plt.xticks(rotation=45)

    st.pyplot(fig)

# -----------------------------------------------------------------------------
# Вкладка 2: RFM анализ
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("RFM анализ")
    st.markdown(
        """
        **RFM** (Recency, Frequency, Monetary) — анализ давности, частоты 
        и суммарной выручки от пользователей.
        """
    )
    st.pyplot(rfm_dist_plot)
    st.markdown(
        """
        Описание графиков RFM-анализа
На представленных графиках показано распределение пользователей по трём ключевым метрикам RFM-анализа:

1️⃣ График "Распределение Recency" (Давность последней покупки)

По оси X: количество дней с момента последней покупки пользователя.

По оси Y: количество пользователей с соответствующим значением Recency.

Что показывает:

Большая часть пользователей совершала покупки относительно недавно (левая часть графика).

Есть клиенты, которые давно не делали покупок (правая часть графика).

Пики на определённых значениях могут указывать на регулярные повторные покупки.

2️⃣ График "Распределение Frequency" (Частота покупок)

По оси X: количество покупок, совершённых одним пользователем за анализируемый период.

По оси Y: количество пользователей с соответствующей частотой покупок.

Что показывает:

У большинства пользователей частота покупок мала — они совершали 1-2 покупки.

Небольшое число пользователей совершают покупки очень часто, что делает их лояльными клиентами.

Длинный "хвост" справа говорит о наличии небольшой группы активных пользователей с высокой частотой покупок.

3️⃣ График "Распределение Monetary" (Суммарная сумма покупок)

По оси X: общая сумма покупок (сколько рублей потратил каждый пользователь).

По оси Y: количество пользователей с соответствующим значением Monetary.

Что показывает:

Большинство пользователей тратят небольшие суммы.

Видны отдельные выбросы — это небольшая группа пользователей, которые потратили значительно больше остальных.

Чёткие пики могут указывать на стандартные суммы платежей (например, типичные размеры заказов).

Вывод по графикам:

Большинство пользователей совершают редкие и небольшие покупки, но есть небольшая, но важная группа лояльных клиентов, которые покупают часто и тратят много.

Recency-график помогает выявить, сколько пользователей "спят" и давно не совершали покупок.

Frequency-график показывает долю постоянных клиентов.

Monetary-график помогает определить наиболее прибыльных клиентов и зафиксировать распределение трат.

Эти данные можно использовать для дальнейшего сегментирования пользователей, определения стратегий удержания и увеличения прибыли.
        """
    )

# -----------------------------------------------------------------------------
# Вкладка 3: Когортный анализ
# -----------------------------------------------------------------------------
with tab3:
    st.subheader("Когортный анализ")
    st.markdown(
        """
        Здесь вы можете переключаться между несколькими сводными таблицами, 
        чтобы посмотреть поведение пользователей в зависимости от их когорты 
        (месяца, когда они впервые пришли).
        """
    )

    pivot_options = {
        "Активные пользователи": {
            "df": cohort_pivot_active_users,
            "title": "Активные пользователи по когортам",
            "ylabel": "Активные пользователи"
        },
        "Количество транзакций": {
            "df": cohort_pivot_transactions,
            "title": "Количество транзакций по когортам",
            "ylabel": "Транзакции"
        },
        "Суммарная выручка": {
            "df": cohort_pivot_total_sum,
            "title": "Суммарная выручка по когортам",
            "ylabel": "Выручка, руб."
        },
        "LTV": {
            "df": cohort_pivot_ltv,
            "title": "LTV по когортам (накопленная)",
            "ylabel": "LTV, руб."
        },
        "Средний чек": {
            "df": cohort_pivot_avg_check,
            "title": "Средний чек по когортам",
            "ylabel": "Средний чек (руб.)"
        },
        "Retention": {
            "df": pivot_retention,
            "title": "Retention Rate по когортам",
            "ylabel": "Retention Rate"
        },
        "Churn": {
            "df": pivot_churn,
            "title": "Churn Rate по когортам",
            "ylabel": "Churn Rate"
        }
    }

    selected_table = st.selectbox("Выберите метрику:", list(pivot_options.keys()))
    chart_type = st.radio("Тип графика:", ["Тепловая карта (Heatmap)", "Линейный график (Line Chart)"])

    chosen_df = pivot_options[selected_table]["df"]
    chosen_title = pivot_options[selected_table]["title"]
    chosen_ylabel = pivot_options[selected_table]["ylabel"]

    fig2, ax2 = plt.subplots(figsize=(8,4))

    if chart_type == "Тепловая карта (Heatmap)":
        # Используем палитру "Reds", чтобы большие значения были более красными
        sns.heatmap(
            chosen_df,
            annot=True,
            fmt=".2f",
            cmap="Reds",     # Красная палитра
            linewidths=0.5,
            ax=ax2
        )
        ax2.set_title(chosen_title)
        ax2.set_xlabel("Когорта (cohort_month)")
        ax2.set_ylabel("Месяц жизни (month_of_life)")

    else:  # Линейный график (каждая линия — своя когорта)
        for col in chosen_df.columns:
            ax2.plot(
                chosen_df.index,
                chosen_df[col],
                marker="o",
                label=f"Когорта {col}"
            )
        ax2.set_title(chosen_title)
        ax2.set_xlabel("Месяц жизни когорты")
        ax2.set_ylabel(chosen_ylabel)
        ax2.legend()

    st.pyplot(fig2)

    st.markdown(
        f"""
        **Пояснение**:
        - В тепловой карте по оси X (столбцам) — номер когорты,
          по оси Y (строкам) — месяц жизни когорты (0 = месяц первого визита).
        - В линейном графике каждая линия — это отдельная когорта.
        
        Значения метрики: {selected_table}.
        """
    )

