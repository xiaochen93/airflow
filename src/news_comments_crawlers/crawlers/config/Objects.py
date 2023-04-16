# -*- coding: utf-8 -*-
"""
Created on Wed Aug 31 18:20:12 2022

@author: liux5
"""
from argparse import Namespace

cna_params = Namespace(
    domain = 'www.channelnewsasia.com',
    website = 'https://www.channelnewsasia.com/',
    sitemap = 'https://www.channelnewsasia.com/sitemap.xml',
    parser = 'lxml',
    name = 'cna',
    css_paths = {
        'title_css': '',
        'news_category_css': '',
        'article_css' : '',
        'date_css': '',
        }
    )

st_params = Namespace(
    domain = 'www.straitstimes.com',
    website = 'https://www.straitstimes.com/',
    sitemap = 'https://www.straitstimes.com/sitemap.xml',
    parser = 'lxml',
    name = 'straitstimes',
    css_paths = {
        'title_css': '',
        'news_category_css': '',
        'article_css' : '',
        'date_css': '',
        }
    )

berita_params = Namespace(
    domain = 'berita.mediacorp.sg',
    website = 'https://berita.mediacorp.sg/',
    sitemap = 'https://berita.mediacorp.sg/Sitemap.xml',
    parser = 'lxml',
    name = 'berita',
    css_paths = {
        'title': 'h1[class*="post-title"]',
        'category': '',
        'date': 'span[class*="article-date"]',
        'article': 'div[class*="post-content clearfix"]'
        }
    )

antara_params = Namespace(
    domain = 'www.antaranews.com',
    website = 'https://www.antaranews.com/',
    sitemap = 'https://www.antaranews.com/sitemap/sitemap.xml',
    parser = 'lxml',
    name = 'ANT',
    css_paths = {
        'title': 'h1[class*="post-title"]',
        'category': '',
        'date': 'span[class*="article-date"]',
        'article': 'div[class*="post-content clearfix"]'
        }
    )
