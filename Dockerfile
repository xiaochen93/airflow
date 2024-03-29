FROM apache/airflow:2.5.2
COPY requirements.txt /
RUN pip install --user --upgrade pip
RUN pip install --no-cache-dir --user -r /requirements.txt
RUN pip install --upgrade selenium
RUN python -c "import nltk; nltk.download('stopwords')"