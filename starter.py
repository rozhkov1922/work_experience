import streamlit as st
import os
from dotenv import load_dotenv
import xlrd
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import random
import functions

st.title('Титульный заголовок приложения')
word = ' и переменная'
st.text('Какой-то текст')
st.markdown(f'*Какой-то* **текст** с ***разметкой*** {word}')

# users = ['user_' + str(random.randint(1, 20)) for _ in range(10000)]
# values = [random.randint(100, 1000) for _ in range(10000)]

# df = pd.DataFrame()

# df['user'] = users
# df['value'] = values

# df['total_value'] = df.groupby('user')['value'].transform('sum')

# st.dataframe(df.total_value.nlargest(10))

# plotly_data = df.groupby('user')['value'].sum().reset_index()

# plotly_graph = px.bar(plotly_data, x='user', y='value')
# st.plotly_chart(plotly_graph)

# st.line_chart(plotly_data, x='user', y='value')

# fig1, ax1 = plt.subplots()
# ax1.pie(plotly_data.value, labels=plotly_data.user)
# ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

# st.pyplot(fig1)

upload_file = st.sidebar.file_uploader('загрузить файлы')


if upload_file is not None:
    show = st.sidebar.button('показать датасет')
    test = st.sidebar.button('какая то кнопка')
    some = st.slider('какой то слайдер')
    some2 = st.sidebar.selectbox('some box', options=['option 1', 'option 2'])
    st.write(f'lkskjklkewjlkew {some} l;ksjdl;jsd;ljsd;l')
    if show:
        st.text(functions.kewl_function(' User'))
        st.text(functions.another_func())
        test_df = pd.read_csv(upload_file)
        st.dataframe(test_df.head())
        to_download = test_df[['Order ID', 'Order Date']].to_csv().encode('utf-8')
        st.download_button(label='Скачать чистые данные', file_name='some_file.csv', data=to_download)
    if test:
        test_df = pd.read_csv(upload_file)
        st.text(test_df.columns)
    