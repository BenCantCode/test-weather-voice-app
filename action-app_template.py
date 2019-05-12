#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from snipsTools import SnipsConfigParser
from hermes_python.hermes import Hermes
from hermes_python.ontology import *
import io
import urllib2
import json
import schedule
from threading import Thread
import time
import math
from datetime import datetime, timedelta
import calendar


CONFIG_INI = "config.ini"

# If this skill is supposed to run on the satellite,
# please get this mqtt connection info from <config.ini>
# Hint: MQTT server is always running on the master device
MQTT_IP_ADDR = "localhost"
MQTT_PORT = 1883
MQTT_ADDR = "{}:{}".format(MQTT_IP_ADDR, str(MQTT_PORT))


class Weather(object):
    """Class used to wrap action code with mqtt connection

        Please change the name refering to your application
    """

    def __init__(self):
        # get the configuration if needed
        try:
            self.config = SnipsConfigParser.read_configuration_file(CONFIG_INI)
        except:
            self.config = None

        # start listening to MQTT
        self.start_blocking()

    # --> Sub callback function, one per intent
    def weather_callback(self, hermes, intent_message):
        # terminate the session first if not continue
        hermes.publish_end_session(intent_message.session_id, "")

        # action code goes here...
        print '[Received] intent: {}'.format(intent_message.intent.intent_name)

        parsed = self.get_weather()
        current_time = int(time.time())
        sentence = 'An error occured when getting the weather.'
        if(current_time - parsed['currently']['time'] < 60):
            print("Less than a minute ago, using cached...")
            sentence = 'It is {} outside, with a temperature of {} degrees.'.format(
                parsed['currently']['summary'], parsed['currently']['temperature'])
        elif(current_time - parsed['currently']['time'] < 172800):  # 48 hours
            print('Looking for hourly data...')
            for i in parsed['hourly']['data']:
                if(i['time'] == current_time-(current_time % 3600)):
                    sentence = 'It is {} outside, with a temperature of {} degrees. This hourly data was gathered {}. For more up-to-date information, connect to the internet.'.format(
                        i['summary'], i['temperature'], self.get_readable_date(i['time']))
                break
            print("Couldn't find hourly data...")
        else:
            print("Too late for hourly data, using daily.")
            epoch_today_morning = int((datetime.now().replace(hour=7, minute=0, second=0, microsecond=0) - datetime.utcfromtimestamp(0)).total_seconds())
            for i in parsed['daily']['data']:
                if(i['time'] == epoch_today_morning):
                    sentence = 'Today, it is supposed to be {} outside, with high of {} and a low of {}. This daily data was gathered {}. For more up-to-date information, connect to the internet.'.format(
                i['summary'], i['temperatureHigh'], i['temperatureLow'], self.get_readable_date(i['time']))
            print("Couldn't find daily!")


        hermes.publish_start_session_notification(
                intent_message.site_id, sentence, "")

    def temperature_callback(self, hermes, intent_message):
        # terminate the session first if not continue
        hermes.publish_end_session(intent_message.session_id, "")

        # action code goes here...
        print '[Received] intent: {}'.format(intent_message.intent.intent_name)

        parsed = self.get_weather()

        sentence = 'It is currently {} degrees.'.format(
            parsed['currently']['temperature'])

        # if need to speak the execution result by tts
        hermes.publish_start_session_notification(
            intent_message.site_id, sentence, "")
    # More callback function goes here...

    # --> Master callback function, triggered everytime an intent is recognized
    def master_intent_callback(self, hermes, intent_message):
        coming_intent = intent_message.intent.intent_name
        if coming_intent == 'searchWeatherForecast':
            self.weather_callback(hermes, intent_message)
        if coming_intent == 'searchWeatherForecastTemperature':
            self.temperature_callback(hermes, intent_message)
        # more callback and if condition goes here...

    # --> Register callback function and start MQTT
    def start_blocking(self):
        with Hermes(MQTT_ADDR) as h:
            h.subscribe_intents(self.master_intent_callback).start()

    def download_weather(self):
        url = ('https://api.darksky.net/forecast/{}/{}'.format(self.config.get(
            'secret').get('api_key'), self.config.get('secret').get('coords')))
        data = urllib2.urlopen(url).read()
        with open("weather.json", "wb") as cache:
            cache.write(data)
        return json.loads(data)

    def get_weather(self):
        try:
            return self.download_weather()
        except urllib2.URLError:
            with open('weather.json', 'r') as cache:
                return json.loads(cache.read())
    def get_readable_date(self, time_input):
        time_delta = time.time() - time_input
        current_time = time.localtime()
        current_datetime = datetime.now()
        parsed_time = time.localtime(time_input)
        parsed_datetime = datetime.fromtimestamp(time_input)
        yesterday_morning_datetime = (
            current_datetime - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        print(yesterday_morning_datetime)
        if(parsed_datetime > yesterday_morning_datetime):  # two days
            if(parsed_time.tm_mday == current_time.tm_mday):
                return time.strftime('today at %-I %p', parsed_time)
            return time.strftime('yesterday at %-I %p', parsed_time)
        else:
            if(math.ceil(time_delta/172800)) > 1:
                unit = 'days'
            else:
                unit = 'day'
            return '{} {} ago'.format(int(math.ceil(time_delta/172800)), unit)


def auto_download_weather(weather):
    schedule.every().day.at("6:00").do(weather.download_weather)


if __name__ == "__main__":
    weather = Weather()
    thread = Thread(target=auto_download_weather, args=(weather))
    thread.start()
