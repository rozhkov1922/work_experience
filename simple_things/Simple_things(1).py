#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python
# coding: utf-8

# Проект анализа для компании "Простые вещи"
#
# В данном проекте я сделал следующее:
#  1. Выгрузил библиотеки
#  2. Проверил данные
#  3. Предообработал данные, удалив часть строчек
#  4. Провел RFM анализ
#  5. Вычислил DAU, WAU, sticky
#  6. Создал дашборд на Streamlit


# --- 1. Загрузка библиотек. ---
import ipywidgets as widgets
from IPython.display import display
import pandas as pd
import streamlit as st
import numpy as np
from datetime import datetime
import seaborn as sns
import matplotlib.pyplot as plt

# Чтобы картинки не "съезжали" в Streamlit:
plt.rcParams.update({'figure.autolayout': True})


# --- 2. Загрузка и проверка данных ---
@st.cache_data
def load_data():
    data = pd.read_excel('correct_payments.xlsx')
    return data

data = load_data()

# Проверка пропусков (для информации):
# st.write(data.isna().sum())

# Как видно, в данных много пропусков. Нужно посмотреть, с чем это связано
# Раскомментируйте для подробного исследования в ноутбуке:
# st.write(data[data['action_date'].isna()]['status'].value_counts())
# st.write(data[data['order_id'].isna()]['status'].value_counts())
# st.write(data[data['final_sum'].isna()]['status'].value_counts())
# st.write(data[data['aim'].isna()]['status'].value_counts())

# Видно, что большая часть пропусков связана с отклонением платежей.

# Приведём статусы "Завершена" -> "Completed" и "Отклонена" -> "Declined" (ниже).
# Прочие первичные исследования датасета опустим в финальном дашборде, чтобы не загромождать.


# --- Предобработка данных ---

# 1) Заменяем пропуски в customer на "Unknown_1"
mask = data['customer'].isna()
data.loc[mask, 'customer'] = "Unknown_1"

# 2) Приводим типы:
data['comission_sum'] = data['comission_sum'].astype(float)
data['final_sum'] = data['final_sum'].astype(float)
data['comission_perc'] = data['comission_perc'].astype(float)

# 3) Приводим статусы к единому формату
data['status'] = data['status'].replace({
    'Завершена': 'Completed',
    'Отклонена': 'Declined'
})

# 4) Удаляем всё, кроме завершённых платежей, у которых нет пропусков в датах и финальной сумме
data = data[data['status'] == 'Completed']
data = data[data['action_date'].notna()]
data = data[data['final_sum'].notna()]

# 5) Преобразуем дату
data['action_date'] = pd.to_datetime(data['action_date'], errors='coerce')

# 6) Создаём колонку с годом и колонку с периодом (месяц)
data['action_date_year'] = data['action_date'].dt.year
data['action_date_month'] = data['action_date'].dt.to_period('M')

# 7) Переводим всё в рубли
exchange_rates = {
    'USD': 96.7821,   # 1 доллар США = 96.7821 рубля
    'EUR': 100.4991,  # 1 евро = 100.4991 рубля
    'BYN': 28.6227    # 1 белорусский рубль = 28.6227 рубля
}
def convert_to_rub(row):
    currency = row['operation_currency']
    amount = row['final_sum']
    if currency == 'RUB':
        return amount
    elif currency in exchange_rates:
        return amount * exchange_rates[currency]
    else:
        return amount  # оставим как есть, если что-то экзотическое

data['amount_in_rub'] = data.apply(convert_to_rub, axis=1)
data['operation_currency'] = 'RUB'  # всё переведено в рубли

# 8) Создаём разные метрики

user_count = data['customer'].nunique()               # общее число уник. пользователей
final_revenue = data['final_sum'].sum().astype(int)   # общая сумма (final_sum)
final_transaction = data['operation_sum'].sum()       # сумма operation_sum
final_comission = data['comission_sum'].sum()
mean_transaction = data['operation_sum'].mean()
median_transaction = data['operation_sum'].median()

# Сколько пользователей совершили оплату
user_pay_count = data.query('type == "Оплата"')['customer'].nunique()

# first_month для каждого пользователя
data['first_month'] = data['customer'].map(
    data.groupby('customer')['action_date'].min().dt.to_period('M')
)

# Считаем кумулятивное количество пользователей по месяцам
users_count_per_month = (
    data
    .groupby('first_month')['customer']
    .nunique()
    .cumsum()
    .reset_index()
)

# Кумулятивная выручка по месяцам
money_per_month = (
    data.groupby('first_month')['final_sum']
    .sum()
    .round()
    .astype(int)
    .cumsum()
    .reset_index()
)

