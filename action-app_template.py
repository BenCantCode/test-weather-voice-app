#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from snipsTools import SnipsConfigParser
from hermes_python.hermes import Hermes
from hermes_python.ontology import *
import io
import urllib2
import json


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
        except :
            self.config = None

        # start listening to MQTT
        self.start_blocking()
        
    # --> Sub callback function, one per intent
    def weather_callback(self, hermes, intent_message):
        # terminate the session first if not continue
        hermes.publish_end_session(intent_message.session_id, "")
        
        # action code goes here...
        print '[Received] intent: {}'.format(intent_message.intent.intent_name)

        parsed = json.loads(urllib2.urlopen('https://api.darksky.net/forecast/{}/{}'.format(self.config.get('secret').get('api-key'), self.config.get('secret').get('coords'))))
        sentence = 'It is currently {} degrees.'.format(parsed['currently']['temperature'])

        # if need to speak the execution result by tts
        hermes.publish_start_session_notification(intent_message.site_id, sentence, "")

    def temperature_callback(self, hermes, intent_message):
        # terminate the session first if not continue
        hermes.publish_end_session(intent_message.session_id, "")
        
        # action code goes here...
        print '[Received] intent: {}'.format(intent_message.intent.intent_name)

        parsed = json.decode(urllib2.urlopen('https://api.darksky.net/forecast/{}/{}'.format(self.config.get('secret').get('api-key'), self.config.get('secret').get('coords'))))
        sentence = 'The temperature is currently {} degrees.'.format(parsed['currently']['temperature'])

        # if need to speak the execution result by tts
        hermes.publish_start_session_notification(intent_message.site_id, sentence, "")

    # More callback function goes here...

    # --> Master callback function, triggered everytime an intent is recognized
    def master_intent_callback(self,hermes, intent_message):
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

if __name__ == "__main__":
    Weather()
