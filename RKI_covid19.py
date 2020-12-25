# -*- coding: utf-8 -*-
from datetime import datetime, date, timedelta
import json
import random
import os
from dateutil.rrule import rrule, DAILY

import xarray
import pandas as pd
import numpy as np
from colour import Color
from pandas import DataFrame
import requests
import difflib

class RKI_covid19:
    FIRST_DAY = date(2020,12,1)
    DATADIRPATH = os.path.join(os.path.dirname(__file__), 'data_cases')

    def __init__(self, update = False):
        self.get_rkicovid19_dataset()
        self.get_bundesland_pop()
        if update:
            self.update_offlinedata()

    def get_bundesland_pop(self):
        bundesland_pop_data = pd.read_csv("bundesland.csv",
                                        encoding='utf8',
                                        usecols=['LAN_ew_GEN', 'LAN_ew_EWZ'], index_col='LAN_ew_GEN')
        bundesland_pop_data.loc['Countrywide'] = bundesland_pop_data.sum(
            numeric_only=True, axis=0)
        self.pop_data= bundesland_pop_data

    def get_cases_7_days(self, x, data):
        con1 = data['Meldedatum'] <= x['Meldedatum']
        con2 = data['Meldedatum'] > x['Meldedatum'] - timedelta(days=7)
        con3 = data['Bundesland'] == x['Bundesland']
        return data[con1 & con2 & con3]['AnzahlFall'].sum()


    def get_cases_7_days_100k(self, x, data):
        ewz = data.loc[x['Bundesland']]['LAN_ew_EWZ']
        res = (x["AnzahlFall_7_tage_absolut"] * 100000) / ewz
        return res


    def get_cases_s_4(self, x, data):
        con3 = data['Meldedatum'] >= x['Meldedatum'] - timedelta(days=10)
        con4 = data['Meldedatum'] <= x['Meldedatum'] - timedelta(days=4)
        con5 = data['Bundesland'] == x['Bundesland']
        return data[con3 & con4 & con5]['AnzahlFall'].sum()



    def get_r_value_intervall_7_days(self, x):
        s_t = x['AnzahlFall_7_tage_absolut']
        s_t_4 = x['AnzahlFall_s_4']
        if s_t_4 == 0:
            return 0
        else:
            return s_t / s_t_4
    
    def clean_bundeslaender(self,data):
        data = data.replace(to_replace=r'^Baden-Württemberg',
                            value='Baden-Wuerttemberg', regex=True)
        data = data.replace(to_replace=r'^Thüringen',
                            value='Thuringia', regex=True)
        data = data.replace(to_replace=r'^Bayern', value='Bavaria', regex=True)
        data = data.replace(to_replace=r'^Niedersachsen',
                            value='Lower Saxony', regex=True)
        data = data.replace(to_replace=r'^Sachsen', value='Saxony', regex=True)
        data = data.replace(to_replace=r'^Nordrhein-Westfalen',
                            value='North Rhine-Westphalia', regex=True)
        data = data.replace(to_replace=r'^Hessen', value='Hesse', regex=True)
        return data

    def get_rkicovid19_dataset(self):
        if not hasattr(self, 'data'):
            url = "https://opendata.arcgis.com/datasets/dd4580c810204019a7b8eb3e0b329dd6_0.csv"
            data = pd.read_csv(url,
                        encoding='utf8',
                        usecols=['Bundesland', 'AnzahlFall', 'Meldedatum'],
                        parse_dates=['Meldedatum'])

            data = data.groupby(['Bundesland', 'Meldedatum'], as_index=False)['AnzahlFall'].sum()
            data = data.sort_values(['Bundesland', 'Meldedatum'])
            data['AnzahlFall_7_tage_absolut'] = data.apply(lambda x: self.get_cases_7_days(x,data), axis=1)
            data['AnzahlFall_s_4'] = data.apply(lambda x: self.get_cases_s_4(x, data), axis=1)
            self.data = data

    def update_offlinedata(self):
        for day in rrule(DAILY, dtstart = self.FIRST_DAY, until=date.today()):
            self.load_data_for_day(day.date(), update = True)

    def load_data_for_day(self, day, update=False):
        filepath = os.path.join(self.DATADIRPATH, "{0}_{1}_{2}.csv".format(day.year, day.month, day.day))
        if os.path.isfile(filepath) and not update:
            datacontainer = pd.read_csv(filepath)
        else:
            datacontainer = self.generate_data_for_day(day)
            datacontainer.to_csv(filepath, index=True)

        return datacontainer

    def generate_data_for_day(self, day):
        
        #self.get_rkicovid19_dataset()
        cal_date = '{0}-{1}-{2}'.format(day.year, day.month, day.day)
        cases = self.data.set_index('Meldedatum').loc[cal_date]
        cases = cases.reset_index().set_index("Bundesland")
        cases.loc['Countrywide'] = cases.sum(numeric_only=True, axis=0)
        cases['Meldedatum'] = cases['Meldedatum'].dt.date
        cases.loc['Countrywide', 'Meldedatum'] = cal_date
        cases = cases.reset_index()
        cases['AnzahlFall_7_tage_100k'] = cases.apply(
            lambda x: self.get_cases_7_days_100k(x, self.pop_data), axis=1)
        cases['R-Wert'] = cases.apply(
            lambda x: self.get_r_value_intervall_7_days(x), axis=1)
        cases = self.clean_bundeslaender(cases)
     
        return cases
if __name__ == "__main__":
    c = RKI_covid19(update=True)