# Средняя сумма транзакции по месяцам
mean_revenue_per_month = (
    data.groupby('action_date_month')
    .agg({'final_sum': ['mean']})
    .reset_index()
    .round(2)
)
# У mean_revenue_per_month теперь есть мультииндекс колонок

# Для скользящего среднего
monthly_mean = (
    data
    .groupby('action_date_month', as_index=False)['final_sum']
    .mean()
)
monthly_mean = monthly_mean.sort_values('action_date_month')
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
# --- Когортный анализ ---
user_first_tx = (
    data
    .groupby('customer', as_index=False)
    .agg(first_txn_date=('action_date', 'min'))
)
user_first_tx['cohort_month'] = user_first_tx['first_txn_date'].dt.month
user_first_tx['cohort_year'] = user_first_tx['first_txn_date'].dt.year

df_merged = data.merge(user_first_tx, on='customer', how='left', validate='many_to_one')
df_merged = df_merged.dropna(subset=['first_txn_date'])
df_merged['txn_year'] = df_merged['action_date'].dt.year
df_merged['txn_month'] = df_merged['action_date'].dt.month
df_merged['month_of_life'] = df_merged['txn_month'] - df_merged['cohort_month']

grouped = df_merged.groupby(['cohort_month', 'month_of_life'])
cohort_metrics = grouped[['month_of_life','id','customer','final_sum']].agg(
    transactions_count=('id','count'),
    active_users=('customer','nunique'),
    total_sum=('final_sum','sum'),
    avg_check=('final_sum', 'mean')
).reset_index()

# Кумулятивная сумма по каждой когорте
cohort_metrics['cumulative_sum'] = (
    cohort_metrics.sort_values('month_of_life')
    .groupby('cohort_month')['total_sum']
    .cumsum()
)

# Пивоты
cohort_pivot_active_users = (
    cohort_metrics
    .pivot(index='month_of_life', columns='cohort_month', values='active_users')
    .fillna(0)
)
cohort_pivot_ltv = (
    cohort_metrics
    .pivot(index='month_of_life', columns='cohort_month', values='cumulative_sum')
    .fillna(0)
)
cohort_pivot_transactions = (
    cohort_metrics
    .pivot(index='month_of_life', columns='cohort_month', values='transactions_count')
    .fillna(0)
)
cohort_pivot_total_sum = (
    cohort_metrics
    .pivot(index='month_of_life', columns='cohort_month', values='total_sum')
    .fillna(0)
)
cohort_pivot_avg_check = (
    round(cohort_metrics)
    .pivot(index='month_of_life', columns='cohort_month', values='avg_check')
    .fillna(0)
)

# Размер каждой когорты
cohort_sizes = (
    user_first_tx
    .groupby('cohort_month', as_index=False)
    .agg(cohort_size=('customer', 'nunique'))
)
# Добавим размеры к cohort_metrics
cohort_metrics = cohort_metrics.merge(
    cohort_sizes,
    on='cohort_month',
    how='left'
)
cohort_metrics['retention_rate'] = (
    cohort_metrics['active_users'] / cohort_metrics['cohort_size']
).round(2)
cohort_metrics['churn_rate'] = (1 - cohort_metrics['retention_rate']).round(2)

pivot_retention = (
    cohort_metrics
    .pivot(index='month_of_life', columns='cohort_month', values='retention_rate')
    .fillna(0)
)
pivot_churn = (
    cohort_metrics
    .pivot(index='month_of_life', columns='cohort_month', values='churn_rate')
    .fillna(0)
)

# --- RFM-анализ ---
def prepare_rfm_data(data, analysis_date=None):
    if analysis_date is None:
        analysis_date = data['action_date'].max()
    rfm = data.groupby('customer').agg({
        'action_date': lambda x: (analysis_date - x.max()).days,  # Recency
        'amount_in_rub': ['count', 'sum']  # Frequency & Monetary
    }).reset_index()
    rfm.columns = ['customer', 'recency', 'frequency', 'monetary']
    
    # Отсечение выбросов
    for column in ['recency', 'frequency', 'monetary']:
        q1 = rfm[column].quantile(0.25)
        q3 = rfm[column].quantile(0.75)
        iqr = q3 - q1
        upper_bound = q3 + 1.5 * iqr
        rfm[column] = np.where(rfm[column] > upper_bound, upper_bound, rfm[column])
    return rfm

rfm_data = prepare_rfm_data(data)

