# -*- coding: utf-8 -*-
"""
Created on Wed Nov 23 17:47:44 2022

@author: liux5
"""
from collections import Counter

cnt = Counter()

file = open("news_links/linkcache_antaranews_2022-01-01_2022-11-30.txt", "r")
keywords = set()
for line in file:
  keyword = (line.split('https://www.antaranews.com')[1].split('/')[1]).strip()
  cnt.update([keyword])

print(cnt)


