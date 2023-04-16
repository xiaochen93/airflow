# -*- coding: utf-8 -*-
"""
Created on Fri Apr  1 10:41:12 2022

@author: liux5
"""

"""
CLASS: NewsAgencyObject - initalise an configuration object to specify the requirements
for web scrapping on a specify news agency.

INPUT: namespace object include:
        domain - website default domain
        

"""

from collections import namedtuple

class NewsTargetObject:
    def __init__(self,parameters):
                
        self._domain = parameters.domain
        
        self._website = parameters.website
        
        self._sitemap = parameters.sitemap
        
        self._parser = parameters.parser
        
        self._name = parameters.name
        
        self._css_paths = parameters.css_paths
        
        self.nsObject = self._getNewsAgencyTargetObject()
        
    def _getNewsAgencyTargetObject(self):
        try:
            Attributes = namedtuple('NewsTargetObject', ['DOMAIN', 'WEBSITE','SITEMAP','PARSER','NAME','CSS_PATHS'])
            NewsAgencyObject = Attributes(self._domain,self._website,self._sitemap,self._parser,self._name,self._css_paths)
            print('\n-- NSTarget Object: Good to go.')
        except Exception as e:
            print(e)
            print('\n-- NSTarget Object: Failed to create.')
        return NewsAgencyObject