def quantile_segmentation(rfm_data, n_segments=3):
    rfm = rfm_data.copy()
    def safe_qcut(series, q):
        unique_values = series.nunique()
        if unique_values < q:
            q = unique_values
        bins = pd.qcut(series, q=q, duplicates='drop', retbins=True)[1]
        labels = range(len(bins) - 1, 0, -1)
        return pd.qcut(series, q=q, labels=labels, duplicates='drop')
    rfm['R'] = safe_qcut(rfm['recency'], n_segments)
    rfm['F'] = safe_qcut(rfm['frequency'], n_segments)
    rfm['M'] = safe_qcut(rfm['monetary'], n_segments)
    rfm['RFM_Score'] = rfm['R'].astype(str) + rfm['F'].astype(str) + rfm['M'].astype(str)
    return rfm

rfm_segmented = quantile_segmentation(rfm_data)
rfm_segmented = rfm_segmented[~rfm_segmented['RFM_Score'].str.contains('nan', na=False)]

def plot_rfm_distributions(rfm_data):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle('Распределение RFM-метрик', fontsize=14)
    sns.histplot(data=rfm_data, x='recency', bins=30, ax=axes[0])
    axes[0].set_title('Распределение Recency')
    axes[0].set_xlabel('Дни с последней покупки')
    sns.histplot(data=rfm_data, x='frequency', bins=30, ax=axes[1])
    axes[1].set_title('Распределение Frequency')
    axes[1].set_xlabel('Количество покупок')
    sns.histplot(data=rfm_data, x='monetary', bins=30, ax=axes[2])
    axes[2].set_title('Распределение Monetary')
    axes[2].set_xlabel('Общая сумма покупок')
    plt.tight_layout()
    return fig

rfm_dist_plot = plot_rfm_distributions(rfm_data)

# --- DAU, WAU, sticky ---
dau_total = (
    data.groupby('action_date').agg({'customer': 'nunique'}).mean()
)
wau_total = (
    data.groupby(['action_date_month', 'action_date_year'])
    .agg({'customer': 'nunique'})
    .mean()
)
dau_total = int(dau_total)
wau_total = int(wau_total)
sticky  = (dau_total / wau_total * 100)

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
        3) Переключатель между DAU, WAU и sticky  
        4) Динамика показателей по месяцам (4 варианта графиков)
        """
    )

    # --- Первый ряд ---
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Количество пользователей (user_count)",
            value=user_count
        )
    with col2:
        st.metric(
            "Общая сумма транзакций (final_transaction)",
            value=round(final_transaction, 2)
        )

    # --- Второй ряд ---
    col3, col4 = st.columns(2)
    with col3:
        st.metric(
            "Количество заплативших пользователей (user_pay_count)",
            value=user_pay_count
        )
    with col4:
        st.metric(
            "Итоговая выручка (final_revenue)",
            value=round(final_revenue, 2)
        )

    # --- Третий ряд: DAU, WAU, sticky
    st.markdown("### DAU, WAU, sticky")
    choice_metric = st.selectbox("Выберите метрику:", ["DAU", "WAU", "sticky"])
    if choice_metric == "DAU":
        st.metric("DAU", dau_total)
    elif choice_metric == "WAU":
        st.metric("WAU", wau_total)
    else:
        st.metric("sticky", round(sticky, 2))

    # --- Графики по месяцам ---
    st.markdown("### Динамика по месяцам")
    choice_chart = st.radio(
        "Выберите график:",
        [
            "Линейный график: кумулятивное число пользователей",
            "Линейный график: кумулятивная выручка",
            "Среднее по месяцам (mean_revenue_per_month)",
            "Таблица со скользящим средним (monthly_mean)"
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

    elif choice_chart == "Среднее по месяцам (mean_revenue_per_month)":
        tmp = mean_revenue_per_month.copy()
        tmp.columns = ["action_date_month","mean_final_sum"]  # убираем мультииндекс
        ax.plot(
            tmp["action_date_month"].astype(str),
            tmp["mean_final_sum"],
            marker="o",
            color="purple"
        )
        ax.set_title("Средняя сумма (final_sum) по месяцам")
        ax.set_xlabel("Месяц")
        ax.set_ylabel("Средняя сумма, руб.")
        plt.xticks(rotation=45)

    else:  # "Таблица со скользящим средним (monthly_mean)"
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
            label="Скользящее среднее (3 месяца)"
        )
        ax.set_title("Средняя сумма и скользящее среднее (3 месяца)")
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
        На графиках можно увидеть, как распределены пользователи по R, F и M.
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
        ax2.set_xlabel("Месяц жизни когорты (month_of_life)")
        ax2.set_ylabel(chosen_ylabel)
        ax2.legend()

    st.pyplot(fig2)

    st.markdown(
        f"""
        **Пояснение**:
        - В тепловой карте по оси X (столбцам) — номер когорты (cohort_month),
          по оси Y (строкам) — месяц жизни когорты (0 = месяц первого визита).
        - В линейном графике каждая линия — это отдельная когорта (cohort_month).
        
        Значения метрики: {selected_table}.
        """
    )

